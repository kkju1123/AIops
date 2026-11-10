## MODIFIED Requirements

### Requirement: Aggregate secret-safe readiness check

后端 SHALL 暴露类型化 `/ready` 端点，独立检查 SQLite、pgvector、配置的 LLM provider 和本地 MCP server，且不暴露凭据。

#### Scenario: All required dependencies are ready

- **WHEN** SQLite、pgvector、配置的 LLM provider 和 MCP server 可用
- **THEN** `/ready` MUST 返回成功的 ready 结果，并包含安全组件元数据和延迟或工具计数信息

#### Scenario: A dependency is unavailable

- **WHEN** PostgreSQL 或 pgvector extension 不可用
- **THEN** `/ready` MUST 将 `pgvector` 标记为不可用，并继续返回其他依赖的独立状态

#### Scenario: 结果包含提供者配置上下文

- **WHEN** `/ready` 包含 LLM 配置上下文
- **THEN** 它 MUST 仅包含安全的 provider、model 和 base URL 信息，且 MUST NOT 包含 API key 或其他密钥

### Requirement: Safe configuration diagnostics

后端 SHALL 通过 `/config/check` 验证 SQLite、pgvector、LLM 和 MCP 配置。

#### Scenario: Configuration and dependencies are valid

- **WHEN** DSN、表名、维度和超时通过校验
- **THEN** 配置诊断 MUST 返回脱敏的 pgvector 主机、端口、数据库和表名

#### Scenario: Configuration or dependency is invalid

- **WHEN** 必需配置无效或依赖无法访问
- **THEN** `/config/check` MUST 标识受影响组件，且 MUST NOT 序列化密钥、凭据、DSN 或原始敏感配置值

### Requirement: Live lightweight workspace connectivity

前端 SHALL 在工作区挂载时获取轻量级后端 health，并从该结果中渲染标题栏的连接状态。

#### Scenario: Backend health succeeds

- **WHEN** 前端可以获取轻量级 `/health` 端点
- **THEN** 工作区标题 MUST 渲染连接状态，且响应 MUST 不依赖 SQLite、pgvector、Qwen 或 MCP 的可用性

#### Scenario: Backend health fails

- **WHEN** 前端无法获取成功的轻量级 health 响应
- **THEN** 工作区标题 MUST 渲染为降级状态，但不会阻止已认证的工作区路由加载
