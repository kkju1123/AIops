# aiops-diagnosis-tasks Specification Delta

## MODIFIED Requirements

### Requirement: Evidence-based execution uses provider-neutral observability capabilities

Executor SHALL 仅调用真实注册的 MCP 工具，并 SHALL 由 Planner 根据发现的工具和项目观测配置选择有界的日志、指标或告警读取能力，不得写死腾讯 CLS `SearchLog`。

#### Scenario: CloudWatch batch log search is available
- **WHEN** 发现 `execute_cwl_insights_batch`
- **THEN** Planner MUST 生成包含配置区域、日志组、UTC 时间窗口和受限 query 的单步真实查询

#### Scenario: No supported log tool is discovered
- **WHEN** MCP discovery 未返回受支持的日志读取能力
- **THEN** Executor MUST 记录不支持或不可用的明确失败，报告 MUST 标记证据不足

#### Scenario: MCP transport succeeds but CloudWatch batches fail
- **WHEN** 工具返回 `summary.failed_chunks > 0`，包括部分批次失败
- **THEN** Executor MUST 将工具执行和任务标记为失败，保留失败原因，不得将其作为成功诊断归档
