# guest-workspace Specification

## ADDED Requirements

### Requirement: Ephemeral guest identity

系统 SHALL 为每位访客签发独立的短期临时账号，使其无需注册即可进入工作台。

#### Scenario: Visitor enters as guest

- **WHEN** 访客调用 `POST /auth/guest` 且 `guestAccess.enabled` 为 true
- **THEN** 后端 MUST 创建 `accountKind=guest` 的新用户，并返回与登录相同结构的 token 响应；每次调用 MUST 创建不同的用户。

#### Scenario: Guest cannot log in with a password

- **WHEN** 任何人用访客邮箱调用 `POST /auth/login`
- **THEN** 后端 MUST 返回 `AUTH_INVALID_CREDENTIALS`。

#### Scenario: Guest session expires

- **WHEN** 访客会话的创建时间早于 `guestAccess.sessionTtlHours`
- **THEN** 受保护接口 MUST 返回 `AUTH_SESSION_REVOKED`。

#### Scenario: Guest access disabled or rate limited

- **WHEN** `guestAccess.enabled` 为 false，或最近 1 小时创建的访客数已达到 `hourlyCreationLimit`
- **THEN** `POST /auth/guest` MUST 分别返回 `SYSTEM_UNAVAILABLE` 或 `BUSINESS_RATE_LIMITED`，且不得创建用户。

### Requirement: Guest permission boundary

系统 SHALL 只允许访客执行只读或受限额保护的操作。

#### Scenario: Guest attempts a write operation

- **WHEN** 访客调用创建工作台诊断、保存诊断为知识、上传/删除/重新索引知识文档，或创建/更新/删除/检查 MCP 连接
- **THEN** 后端 MUST 返回 `AUTH_FORBIDDEN`，且不得产生任何记录或外部调用。

#### Scenario: Guest chat quota

- **WHEN** 访客最近 1 小时发送的对话消息数已达到 `guestAccess.chatMessagesPerHour`
- **THEN** 发送消息接口 MUST 返回 `BUSINESS_RATE_LIMITED`，且不得调用模型。

#### Scenario: Guests are isolated from each other

- **WHEN** 访客 A 读取访客 B 的会话、消息或其发起的演练诊断
- **THEN** 后端 MUST 返回 `AUTH_FORBIDDEN` 或在列表中不包含这些数据。

### Requirement: Drill diagnoses in the workspace

系统 SHALL 让演练发起人在智能诊断中查看演练诊断，同时保持演练数据与工作台数据的边界。

#### Scenario: Authenticated user triggers a drill

- **WHEN** 已登录用户（含访客）携带 Bearer token 调用 `POST /live-demo/runs`
- **THEN** 后端 MUST 记录发起人，并在响应的 `run.diagnosticId` 中返回诊断 ID；任务 owner MUST 仍为服务账号。

#### Scenario: Requester reads the drill diagnosis

- **WHEN** 发起人调用 `GET /aiops/diagnostics`、`GET /aiops/diagnostics/{id}`、`GET /aiops/diagnostics/{id}/evidence-chain` 或 `POST /aiops/diagnostics/{id}:stream`
- **THEN** 后端 MUST 返回该演练诊断，并标记 `origin=live-drill`；故障模拟器模式下 MUST 标记 `simulated=true`。

#### Scenario: Anonymous drills stay private

- **WHEN** 匿名访客触发演练
- **THEN** 该诊断 MUST NOT 出现在任何用户的诊断列表中。

#### Scenario: Simulated data never becomes workspace knowledge

- **WHEN** 演练诊断完成
- **THEN** 系统 MUST NOT 把它写入案例库或知识库，`:save-to-knowledge` 对非自有任务 MUST 返回 `AUTH_FORBIDDEN`。

### Requirement: Read-only drill SOP library

系统 SHALL 向已登录用户只读展示演练检索使用的 SOP 文档。

#### Scenario: List and read SOP documents

- **WHEN** 已登录用户调用 `GET /live-demo/sop-documents` 或 `GET /live-demo/sop-documents/{documentId}`
- **THEN** 后端 MUST 返回服务账号知识库中的文档元数据，详情 MUST 包含文档正文；未登录时 MUST 返回 `AUTH_UNAUTHENTICATED`。

### Requirement: Drill inside the workspace UI

系统 SHALL 把故障演练作为工作台的一个模块，并移除静态公开导览。

#### Scenario: Visitor opens the drill

- **WHEN** 未登录访客打开 `/drill` 或旧地址 `/live`
- **THEN** 前端 MUST 自动创建访客会话并在工作台布局中显示故障演练；导航第一项 MUST 是“故障演练”并带“模拟”标识。

#### Scenario: Guest mode is visible

- **WHEN** 当前用户为访客
- **THEN** 顶栏 MUST 显示访客模式与“演练数据由故障模拟器生成”标识，并提供所有者登录入口；受限操作的入口 MUST 隐藏或禁用并说明原因。

#### Scenario: From drill to evidence chain

- **WHEN** 演练完成
- **THEN** 页面 MUST 提供跳转到 `/aiops?diagnosticId=<id>` 的入口，智能诊断 MUST 打开该诊断并显示“故障演练 · 模拟数据”标识。

#### Scenario: Static tour removed

- **WHEN** 访客打开 `/demo`
- **THEN** 前端 MUST 重定向到 `/`，落地页 MUST NOT 再链接静态导览。
