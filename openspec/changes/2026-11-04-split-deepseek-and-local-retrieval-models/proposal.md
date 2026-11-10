## Why

当前 `llm` 配置将 Chat、Embedding 和 Rerank 绑定到同一个百炼 Key、Base URL 与 Provider，无法使用 DeepSeek 负责推理、同时让内部 SOP 的向量化和精排在本机完成。

## What Changes

- 将 OpenAI-compatible Chat Provider 配置为 DeepSeek。
- 新增独立 `retrievalModels` 配置，使用本地 `BAAI/bge-m3` Embedding 和 `BAAI/bge-reranker-v2-m3` Rerank。
- 本地模型懒加载，模块导入和后端启动不下载权重。
- 保持 1024 维 pgvector schema、BM25L、RRF、Rerank 和引用解释字段不变。
- 将 Chat readiness 与本地检索模型配置校验分开，且不暴露 API Key。

## Capabilities

### New Capabilities

- `local-retrieval-models`: 本地 Embedding/Rerank 模型配置、懒加载和异步边界。

### Modified Capabilities

- `qwen-openai-provider`: 将绑定 Qwen 的 Provider 抽象调整为通用 OpenAI-compatible Chat Provider，并使用 DeepSeek 配置。
- `knowledge-retrieval-tool`: Embedding 和 Rerank 改由独立本地 Provider 提供。

## Impact

- 后端模型配置、Provider、依赖、测试和运行文档。
- 首次知识索引或检索会从 Hugging Face 下载模型；模型缓存不进入仓库。
- 不修改 HTTP/SSE、SQLite schema 或 pgvector 维度。
