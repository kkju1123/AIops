# public-portfolio-demo Specification

## ADDED Requirements

### Requirement: Public project entry

系统 SHALL 为匿名访客提供无需登录的项目介绍入口。

#### Scenario: Recruiter opens the résumé project link

- **WHEN** 匿名访客打开根 URL
- **THEN** 前端 MUST 展示产品价值、核心模块、技术架构以及进入公开导览和所有者登录的清晰操作。

### Requirement: Safe interactive product tour

系统 SHALL 提供无需登录的交互式模块导览，同时不调用受保护或会产生外部影响的服务。

#### Scenario: Visitor explores product modules

- **WHEN** 访客在公开导览中切换 Chat、知识库、智能诊断和 MCP
- **THEN** 页面 MUST 更新对应模块说明和界面示意，并 MUST NOT 发起真实 LLM、上传、诊断或 MCP 请求。

#### Scenario: Preview content is not represented as live evidence

- **WHEN** 页面展示诊断、知识或工具相关说明
- **THEN** 页面 MUST 明确标注公开预览状态，并 MUST NOT 将静态内容描述为真实日志、引用、证据或工具结果。

### Requirement: Protected workspace remains protected

系统 SHALL 在增加公开导览后继续保护真实工作台。

#### Scenario: Anonymous visitor opens a workspace route

- **WHEN** 匿名访客访问 `/chat`、`/knowledge`、`/aiops` 或 `/mcp`
- **THEN** 前端 MUST 跳转到登录页并保留原目标路径。
