## MODIFIED Requirements

### Requirement: Ten correlated Java e-commerce incident fixtures
系统 SHALL 提供 10 套不同的 Java 电商微服务后端故障 fixture，每套包含一条关键日志、一条告警，并映射到一份按故障类别编写的通用排查手册。场景根因 MUST 只作为评测标准答案保存。

#### Scenario: Fixture catalog is generated
- **WHEN** 构建 Java 电商 fixture 目录
- **THEN** 目录 MUST 恰好包含 10 个不同 service/alert 故障场景和 10 个不同 trace ID

#### Scenario: Evidence types correlate
- **WHEN** 为任一场景生成日志与告警
- **THEN** 两类数据 MUST 具有一致的 `incident_id`、`service`、`alertname`，告警 annotation MUST 指向该场景所属类别手册，日志 trace ID MUST 可用于日志查询

#### Scenario: Scenario has operational rationale
- **WHEN** 检查任一 fixture
- **THEN** 它 MUST 包含可观测症状、触发阈值、标准根因、指向根因的线索、排查步骤、恢复动作和验证标准

#### Scenario: Runbooks do not reveal ground truth
- **WHEN** 生成类别手册与 fixture 日志
- **THEN** 内容 MUST NOT 包含任何场景标准根因原文
