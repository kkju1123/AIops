# Oncall 新 Session 交接文档

更新时间：2026-11-05（Asia/Taipei）

## 1. 当前目标

把 `oncall` 作为主要 AIOps 项目继续开发，后续可将同级目录中的 `trainwatch` 作为“模型训练监控”能力嵌入，而不是再创建一套平行系统。

当前阶段正在完成模型配置拆分：

- Chat LLM：DeepSeek 的 OpenAI-compatible API
- Embedding：本地 `BAAI/bge-m3`
- Rerank：本地 `BAAI/bge-reranker-v2-m3`
- 向量库：PostgreSQL + pgvector
- 告警：可选 Alertmanager；现有 Prometheus/Alertmanager 接入保留

## 2. 必须先读

新 session 进入仓库后，先阅读：

1. `AGENTS.md`
2. `openspec/changes/2026-11-04-split-deepseek-and-local-retrieval-models/proposal.md`
3. `openspec/changes/2026-11-04-split-deepseek-and-local-retrieval-models/design.md`
4. `openspec/changes/2026-11-04-split-deepseek-and-local-retrieval-models/tasks.md`
5. `openspec/changes/2026-11-04-split-deepseek-and-local-retrieval-models/specs/local-retrieval-models/spec.md`

工作目录：

```text
/Users/kekeju/Documents/work/4project/oncall
```

注意：当前 `oncall` 目录没有可用的 `.git` 元数据，`git status` 会报告“not a git repository”。不要因此删除或回滚文件。

## 3. 已完成的实现

### 3.1 模型边界

已将远程 Chat 和本地检索模型拆开：

- `apps/backend/src/super_ai/llm/config.py`
  - `LlmProviderConfig`：远程 Chat 配置
  - `LocalEmbeddingConfig`：本地 Embedding 配置
  - `LocalRerankConfig`：本地 Rerank 配置
  - 从 `llm` 与 `retrievalModels` 两个配置区读取
- `apps/backend/src/super_ai/llm/local_retrieval.py`
  - `LocalBgeEmbeddingModel`
  - `LocalBgeRerankModel`
  - 模型惰性加载，推理通过 `asyncio.to_thread` 执行
  - 包含向量数量、维度及 rerank 参数校验
- `apps/backend/src/super_ai/llm/provider.py`
  - Chat 使用 `ChatOpenAI` 连接 DeepSeek
  - Embedding/Rerank 改为本地 BGE 工厂
  - `OpenAICompatibleProvider` 为当前实现
  - 暂时保留 `QwenOpenAIProvider` 别名，避免旧调用方直接损坏
- `apps/backend/src/super_ai/llm/__init__.py`
  - 已导出新的配置和实现类型

### 3.2 依赖

`apps/backend/pyproject.toml` 已加入：

```text
sentence-transformers>=5.0.0,<6.0.0
```

已经运行 `uv lock` 和 `uv sync`，锁文件已更新，安装了 `sentence-transformers`、`torch`、`transformers` 等依赖。

尚未主动下载 BGE 权重。第一次真正执行知识索引或 rerank 时会从 Hugging Face 下载，可能耗时较久并占用较多磁盘空间。

### 3.3 配置

已更新：

- `config/project.template.json`
- `config/user.project.template.json`
- 本地忽略文件 `config/project.json`
- 本地忽略文件 `config/user.project.json`

当前有效配置意图：

```json
{
  "llm": {
    "provider": "deepseek-openai",
    "baseUrl": "https://api.deepseek.com",
    "chatModel": "deepseek-flash"
  },
  "retrievalModels": {
    "embedding": {
      "provider": "sentence-transformers",
      "model": "BAAI/bge-m3",
      "dimensions": 1024,
      "device": "cpu",
      "batchSize": 8,
      "normalize": true
    },
    "rerank": {
      "provider": "sentence-transformers",
      "model": "BAAI/bge-reranker-v2-m3",
      "device": "cpu",
      "batchSize": 8
    }
  }
}
```

用户已在 `config/user.project.json` 填写 API Key。该文件被 Git 忽略。禁止在命令输出、日志、测试、交接信息或聊天回复中打印 Key。

用户曾在聊天中直接粘贴过一个 Key；不要复述它。如果当前本地 Key 与被粘贴的 Key 相同，应提醒用户在 DeepSeek 控制台轮换。

### 3.4 文档

已同步：

- `AGENTS.md`
- `README.md`
- `docs/setup-macos.md`
- `docs/setup-linux.md`
- `docs/setup-windows.md`

内容已经从 Qwen/百炼改为 DeepSeek Chat，并说明本地 BGE 首次使用会下载模型。

### 3.5 测试

新增：

- `apps/backend/tests/test_local_retrieval_models.py`

更新：

- `apps/backend/tests/test_llm_provider.py`
- `apps/backend/tests/test_environment_examples.py`
- `apps/backend/tests/test_readiness_api.py`

已经通过：

```bash
cd /Users/kekeju/Documents/work/4project/oncall/apps/backend
uv run ruff check .
uv run pyright
uv run pytest \
  tests/test_llm_provider.py \
  tests/test_local_retrieval_models.py \
  tests/test_readiness_api.py \
  tests/test_document_indexing.py \
  tests/test_document_indexing_api.py \
  tests/test_knowledge_retrieval_tool.py \
  tests/test_knowledge_retrieval_api.py
```

