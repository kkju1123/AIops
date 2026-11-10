## ADDED Requirements

### Requirement: Pgvector chunk table and index

后端 SHALL 在 PostgreSQL 中为知识 chunk 创建包含所有权、内容、JSON 元数据和固定维度向量的表，并 SHALL 使用 cosine HNSW 索引。

#### Scenario: Missing vector table is initialized

- **WHEN** 向量存储显式初始化且目标表不存在
- **THEN** 后端 MUST 创建 vector extension、chunk 表、范围过滤索引和 HNSW cosine 索引

#### Scenario: Import has no connection side effect

- **WHEN** 后端导入向量存储模块
- **THEN** 它 MUST NOT 建立 PostgreSQL 连接

### Requirement: Tenant-scoped pgvector operations

后端 SHALL 对向量搜索、chunk 列举和文档删除应用 tenant 与知识库范围，并使用参数化 SQL 处理所有用户范围值。

#### Scenario: Scoped vector search

- **WHEN** 检索工具提供 tenant 和允许的知识库 ID
- **THEN** 查询 MUST 只返回该范围内的 chunk，并按 cosine 相似度排序

#### Scenario: Empty knowledge base scope

- **WHEN** 允许的知识库 ID 为空
- **THEN** 向量存储 MUST 返回空列表且 MUST NOT 发出无范围查询

#### Scenario: Scoped document deletion

- **WHEN** 删除指定 tenant、知识库和文档的 chunk
- **THEN** 后端 MUST 仅删除三个范围值全部匹配的记录

### Requirement: Pgvector readiness is secret-safe

后端 SHALL 通过 `SELECT 1` 和 vector extension 状态检查 pgvector readiness，响应 MUST NOT 包含 DSN、密码或数据库驱动错误详情。

#### Scenario: Healthy pgvector dependency

- **WHEN** PostgreSQL 可访问且 vector extension 可用
- **THEN** readiness MUST 返回健康状态、主机、端口、数据库和表名

#### Scenario: Unavailable pgvector dependency

- **WHEN** 连接或查询失败
- **THEN** readiness MUST 返回统一的不可用消息且 MUST NOT 泄露凭据
