# live-incident-drill Specification

## ADDED Requirements

### Requirement: Fault simulator observability for drills

系统 SHALL 在 `liveDemo.observability=simulator` 时，使用仓库内的故障模拟器 MCP Server 为演练提供日志与指标，而不依赖云凭据。

#### Scenario: Drill queries simulated logs and metrics

- **WHEN** 访客触发一个开放场景
- **THEN** 诊断 MUST 通过 MCP 调用模拟器的 `query_service_logs` 与 `query_service_metrics`，返回内容 MUST 对应本次注入的场景与服务，且每条记录 MUST 标注 `simulated=true`。

#### Scenario: Simulated data stays in the drill

- **WHEN** 认证用户在工作台创建诊断
- **THEN** 诊断 MUST NOT 使用故障模拟器连接，模拟数据 MUST NOT 写入任何知识库。

#### Scenario: Visitor can tell the data is simulated

- **WHEN** 演练页面展示日志、指标或报告
- **THEN** 页面 MUST 标注数据由故障模拟器生成。

### Requirement: Fast and continuously updating drill

系统 SHALL 让演练在热状态下快速完成，并持续向访客展示进展。

#### Scenario: AIOps model calls skip deep reasoning

- **WHEN** 诊断服务生成计划或报告
- **THEN** 后端 MUST 以关闭深度思考的方式调用聊天模型，而聊天 Agent MUST 保持原有设置。

#### Scenario: Report streams while generating

- **WHEN** 报告节点生成报告
- **THEN** SSE MUST 在 `aiops` 通道输出递增 `sequence` 的 `content.delta` 事件，随后输出最终 `report` 事件；页面 MUST 边接收边展示，并以最终报告替换增量文本。

#### Scenario: Models are warm before the first click

- **WHEN** 后端在演练开启时启动
- **THEN** 后端 MUST 在后台预热 Embedding 与 Rerank 模型，预热失败 MUST NOT 阻止启动。
