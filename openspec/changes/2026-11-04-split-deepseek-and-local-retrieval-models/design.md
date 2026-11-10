## Context

Chat 模型需要远程推理和工具调用，Embedding/Rerank 则处理可能敏感的内部运维文档。三者生命周期、接口和成本不同，应通过独立配置和工厂解耦。

## Decisions

### DeepSeek 仅负责 Chat

继续使用 LangChain `ChatOpenAI`，将 Base URL、模型与 Key 指向 DeepSeek。Readiness 只发起最小 Chat 请求。

### 本地检索模型使用 Sentence Transformers

Embedding 使用 `BAAI/bge-m3`，输出归一化 1024 维向量；Rerank 使用 `BAAI/bge-reranker-v2-m3` 对 query-document pair 评分。同步推理通过线程执行，避免阻塞异步检索流程。

### 懒加载与进程内复用

模型对象在第一次 Embedding/Rerank 调用时加载并复用。模块导入、`create_app()` 和 readiness MUST NOT 下载模型或初始化 PyTorch。

### 保持向量兼容性

`bge-m3` 的 1024 维与当前 pgvector 列一致。切换模型后已有向量语义空间不兼容，现有文档需要重建索引。

## Risks / Trade-offs

- [首次调用下载较慢] → 懒加载并在文档中明确首次下载行为。
- [CPU 推理延迟较高] → 默认小批量执行，后续可配置 MPS/CUDA。
- [旧向量不可混用] → 切换后通过现有“重建索引”重新生成全部向量。
- [模型包增加依赖体积] → 不把权重纳入项目或容器，使用 Hugging Face 用户缓存。
