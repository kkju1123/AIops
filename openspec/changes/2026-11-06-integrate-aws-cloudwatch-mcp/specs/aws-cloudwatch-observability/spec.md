# aws-cloudwatch-observability Specification

## Purpose

定义 AWS CloudWatch 作为默认真实可观测性来源时的配置、权限、查询和安全边界。

## Requirements

### Requirement: Official CloudWatch MCP server is project managed

系统 SHALL 通过固定版本的官方 AWS Labs CloudWatch MCP Server 接入 CloudWatch，并 SHALL 仅从 merged 项目 JSON 读取启动配置。

#### Scenario: Local profile is configured
- **WHEN** 项目配置启用 CloudWatch 并提供 AWS profile 名称
- **THEN** 后端 MUST 通过 stdio 启动官方 Server，并仅向子进程传递 profile、region 和日志级别配置

#### Scenario: Deployment uses workload credentials
- **WHEN** profile 为空且运行环境提供 AWS SDK 默认凭据链
- **THEN** Server MUST 使用默认凭据链，且应用 MUST NOT 要求浏览器提交云凭据

### Requirement: CloudWatch diagnostics are read only and bounded

诊断 SHALL 只使用 CloudWatch 读取能力，并 SHALL 限制区域、日志组、时间窗口和结果数量。

#### Scenario: A diagnostic searches demo logs
- **WHEN** Planner 发现 `execute_cwl_insights_batch`
- **THEN** 计划 MUST 使用配置的 `eu-west-1`、`/super-ai/demo`、ISO 8601 UTC 时间窗口和最多 20 条结果的 Logs Insights 查询

#### Scenario: AWS access fails
- **WHEN** 凭据、IAM、区域或日志组配置导致工具失败
- **THEN** 诊断 MUST 保存明确失败和真实审计，MUST NOT 生成 mock evidence

### Requirement: Configuration templates contain no AWS credentials

可提交模板 SHALL 不包含 AWS access key、secret key、session token 或账户专属 ARN。

#### Scenario: Repository templates are inspected
- **WHEN** 验证 `config/*.template.json`
- **THEN** 模板 MUST 仅包含空 profile、公共默认区域、演示日志组和固定 Server 包版本
