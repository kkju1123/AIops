# real-mcp-tools Specification Delta

## MODIFIED Requirements

### Requirement: Real MCP tools support managed stdio and remote HTTP transports

系统 SHALL 从项目管理的 stdio MCP Server 与当前用户启用的 SSE / Streamable HTTP 连接装配真实工具，并 SHALL 保留超时、重试、同名工具保护和审计。

#### Scenario: Project CloudWatch server is enabled
- **WHEN** 用户启动聊天或 AIOps 诊断
- **THEN** Agent MUST 加载官方 CloudWatch Server 真实发现的工具以及该用户启用的远程工具

#### Scenario: Stdio command is unavailable
- **WHEN** 项目管理的 MCP 命令无法启动或超时
- **THEN** readiness 与工具调用 MUST 返回安全的明确失败，且不得泄露环境或凭据
