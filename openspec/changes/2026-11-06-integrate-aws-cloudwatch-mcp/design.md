# Context

官方 AWS Labs CloudWatch MCP Server 通过 stdio 启动，并提供 `execute_cwl_insights_batch`、`get_metric_data`、`get_active_alarms` 等只读诊断工具。现有应用只支持 URL 型 SSE / Streamable HTTP 连接，且 AIOps Planner 强制把每个计划归一化为腾讯 CLS `SearchLog`。

# Goals / Non-Goals

**Goals:**

- 默认诊断能够查询 `eu-west-1` 的 `/super-ai/demo`，并保留真实 MCP 审计与失败语义。
- MCP transport 与 AIOps 领域逻辑不绑定某个云厂商。
- 本地开发可使用 AWS profile，部署环境可使用默认凭据链或工作负载角色。
- 查询必须限定区域、日志组、时间范围和最大记录数。

**Non-Goals:**

- 不在本次变更中创建或修改 AWS 资源。
- 不允许浏览器保存 AWS access key、secret key 或 session token。
- 不删除用户已有的远程 MCP 连接。
- 不实现自动修复或任何 CloudWatch 写操作。

# Decisions

## 项目默认 MCP 与用户连接分离

官方 CloudWatch Server 属于部署配置，不是用户输入。后端从 merged JSON 配置创建只读的项目默认连接；用户仍可在页面管理 HTTP 型 MCP 连接。运行时合并默认连接和当前用户启用的连接，并继续执行同名工具冲突保护。

## stdio 连接使用显式 allowlisted 配置

`McpServerConnection` 支持 `command`、`args` 和最小环境映射。只有项目 JSON 能配置 stdio；HTTP 管理 API 不接受任意命令。默认命令固定为 `uvx awslabs.cloudwatch-mcp-server@0.3.1`（真实安装验证发现原先指定的 0.3.0 未发布到 PyPI）。进程环境只传递配置中的 `AWS_PROFILE`、`AWS_REGION` 和 `FASTMCP_LOG_LEVEL`，AWS 凭据由 SDK 默认链解析。

## 诊断按能力选择工具

本地使用 `aws login` profile 时，SDK 需要 CRT 依赖。实际启动参数为 `uvx --with 'boto3[crt]>=1.41.0' awslabs.cloudwatch-mcp-server@0.3.1`；仅安装 MCP 包会在查询时抛出 MissingDependencyException。凭据仍由 SDK 读取，不能复制到项目配置。

诊断任务启动时按 owner 检查知识库文档。空知识库传入空的可访问知识库列表，复用检索工具的空结果路径，避免为没有文档的库下载 BGE 模型；报告明确标注未匹配 SOP。有文档时保留原有并发混合检索流程。

Planner 优先选择已发现的 `execute_cwl_insights_batch`，其次选择 `execute_log_insights_query`，再退回描述中声明日志搜索能力的真实工具。CloudWatch 默认计划使用 ISO 8601 UTC 时间、配置的日志组和区域，以及只读 Logs Insights 查询：选择时间、消息、service、severity、trace/incident 字段，倒序并限制 20 条。

一期使用 `execute_cwl_insights_batch`，因为它在一次调用内等待结果并返回合并记录，避免把异步 query ID 与第二次取结果调用混入当前单步 Executor。若只有 `execute_log_insights_query`，计划必须显式说明查询可能只返回 query ID，不得把它误当作日志记录。

## 证据采用标准化 envelope

工具原始结果继续保留在受 owner 约束的 evidence payload 中；给报告和 UI 的摘要使用 `provider`、`kind`、`region`、`source`、`tool`、`recordCount`、`records`、`query` 和 `queryId`。解析失败时保留有界文本并标记 `parseStatus=unparsed`，不得制造记录。

## 失败不回退到 mock

MCP 子进程同时设置 `AWS_REGION` 与 Boto3 使用的 `AWS_DEFAULT_REGION`，均来自项目配置。不能依赖开发者的 AWS profile 恰好配置默认区域。

`execute_cwl_insights_batch` 即使 MCP 协议调用成功，也可能返回 `summary.failed_chunks > 0`。Executor 必须将全部或部分批次失败按执行失败处理，生成失败审计、失败证据与失败任务，不能以零条日志成功归档。

命令缺失、AWS 凭据失效、IAM 不足、区域或日志组错误均返回明确失败，写入审计和诊断步骤。公开简历导览继续只展示静态安全演示，不触发 AWS 调用。

# Risks / Trade-offs

- [每次 stdio 调用会启动子进程] → 第一版保持会话短生命周期和明确超时，后续可在独立变更中增加进程池。
- [AWS MCP 工具 schema 随版本变化] → 固定包版本并在运行时以 discovery schema 为准；测试覆盖所需参数。
- [本地 profile 不存在] → readiness 显示安全错误，不记录 profile 内容或凭据。
- [旧数据库中保留腾讯连接] → 不删除用户数据；项目默认 AWS 连接与用户连接并存，文档提供人工禁用/删除旧连接的方法。

# Migration Plan

1. 增加 stdio transport 和项目默认连接配置，保持 HTTP 连接兼容。
2. 将 AIOps 默认日志步骤迁移到 CloudWatch 能力选择和标准化证据。
3. 更新 readiness、前端术语、模板和文档。
4. 运行目标测试、静态检查、构建和 OpenSpec 校验。
5. 使用具备只读 IAM 权限的 AWS profile 做真实 discovery/query 冒烟测试；没有本机凭据时明确记录未执行。

# Rollback

关闭 `observability.awsCloudWatch.enabled` 即可停止加载项目默认 AWS MCP；保留的用户 HTTP MCP 连接仍可工作。代码回滚不删除用户连接、诊断历史或 AWS 资源。