结果：目标测试共 `40 passed`，Ruff 与 Pyright 均通过。

OpenSpec 校验也已通过：

```bash
cd /Users/kekeju/Documents/work/4project/oncall
npx --yes @fission-ai/openspec@latest validate \
  2026-11-04-split-deepseek-and-local-retrieval-models \
  --type change
```

另一次环境与 readiness 测试中有 `7 passed, 1 failed`。失败与本次模型拆分无关：本地实际配置中 `external-test-prometheus` 的 `alertsApi` 为空。不要为了让测试变绿而随意填写虚假外部地址。

## 4. 当前中断点

最后一步是重启后端并验证 DeepSeek readiness。

上一次调用 `/ready` 时请求异常地长时间没有返回，工具调用最终被用户中止。因此：

- 不能宣称 DeepSeek readiness 已通过。
- 不能确认是 API Key、模型名、外部网络、DeepSeek 服务还是 readiness 超时链路的问题。
- 不要再次直接执行长达 120 秒以上的阻塞请求。
- 先做 3～10 秒的短超时、脱敏探测，再决定是否修改配置或代码。

截至编写本文档时，端口 `8000`、`5173`、`3000` 均未检测到监听进程；应按“服务当前未运行”处理。Docker 状态因当前沙箱无权访问 Docker socket，未能重新确认。

## 5. 新 Session 的推荐恢复步骤

### 第一步：检查本地配置，但绝不打印 Key

只输出布尔值和非敏感字段，例如确认：

- `apiKeyConfigured == true`
- Provider 为 `deepseek-openai`
- Base URL 为 `https://api.deepseek.com`
- Chat model 为 `deepseek-flash`
- Embedding 维度与 pgvector 维度都是 `1024`

### 第二步：确认基础设施

```bash
cd /Users/kekeju/Documents/work/4project/oncall
docker compose -f infra/compose.yaml up -d --wait postgres
docker compose -f infra/compose.yaml ps
```

访问 Docker socket 可能需要用户批准。

### 第三步：启动后端

```bash
cd /Users/kekeju/Documents/work/4project/oncall/apps/backend
uv run alembic upgrade head
uv run uvicorn super_ai.api.app:create_app \
  --factory --host 127.0.0.1 --port 8000
```

先只检查快速健康接口：

```bash
curl --max-time 5 http://127.0.0.1:8000/health
```

### 第四步：短超时验证 DeepSeek

使用一个读取本地 JSON 的临时脚本发起最小 Chat Completions 请求：

- 总超时控制在 10 秒左右
- Authorization 从配置文件读取
- 只输出 HTTP 状态码、错误类型和错误代码
- 不输出请求头、完整响应体或 API Key

若短探测成功，再调用：

```bash
curl --max-time 20 http://127.0.0.1:8000/ready
```

若失败，先根据脱敏的 HTTP 状态分类：

- `401/403`：Key 或账户权限问题
- `404` 或模型不存在：核对当前账号可用模型名
- `429`：额度或限流
- 连接/解析超时：网络或服务端问题
- 直接 API 成功但 `/ready` 失败：检查 readiness 实现和 `ChatOpenAI` 参数

不要未经证据就把 `deepseek-flash` 改成其他模型。

### 第五步：收尾 OpenSpec

`tasks.md` 的勾选状态尚未同步，虽然 1.1～2.3 的实现和验证基本已完成。应先复核文件与测试，再勾选：

- 1.1～1.4
- 2.1～2.3

只有 DeepSeek readiness 真正通过后，才能勾选 2.4。随后运行完整的相关校验，并根据项目流程决定是否归档该 change。

## 6. 仍需特别注意

- 本地 BGE 使用 CPU，首次加载慢是正常现象；不要把模型加载放到模块 import 阶段。
- `BAAI/bge-m3` 输出 1024 维，必须与 `vectorStore.vectorDimension` 及 pgvector schema 保持一致。
- 不要恢复旧的远程 Qwen Embedding/Rerank 配置。
- 不要把 `config/project.json`、`config/user.project.json` 或任何密钥提交到仓库。
- 不要删除现有的 `QwenOpenAIProvider` 兼容别名，除非先确认全仓调用方已经迁移。
- `trainwatch` 尚未开始嵌入；当前先把 Oncall 的模型与运行链路稳定下来。
- 当前目录存在用户既有修改，禁止使用破坏性 Git 命令或批量覆盖。

## 7. 可直接交给新 Session 的首条提示词

```text
请继续 /Users/kekeju/Documents/work/4project/oncall 的工作。先完整阅读 AGENTS.md 和 HANDOFF.md，再查看 openspec/changes/2026-11-04-split-deepseek-and-local-retrieval-models。不要打印任何 API Key。当前需要从“DeepSeek readiness 尚未验证”处继续：先用 3～10 秒短超时做脱敏探测，确认失败分类，然后启动并验证后端；不要再执行长时间阻塞请求。验证成功后同步 tasks.md，并向我说明如何使用系统。
```
