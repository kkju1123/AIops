## Context

演练诊断任务的 owner 是 `liveDemo.serviceAccountEmail` 对应的服务账号。SOP 检索按任务 owner 过滤 pgvector（`ownerUserId`、`tenantId`、`knowledgeBaseId`），所以演练只能检索服务账号知识库里的 SOP。工作台所有读接口都按 `user.id` 过滤。

## Goals / Non-Goals

- Goals：面试官零门槛进入真实工作台；演练与其他模块在同一界面里；演练结果能在智能诊断中查看完整证据链；不削弱租户隔离。
- Non-Goals：不让访客触发 CloudWatch 查询；不清理过期访客账号（后续 change 处理）；不改变所有者账号的现有行为。

## Decisions

### 每位访客一个临时账号

`POST /auth/guest` 创建 `account_kind=guest` 的用户，邮箱形如 `guest_<hex>@guest.agent-py.local`，密码哈希来自无法获知的随机密码（Argon2），因此不能用密码登录。会话沿用 `auth_sessions`，只在认证时额外检查：访客会话创建时间超过 `guestAccess.sessionTtlHours` 时返回 `AUTH_SESSION_REVOKED`。

备选方案是所有访客共用一个演示账号。它实现更简单，但访客会互相看到聊天记录，违反隔离原则，所以没有采用。

### 演练任务继续归服务账号，访客通过发起人读取

如果让访客直接拥有演练任务，SOP 检索就要跨 owner 读取服务账号的向量，这会破坏向量过滤规则。因此任务 owner 保持为服务账号，`live_demo_runs` 新增可空的 `requester_user_id`。

诊断读接口通过 `_readable_diagnostic_owner(user, diagnosticId)` 解析 owner：
1. 任务属于当前用户时，使用当前用户。
2. 否则，若存在 `diagnostic_task_id` 匹配且 `requester_user_id == user.id` 的演练运行，使用该运行的 owner（服务账号）读取。
3. 都不满足时返回 `AUTH_FORBIDDEN`。

`GET /aiops/diagnostics` 合并当前用户自己的任务和他发起的演练任务。取消后台任务、保存为知识仍只作用于自己拥有的任务。

### 访客写权限

新增依赖 `_member_user`：访客调用时返回 `AUTH_FORBIDDEN`，提示改用所有者账号。受限接口包括：创建工作台诊断、保存诊断为知识、上传/删除/重新索引知识文档、创建/更新/删除/检查 MCP 连接。

对话允许访客使用，但按 `guestAccess.chatMessagesPerHour` 限额，超出返回 `BUSINESS_RATE_LIMITED`。访客创建频率受 `guestAccess.hourlyCreationLimit`（全站每小时）限制。

### 诊断来源标识

任务 payload 新增 `origin`（`workspace` 或 `live-drill`）和 `simulated`（输入包含 `simulatedFault` 时为 true）。前端以此显示标识，并隐藏演练任务的取消按钮。

### 前端结构

- `/drill` 是 `WorkspaceLayout` 的子路由，路由元数据 `guestEntry: true`。守卫在未登录时调用 `enterAsGuest()`，失败时跳到登录页。
- 演练页移除自带的顶栏，改为工作台面板风格。完成后提供“在智能诊断中查看证据链”，跳到 `/aiops?diagnosticId=…`。
- 访客打开智能诊断时默认显示历史 tab，隐藏“描述问题/选择告警”；知识库显示只读演练 SOP 库；MCP 页面显示只读说明。

## Risks / Trade-offs

- 访客账号会积累在 SQLite 中 → 先由全站创建限额控制规模，后续再加清理任务。
- 返回给访客的演练任务 payload 包含服务账号 ID → 这是内部标识，不是凭据，可以接受。
- 演练诊断出现在所有者工作台的历史中 → 用 `origin` 与“模拟数据”标识区分，并且仍不进入知识库或案例库。
