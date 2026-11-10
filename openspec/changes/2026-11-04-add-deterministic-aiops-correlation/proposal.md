## Why

当前 AIOps 工作流虽然能够通过真实 MCP 工具收集证据，但 `Replanner` 仅按计划索引决定继续或结束，最终根因主要由报告 LLM 从自由文本证据中归纳。这使诊断难以在关闭 LLM 时复现，也缺少可单元测试、可解释的根因候选排序。

## What Changes

- 在 `Planner -> Executor -> Replanner -> Report` 中增加确定性的 `Correlator` 节点。
- 使用声明式规则从告警、查询和真实执行证据中生成根因候选、分数、置信等级、匹配信号和关联证据 ID。
- 将确定性候选作为诊断步骤、证据、checkpoint 和报告 payload 持久化。
- 约束报告 LLM 只能基于确定性候选和原始证据描述根因；没有候选时必须明确证据不足。
- 增加纯函数单元测试和诊断工作流回归测试。

## Capabilities

### New Capabilities

无。

### Modified Capabilities

- `aiops-diagnosis-tasks`: 增加确定性信号关联、根因候选排序、候选持久化和报告约束。

## Impact

- 后端 AIOps 工作流、诊断报告上下文和回退报告。
- 后端单元测试与现有诊断集成测试。
- 不修改数据库 schema、HTTP API 或 SSE 契约。

