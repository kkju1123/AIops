## Context

实测（2026-11-08，冷启动）各阶段耗时：SOP 检索 27s、MCP 发现 6s、计划 59s、CloudWatch 查询 6.5s、报告 32s。计划调用的 completion 中 5006 个是 reasoning token，而计划最终会被归一化为一条有界日志查询。

## Goals / Non-Goals

**Goals:**

- 热状态下演练端到端 ≤ 30 秒，且页面每隔几秒就有新内容。
- 演练不依赖 AWS 凭据，任何时候点击都能跑通。
- 模拟数据与真实数据边界清晰：只用于 `/live`，明确标注。

**Non-Goals:**

- 不改变认证工作台诊断与聊天 Agent 的模型参数和观测源。
- 不实现复杂的拓扑或混沌工程，只模拟与场景对应的日志和指标。

## Decisions

### 关闭思考仅作用于 AIOps 调用

`LlmProvider.create_chat_model(*, thinking: bool = True)`；`thinking=False` 时 DeepSeek 请求带 `extra_body={"thinking": {"type": "disabled"}}`。实测同一请求 4.4s → 1.4s。诊断服务的计划与报告调用使用 `thinking=False`。

### 精简计划提示

计划提示只包含 SOP 文件名、标题和排查步骤摘要（每条命中截断），不再携带完整 chunk 与检索排名字段。可解释排名仍保存在 `knowledge_retrieval` 工具事件与证据中。

### 流式报告

报告节点使用 `astream`，按约 150ms 或 80 字符批量输出 `content.delta`（`channel=aiops`，`sequence` 递增）到 LangGraph custom 流。增量事件不写入节点 `events` 状态，但会经后台任务事件表持久化，断线恢复时可重放。流结束后仍执行 Markdown 清洗与回退，并发送最终 `report` 事件；客户端以最终 `report` 覆盖增量文本。

### 模型预热

FastAPI lifespan 在 `liveDemo.enabled` 时创建一个后台预热任务，加载 Embedding 与 Rerank 并各推理一次；失败只记录日志，不影响启动；关闭时取消。

### 故障模拟器 MCP Server

- `python -m super_ai.simulator.server`，FastMCP stdio。注入信息通过环境变量 `SUPER_AI_SIMULATED_FAULT`（JSON：runId、scenarioId、service、injectedAt）传入，后端为每次演练构造独立连接，因此不需要共享存储，也不会串到其他运行。
- `query_service_logs(service, start_time, end_time, limit)`：生成故障注入前的正常背景日志与注入后的故障日志（异常类型、logger、trace_id、延迟、错误率），以 runId 为随机种子，同一运行结果可复现。所有记录带 `simulated=true`。
- `query_service_metrics(service, metric_names, start_time, end_time)`：返回分钟级时间序列，注入后指标按场景跃升。
- 诊断服务在任务输入含 `simulatedFault` 时使用模拟器连接，并生成两步固定计划（日志 + 指标），LLM 只补充每步目的。

### 观测模式

`liveDemo.observability`：`simulator`（默认）或 `aws-cloudwatch`。模拟模式开放全部场景；`aws-cloudwatch` 模式维持现状。

## Risks / Trade-offs

- [关闭思考影响报告质量] → 报告模板与证据约束不变；实测对比后再决定，必要时只对计划关闭。
- [模拟数据被误认为真实] → 页面、日志记录、报告提示词三处标注；模拟数据不进知识库（演练已跳过案例沉淀）。
- [增量事件增多] → 批量输出控制行数（一次报告约数十条）。

## Migration Plan

无数据库迁移。配置模板新增 `liveDemo.observability`。回滚：设为 `aws-cloudwatch` 或关闭演练。
