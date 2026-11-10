# live-incident-drill Specification

## ADDED Requirements

### Requirement: One-click live incident drill

系统 SHALL 为匿名访客提供一键触发真实告警与真实 AIOps 诊断的演练入口。

#### Scenario: Visitor triggers a drill

- **WHEN** 匿名访客在 `/live` 选择已开放场景并点击“触发故障”
- **THEN** 后端 MUST 向配置的 Alertmanager 发布该场景告警、以服务账号创建真实诊断任务，并返回运行 ID、单次运行令牌和 `alertPublished` 结果。

#### Scenario: Visitor watches the drill in real time

- **WHEN** 访客使用运行 ID 和匹配令牌请求 `POST /live-demo/runs/{runId}:stream`
- **THEN** 后端 MUST 按现有 AIOps SSE 契约推送该次运行的 task.status、tool.call、reference.source、report、complete 或 error 事件，页面 MUST 依次展示告警、SOP 检索、计划、日志查询、重规划和报告。

#### Scenario: Scenario is not on the allowlist

- **WHEN** 请求的 `scenarioId` 不在 `liveDemo.scenarioIds` 中
- **THEN** 后端 MUST 返回 `VALIDATION_INVALID_ARGUMENT` 且不得发布告警或创建诊断。

### Requirement: Drill access isolation

系统 SHALL 保证演练入口不暴露用户数据，也不授予访客用户会话。

#### Scenario: Stream without a valid run token

- **WHEN** 请求缺少运行令牌、令牌不匹配或运行不存在
- **THEN** 后端 MUST 返回 `AUTH_FORBIDDEN` 且不得输出任何事件。

#### Scenario: Run token cannot access the workspace

- **WHEN** 访客把运行令牌作为 Bearer token 调用受保护 API
- **THEN** 后端 MUST 返回 `AUTH_UNAUTHENTICATED`。

#### Scenario: Owner is server-defined

- **WHEN** 创建演练运行
- **THEN** 诊断任务 owner MUST 是 `liveDemo.serviceAccountEmail` 对应的账号，后端 MUST NOT 接受客户端提交的 owner、tenant 或知识库标识。

### Requirement: Drill rate and cost limits

系统 SHALL 限制演练次数与并发以控制模型与云查询费用。

#### Scenario: Visitor exceeds the hourly limit

- **WHEN** 同一访客键最近 1 小时的运行数已达到 `perVisitorHourlyLimit`
- **THEN** 后端 MUST 返回 `BUSINESS_RATE_LIMITED`（HTTP 429）且不得发布告警或创建诊断。

#### Scenario: Daily or concurrent limit reached

- **WHEN** 全站最近 24 小时运行数达到 `dailyLimit`，或未结束运行数达到 `maxConcurrentRuns`
- **THEN** 后端 MUST 返回 `BUSINESS_RATE_LIMITED`，`GET /live-demo` MUST 反映剩余额度为 0。

#### Scenario: Drill is disabled or not prepared

- **WHEN** `liveDemo.enabled` 为 false 或服务账号不存在
- **THEN** `GET /live-demo` MUST 返回 `available=false` 与原因，创建运行 MUST 返回 `SYSTEM_UNAVAILABLE`。

### Requirement: Honest fallback and no case pollution

系统 SHALL 在无法实时运行时展示最近一次真实结果，并避免演练写入知识库。

#### Scenario: Live run is unavailable

- **WHEN** 额度用尽或服务不可用且存在已成功的演练运行
- **THEN** 页面 MUST 展示最近一次成功运行的报告，并标注其为真实运行及完成时间。

#### Scenario: Drill succeeds

- **WHEN** 演练诊断成功完成
- **THEN** 诊断服务 MUST NOT 为该任务创建故障案例或调度知识索引。
