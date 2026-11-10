## Context

真实诊断链路已经存在：`POST /aiops/diagnostics` 创建任务并交给 durable job runtime，`AiopsDiagnosticService` 执行 Planner → Executor → Replanner → Report，并把 SSE 事件持久化到后台任务事件表。限制在于所有入口都要求已登录用户，诊断与知识检索都按当前用户作用域过滤。

一次真实诊断约 60～100 秒，固定包含 1 次知识检索、1 次 CloudWatch Logs Insights 查询和 2 次 LLM 调用（计划与报告），单次成本有界。

## Goals / Non-Goals

**Goals:**

- 匿名访客一键触发真实告警与真实诊断，并实时看到全过程。
- 不破坏现有用户与 tenant 隔离；访客不能读取任何用户数据。
- 费用与滥用有明确上限，超限或依赖不可用时给出可理解的说明，并展示最近一次真实成功运行。

**Non-Goals:**

- 不为访客创建用户账号或会话，不开放聊天、上传、MCP 管理等其他能力。
- 不向 CloudWatch 写入日志；日志证据来自已存在的合成故障数据源。
- 本变更不处理公网部署、HTTPS 与反向代理。

## Decisions

### 专用服务账号执行，访客只持有单次运行令牌

演练任务归属于 `liveDemo.serviceAccountEmail` 对应的已注册用户，该账号由项目所有者预先创建并索引 SOP。服务端按邮箱查找账号，客户端无法指定 owner。创建运行时生成 `secrets.token_urlsafe(32)` 运行令牌，只把 SHA-256 哈希写入 `live_demo_runs`；流式读取必须同时提供 runId 与匹配的 `X-Live-Demo-Token`。

替代方案“为每个访客创建临时用户”需要为每个访客复制或开放 SOP 向量，并产生大量无主账号，因此不采用。

### 场景来自服务端白名单

场景定义来自 `LIVE_DRILL_INCIDENTS` 与 `JAVA_ECOMMERCE_INCIDENTS`，`liveDemo.scenarioIds` 决定开放哪些场景。默认只开放 `checkout-db-pool-exhausted`：CloudWatch 定时 Lambda 只写入 `checkout-service` 的 `database_connection_pool_exhausted` 日志，场景、告警与专用 SOP 必须与之对应，否则诊断只能得出“日志与告警不匹配”。演练告警不在注解中包含根因，避免“答案写在告警里”。专用 SOP 通过 `seed_ecommerce_aiops_sop.py --profile live-drill` 索引到服务账号。

### 故障注入 = 发布真实告警 + 创建真实诊断

创建运行时向配置中的 `local-alertmanager` 发布该场景告警；发布结果以 `alertPublished` 如实返回。无论发布成功与否，诊断都以同一份告警作为输入执行，告警会作为证据持久化。

### 限流与费用保护

在 SQLite `live_demo_runs` 中按以下条件计数，均在创建诊断前检查：

- 同一访客键（`sha256("live-demo:" + clientIp)`）最近 1 小时运行数 ≤ `perVisitorHourlyLimit`
- 全站最近 24 小时运行数 ≤ `dailyLimit`
- 未结束运行数 ≤ `maxConcurrentRuns`（以诊断任务状态判定，超过 `runTimeoutSeconds` 的运行不再计入）

超限返回 `BUSINESS_RATE_LIMITED`（429）。`enabled=false`、服务账号不存在时返回 `SYSTEM_UNAVAILABLE`。默认只使用 `request.client.host`；`trustForwardedFor=true` 时才读取 `X-Forwarded-For` 首个地址，供后续反向代理部署使用。

### 不沉淀案例

演练任务的 `input_payload.liveDemo=true`，诊断服务在报告成功后跳过 `DiagnosisCasePersistor`，避免每次演练都向服务账号知识库写入并索引新案例。

### 节点内事件即时推送

Planner 节点包含知识检索、MCP 工具发现和 LLM 规划，冷启动时耗时可达 90 秒。原实现只在节点结束后输出事件，页面会长时间停在“检索 SOP”。诊断服务改用 LangGraph `custom` 流在节点内即时推送事件，并新增 `Planner: discovering MCP tools.`、`Planner: drafting a bounded plan with the LLM.` 两条状态；节点结束时的 `updates` 按事件 id 去重，SSE 事件类型与字段不变。

### 最近一次成功运行作为兜底展示

`GET /live-demo` 返回最近一次成功演练的场景、完成时间、耗时和报告 Markdown。页面在额度用尽或服务不可用时展示它，并明确标注为“最近一次真实运行”及其时间。

## Risks / Trade-offs

- [CloudWatch 合成数据源停止] → 诊断仍会如实报告未找到日志；页面不伪造证据。
- [IP 限流可被代理绕过] → 全站每日上限与并发上限兜住总费用。
- [公开报告内容] → 报告只基于合成告警、合成日志和公开 SOP，不包含任何用户数据；返回前不附带工具原始参数中的凭据（本来也不含）。

## Migration Plan

1. 新增 Alembic revision 创建 `live_demo_runs`。
2. 配置模板新增 `liveDemo`，默认 `enabled=false`，本地显式开启。
3. 所有者使用已有 `seed_java_ecommerce_aiops_sops.py` 为服务账号索引 SOP。
4. 回滚：设置 `enabled=false` 即关闭公开入口；表可通过 downgrade 删除。
