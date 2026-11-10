# Why

当前诊断运行时、默认 MCP 连接和证据摘要都把腾讯 CLS 与 `SearchLog` 写死。项目已经在 AWS `eu-west-1` 建立可持续运行的 CloudWatch Logs、指标、告警和定时合成故障源，但应用尚不能通过官方 AWS Labs CloudWatch MCP Server 使用这些真实数据，因此简历演示仍会依赖与目标岗位不一致的云产品和不可执行的工具参数。

# What Changes

- 将默认可观测性提供方改为 AWS CloudWatch，并通过官方 `awslabs.cloudwatch-mcp-server` 的 stdio transport 接入真实工具。
- 为 MCP 客户端增加受项目配置管理的 stdio 连接，同时保留用户自建 SSE / Streamable HTTP 连接。
- 把 AIOps 规划从 `SearchLog` 专用逻辑改为 provider-neutral 的日志搜索能力，并为 CloudWatch `execute_cwl_insights_batch` 生成有界查询。
- 使用标准化的 provider、region、source、query 和 records 元数据保存日志证据，前端不再依赖 `SearchLog` 特殊结构。
- 更新 readiness、配置模板、启动流程、MCP 页面术语和运维文档；模板不得包含 AWS 密钥或会话令牌。
- 增加 stdio 生命周期、CloudWatch 计划参数、失败显式化、证据摘要和配置验证测试。

# Capabilities

## New Capabilities

- `aws-cloudwatch-observability`: 定义官方 CloudWatch MCP Server、默认区域、日志组和只读诊断能力的配置与运行边界。

## Modified Capabilities

- `real-mcp-tools`: 支持受管理的 stdio MCP Server 和 AWS 默认凭据链。
- `mcp-connection-management`: 区分项目管理的默认连接与用户管理的远程连接。
- `aiops-diagnosis-tasks`: 使用 provider-neutral 观测能力和真实 CloudWatch 日志查询。
- `aiops-evidence-chain`: 保存并展示标准化的跨提供方日志证据。

# Impact

- 后端 MCP 客户端、连接装配、配置检查、readiness 和 AIOps 规划器。
- 前端 MCP 工作区与诊断证据格式化。
- 项目配置模板、本地启动脚本、README 与运维文档。
- 不修改现有 AWS 资源，不在仓库保存 AWS 凭据，不把公开简历页面连接到私有 AWS 数据。
