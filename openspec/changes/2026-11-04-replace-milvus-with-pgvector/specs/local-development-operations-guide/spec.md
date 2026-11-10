## MODIFIED Requirements

### Requirement: Local-first developer startup guide

仓库 SHALL 提供中文根级本地优先开发者指南，默认从 Compose 管理的 PostgreSQL + pgvector 开始，并在主机上直接运行后端、Vue 前端和官方 CLS MCP server。Alertmanager SHALL 作为显式可选 profile 记录。

#### Scenario: Developer follows ordinary local startup

- **WHEN** 开发者从已安装好先决条件的全新代码库中遵循根 README
- **THEN** 指南 MUST 提供前后端依赖、SQLite 迁移、pgvector、本地 MCP、后端和前端命令，且 MUST NOT 在 Compose 中运行应用服务

#### Scenario: Developer needs infrastructure services

- **WHEN** 开发者调用默认 Compose 命令
- **THEN** 它 MUST 只启动 PostgreSQL + pgvector；Alertmanager MUST 通过独立可选命令启动

### Requirement: Cross-platform local launchers

仓库 SHALL 提供 macOS/Linux shell 启动器和 Windows 命令启动器，通过 Compose 准备 PostgreSQL + pgvector、运行 SQLite 迁移，并在主机上直接启动 CLS MCP server、后端和前端。启动器 MUST NOT 打印凭据。

#### Scenario: macOS or Linux developer invokes the launcher

- **WHEN** 开发者运行 `scripts/start-local.sh`
- **THEN** 它 MUST 启动 PostgreSQL + pgvector，然后启动 MCP、后端和前端主机进程

#### Scenario: Windows developer invokes the launcher

- **WHEN** 开发者运行 `scripts\\start-local.bat`
- **THEN** 它 MUST 启动相同的依赖和主机进程集，且不要求 Unix shell

#### Scenario: Developer reads launcher output

- **WHEN** 启动器完成进程启动
- **THEN** 它 MUST 用中文报告前端、后端、MCP URL 和被忽略的本地日志目录，且 MUST NOT 打印凭据
