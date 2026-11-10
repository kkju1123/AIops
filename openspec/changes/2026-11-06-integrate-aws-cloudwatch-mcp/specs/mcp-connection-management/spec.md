# mcp-connection-management Specification Delta

## MODIFIED Requirements

### Requirement: Managed MCP runtime assembly separates project and user connections

聊天与 AIOps SHALL 合并项目管理的默认 MCP 连接和当前用户启用的远程连接；用户管理 API SHALL 只允许安全的 SSE / Streamable HTTP URL，不得接受任意 stdio 命令。

#### Scenario: User has no remote connection
- **WHEN** 当前用户没有保存 MCP 连接且项目启用 CloudWatch
- **THEN** 运行时 MUST 仍加载项目管理的 CloudWatch 工具

#### Scenario: User submits a stdio command
- **WHEN** 用户通过连接管理 API 提交 stdio transport 或 command
- **THEN** API MUST 拒绝请求且不得启动命令
