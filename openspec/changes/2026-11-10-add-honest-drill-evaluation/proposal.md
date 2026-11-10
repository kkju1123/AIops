## Why

故障演练的诊断结果目前不可信：每个场景都有一份专属 SOP，其中“已知根因假设”一节原样写着该场景的根因；CloudWatch fixture 日志带有 `root_cause_hint` 字段，告警 description 也拼接了根因，告警 annotation 还直接指向对应 SOP。诊断只要检索到对应 SOP 就能“抄”出答案。同时项目没有任何评测，无法回答“诊断准确率是多少”。

## What Changes

- 用 7 份按故障类别编写的通用排查手册（runbook）替换 11 份场景专属 SOP。每份手册列出该类故障的多个常见根因假设及区分方法，不针对任何具体场景。
- 场景的标准根因只作为评测的标准答案保存在 fixture 中，不再出现在知识文档、日志、告警或模拟器输出里。
- 故障模拟器为每个场景输出能指向根因、但不直接写出根因的线索日志（例如 TLS 握手耗时、持锁事务、慢 SQL），并加入与本次故障无关的干扰事件（例如较早的一次发布）。日志工具结果新增按事件聚合的 `notableEvents` 摘要。
- 演练告警不再携带 `incident_id` 标签。
- SOP 种子脚本改为上传类别手册，并删除服务账号知识库中的旧场景 SOP（`<incident_id>-sop.md`）。
- 新增离线评测：`uv run python scripts/evaluate_drill_diagnoses.py` 在进程内对每个场景重复运行真实诊断（真实 DeepSeek、真实检索、故障模拟器），用 LLM 评审对照标准根因打分，统计根因准确率、手册检索命中率、工具调用数与耗时，输出 JSONL 原始结果和 Markdown 汇总表。
- 在 `docs/evaluation/` 记录改造前（存在泄露）和改造后的评测结果，并在 README 中展示。

## Capabilities

### New Capabilities

- `drill-diagnosis-evaluation`: 演练诊断的离线评测、评分规则与结果记录，以及演练数据不泄露标准答案的约束。

### Modified Capabilities

- `ecommerce-aiops-fixtures`: Java 电商 fixture 的 SOP 改为按类别的通用排查手册，根因只作为评测标准答案。

## Impact

- 后端：`aiops/fixtures.py`（类别手册、线索、标准答案）、`simulator/faults.py`（线索日志、干扰事件、`notableEvents`）、`live_demo.py`（告警标签）、新模块 `evaluation/`、`api/app.py`（为离线评测暴露诊断运行器构造函数）。
- 脚本：`scripts/seed_ecommerce_aiops_sop.py`（`--profile runbooks`、清理旧 SOP）、新增 `scripts/evaluate_drill_diagnoses.py`。
- 文档：README、运维文档、`docs/evaluation/`。
- 不改变 HTTP API、SSE 事件契约和前端。
