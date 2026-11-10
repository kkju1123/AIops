# AWS 真实链路验证

## 2026-11-07 区域与失败语义修复

- 用户任务暴露出 Boto3 默认区域缺失：MCP 协议返回成功但批次摘要 `failed_chunks=1`，曾被错误标记 succeeded。
- 按 Boto3 官方配置文档补传 `AWS_DEFAULT_REGION`，保留 `AWS_REGION`。参考：https://docs.aws.amazon.com/boto3/latest/guide/configuration.html
- Executor 检查批次失败数量；非零进入失败审计、证据及任务路径。
- 10 项相关 pytest 通过，目标 Ruff 和全项目 Pyright 通过。
- 重启后真实查询再次取得 4 条日志，记录解析成功。新任务为 `diagnostic_f42aa72de97b4b269dcb54dc9fc22c93`。

## 首次验证

验证时间：2026-11-07 16:15（北京时间）。本地开发环境；未部署云端应用。

- AWS profile 登录成功，官方 MCP discovery 返回 19 个工具。
- 通过应用 HTTP API 创建诊断任务 `diagnostic_dc204461e90448deb5fc14db7e8a769d`，最终状态 `succeeded`。
- 查询区域 `eu-west-1`、日志组 `/super-ai/demo`，时间范围限定为过去 24 小时，最大 20 条。
- `execute_cwl_insights_batch` 返回 4 条真实存储在 CloudWatch 中的合成演示日志，解析成功。
- 日志标注 `synthetic=true`，事件为 `database_connection_pool_exhausted`，字段 `latency_ms=2200`、`error_rate=0.18`。这不是生产事故，也不是独立查询得到的 CloudWatch 指标。
- 使用通用日志查询计划（`planOrigin=generic`），报告由模型生成（`reportGeneration=llm`），不是失败回退模板。
- 报告指出直接故障事件为连接池耗尽；连接泄漏、慢查询或流量等更深层原因缺乏证据，不能确认。
- 知识库为空，`noSopMatched=true`；报告没有虚构知识引用。此次未查询告警状态或执行修复。
- 报告与证据链保存在本地测试账户下，不自动出现在其他用户的诊断历史中。

已修复阻塞：本机时钟偏移导致登录失败、未发布的 MCP 版本、AWS login 所需 CRT 依赖缺失、空知识库触发无意义模型加载。

认证使用临时本地会话，过期后需要重新登录。此验证不代表六个月无人值守部署已完成；公开简历演示应使用明确标注的静态回放，不依赖本地会话。
