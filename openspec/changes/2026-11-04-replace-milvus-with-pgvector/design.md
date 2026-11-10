## Context

知识文档同时需要向量召回和 tenant/知识库范围过滤。当前 Milvus 实现已经通过 Repository 边界与索引任务和检索工具解耦，因此可以只替换基础设施与适配器。

## Goals / Non-Goals

**Goals:**

- 将默认容器从四个 Milvus 相关服务缩减为一个 PostgreSQL 服务。
- 保留 chunk 字段、所有权过滤、批量写入、删除和余弦相似度语义。
- 保留 BM25L + RRF + rerank 管线和可解释排名字段。
- 连接只在显式调用时建立，健康检查不泄露 DSN 密码。

**Non-Goals:**

- 不把 SQLite 业务数据迁入 PostgreSQL。
- 不迁移已有 Milvus 数据；本地文档可通过现有索引任务重新索引。
- 不改变 Embedding 模型或维度。
- 不新增数据库管理 UI。

## Decisions

### 单独的 pgvector 数据库边界

使用 `psycopg` 和 `pgvector` Python 适配器直接访问 Compose PostgreSQL。向量表由 Repository 的显式 `initialize()` 创建，避免把独立向量数据库混入 SQLite Alembic 迁移。

### 使用参数化 SQL 和白名单标识符

tenant、知识库和文档过滤全部使用参数化 SQL；表名在配置加载时按 SQL 标识符规则校验。向量使用 pgvector 类型适配器，禁止拼接用户输入。

### HNSW + cosine

表使用 `vector(1024)` 列和 `vector_cosine_ops` HNSW 索引。查询将 cosine distance 转换为越大越相关的相似度分数，供现有 RRF 管线使用。

### Alertmanager 可选

默认启动脚本只启动 PostgreSQL。需要告警演示时使用 Compose `observability` profile 启动 Alertmanager；告警提供者继续容忍数据源不可用。

## Risks / Trade-offs

- [已有 Milvus 向量不会自动迁移] → 本地开发数据通过现有文档重试索引重建，避免双写和一次性迁移复杂度。
- [同步 psycopg 调用可能阻塞事件循环] → 现有 API 已通过线程池调用向量边界，后台索引也沿用现有同步 Repository 契约。
- [表维度与配置不一致] → 初始化时固定向量列维度，写入前验证维度并用测试覆盖。

## Migration Plan

1. 增加 pgvector 配置、Repository 和单元测试。
2. 切换应用 wiring、readiness 和配置检查。
3. 替换 Compose 与本地启动脚本，更新模板和文档。
4. 启动 PostgreSQL，验证扩展、表、健康检查和目标测试。
5. 回滚时可恢复 Milvus 适配器与旧 Compose；SQLite 业务数据不受影响。
