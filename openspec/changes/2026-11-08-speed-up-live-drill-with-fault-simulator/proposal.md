## Why

公开实时故障演练（`/live`）实测需要 80～130 秒，面试官等不及。耗时主要来自：DeepSeek 制定计划时先推理约 5000 个 token（36～59 秒）、报告生成完才一次性展示（约 32 秒）、本地检索模型冷启动（约 25 秒）、每次调用都重新启动 AWS CloudWatch MCP 进程（约 12 秒）。此外演练依赖 AWS SSO 会话，会话过期后日志查询直接失败，公开演示不可靠。

## What Changes

- AIOps 诊断的计划与报告调用关闭 DeepSeek 深度思考；计划提示只携带 SOP 标题与排查步骤摘要。聊天 Agent 保持原有行为。
- 报告生成改为流式：诊断 SSE 在 `aiops` 通道输出 `content.delta`，页面边生成边显示，最终仍以 `report` 事件为准。
- 后端启动时（演练开启时）在后台预热本地 Embedding 与 Rerank 模型。
- 新增故障模拟器 MCP Server（`super_ai.simulator`，stdio）：触发演练时把故障“注入”到本次运行，模拟器按场景实时生成背景日志、故障日志和指标时间序列，提供 `query_service_logs` 与 `query_service_metrics` 工具。
- `liveDemo.observability` 新增 `simulator`（默认）与 `aws-cloudwatch` 两种模式；模拟模式下演练只使用模拟器 MCP，计划包含日志与指标两步。
- 页面与报告明确标注“故障模拟器生成”。演练可开放全部 11 个场景。

## Capabilities

### New Capabilities

- 无。

### Modified Capabilities

- `live-incident-drill`: 新增故障模拟器观测源、流式报告与延迟目标。

## Impact

- 后端：`llm/provider.py`（thinking 开关）、`aiops/diagnostics.py`（流式报告、模拟器计划、精简提示）、新模块 `simulator/`、`live_demo.py`、`api/app.py`（预热、模拟器连接）。
- 共享契约与前端：`content.delta` 在 aiops 通道的语义、演练页报告流式展示与模拟器标注。
- 配置：`liveDemo.observability`；文档与 `AGENTS.md` 例外条款。
- 不改变认证工作台诊断使用 CloudWatch 的行为，模拟数据不进入知识库。
