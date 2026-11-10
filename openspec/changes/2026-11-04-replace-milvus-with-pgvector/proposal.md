## Why

当前本地向量运行时由 etcd、对象存储、Milvus 和 Attu 组成，启动链路长、镜像多，且 MinIO 社区镜像变化已经导致本地启动失败。现有知识库规模不需要独立向量数据库，PostgreSQL + pgvector 可以用一个容器提供向量持久化、权限过滤和 HNSW 检索。

## What Changes

- 用 PostgreSQL 16 + pgvector 替换 etcd、MinIO、Milvus 和 Attu。
- 新增 pgvector Repository，保持现有 chunk、tenant 隔离、BM25L、RRF 和 rerank 行为。
- 将 readiness 和配置诊断从 Milvus 改为 pgvector，并确保连接信息脱敏。
- 默认本地启动只启动 PostgreSQL；Alertmanager 改为可选 observability profile。
- 保留 SQLite 作为业务数据库，本次不迁移用户、任务、证据和报告数据。

## Capabilities

### New Capabilities

- `pgvector-vector-store`: PostgreSQL + pgvector 的向量存储、检索、权限过滤和健康检查。

### Modified Capabilities

- `docker-compose-startup`: 本地 Compose 改为单 PostgreSQL 主依赖和可选 Alertmanager。
- `runtime-readiness-checks`: 向量依赖诊断改为 pgvector。
- `local-development-operations-guide`: 更新跨平台启动命令和本地端口。

## Impact

- 后端向量存储适配器、配置、readiness 与测试。
- Compose、本地启动脚本、README 和安装文档。
- 不改变 HTTP 业务 API、SSE、RAG 排名算法或 SQLite schema。
