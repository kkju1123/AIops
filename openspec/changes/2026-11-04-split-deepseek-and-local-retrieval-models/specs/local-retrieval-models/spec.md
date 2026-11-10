## ADDED Requirements

### Requirement: Local embedding model

后端 SHALL 使用配置的本地 BGE 模型生成固定维度、归一化的知识文档和查询向量。

#### Scenario: Model is loaded lazily

- **WHEN** 应用导入模块或创建 Provider，但尚未请求 Embedding
- **THEN** 后端 MUST NOT 下载或加载模型权重

#### Scenario: Documents are embedded

- **WHEN** 索引任务提交一批非空 chunk
- **THEN** 后端 MUST 在线程中批量生成与 pgvector 配置维度一致的浮点向量

### Requirement: Local rerank model

后端 SHALL 使用本地 cross-encoder 对融合候选进行 query-document 精排，并返回稳定的输入索引与相关性分数。

#### Scenario: Candidates are reranked

- **WHEN** 检索管线提交 query、候选文档和 top_n
- **THEN** 后端 MUST 按相关性降序返回不超过 top_n 个结果，并保留原始候选索引

#### Scenario: Invalid request is rejected

- **WHEN** top_n 超出候选范围
- **THEN** 后端 MUST 返回安全的 Rerank 错误
