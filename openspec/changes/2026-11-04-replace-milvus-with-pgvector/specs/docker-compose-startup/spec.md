## MODIFIED Requirements

### Requirement: Unified compose startup

项目 SHALL 在 `infra` 下提供仅管理本地容器基础设施的 Compose 文件。默认运行时 SHALL 只要求 PostgreSQL + pgvector；Alertmanager SHALL 通过可选 `observability` profile 提供。后端、前端和官方 CLS MCP Server SHALL 通过本地启动器直接在主机上运行；Compose MUST NOT 构建或运行应用程序镜像。

#### Scenario: Compose 文件定义了基础设施服务

- **WHEN** `infra/compose.yaml` 被检查
- **THEN** 它 MUST 定义 PostgreSQL + pgvector 和可选 Alertmanager，且 MUST NOT 定义 etcd、MinIO、Milvus、Attu、backend、frontend 或 `cls-mcp-server`

#### Scenario: Compose startup does not require local env files

- **WHEN** `infra/compose.yaml` 被检查
- **THEN** 它 MUST NOT 需要 `env_file`、`.env.example` 或 `--env-file` 作为项目应用程序配置输入

#### Scenario: Compose excludes application image runtime

- **WHEN** 检查 `infra` 中的 Compose 启动资产
- **THEN** 它们 MUST NOT 构建、引用或要求应用程序 Dockerfile 作为本地启动前提

## ADDED Requirements

### Requirement: Pgvector stack managed by compose

Compose SHALL 使用 `pgvector/pgvector` PostgreSQL 镜像提供向量运行时，并通过健康检查确认数据库可连接。

#### Scenario: Default infrastructure starts

- **WHEN** 开发者运行默认本地启动器
- **THEN** Compose MUST 只启动 PostgreSQL + pgvector 主依赖

#### Scenario: Optional alerts start

- **WHEN** 开发者启用 `observability` profile
- **THEN** Compose MUST 额外启动 Alertmanager

## REMOVED Requirements

### Requirement: Milvus stack managed by compose

**Reason**: 知识库规模不需要 etcd、对象存储、Milvus 和 Attu 四个容器，pgvector 可用单容器提供相同的向量检索边界。

**Migration**: 通过现有文档重建索引操作将知识 chunk 重新写入 pgvector；SQLite 业务数据不受影响。
