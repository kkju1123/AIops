## Context

演练诊断链路：告警 → 检索 SOP → LLM 排列计划 → 通过 MCP 调用故障模拟器查日志与指标 → LLM 写报告。检索与报告都会把 SOP 内容交给模型，因此 SOP 里的场景根因等同于把答案直接给了模型。

## Goals / Non-Goals

**Goals**
- 知识文档、日志、告警、模拟器输出中都不出现任何场景的标准根因原文。
- 根因可以从证据推断：每个场景至少有一条指向根因的线索。
- 评测可重复运行，结果可追溯（原始 JSONL + 汇总表），并记录改造前后对比。

**Non-Goals**
- 不改诊断图结构（replanner 动态化另开 change）。
- 不接入真实微服务系统，不改前端与 API 契约。

## Decisions

1. **类别手册而不是删除 SOP。** 真实团队的 runbook 本来就是按故障类别写、列出多个常见原因。手册中包含真实根因的通用表述作为候选之一，但同时列出其他候选和区分证据，模型必须靠证据选择。
2. **标准答案留在 fixture。** `JavaEcommerceIncident.root_cause` 保留，仅供评测评审使用；新增测试断言它不出现在手册、模拟器日志、告警 payload 中。
3. **线索放进 `message`。** 诊断对模拟器结果做了字段裁剪，只保留固定字段，因此线索内容写在 `message` 中，并通过 `notableEvents` 聚合让较早出现的一次性事件（如规则发布）在 20 条日志上限之外也能被看到。
4. **进程内评测。** 演练 HTTP 接口受访客/全站限流且会发布 Alertmanager 告警；评测脚本通过 `create_app` 构建同一套诊断运行器，在进程内直接运行诊断任务，不启动后台 worker，也不发布告警。评测任务归演练服务账号所有，`input_payload.evaluation` 标记来源，没有发起人，访客看不到。
5. **LLM 评审。** 评审使用同一 DeepSeek 配置、关闭深度思考，输出 `correct / partial / incorrect` 与理由；分数 1 / 0.5 / 0。评审模型与被评模型同源是已知局限，在结果文档中注明。
6. **检索命中。** 记录检索返回的文档文件名，判断期望文档是否在其中（hit@k，k 为检索返回数量）。改造前期望文档是场景 SOP，改造后是类别手册。

## Risks / Trade-offs

- 改造后准确率预计下降，这是预期结果，文档中如实记录。
- LLM 评审存在噪声：每个场景重复多次运行并保留评审理由，便于人工复核。
- 评测会产生真实 DeepSeek 费用；脚本默认每场景 3 次，可通过参数调整。

## Migration Plan

运行 `uv run python scripts/seed_ecommerce_aiops_sop.py --profile runbooks` 上传类别手册并删除旧场景 SOP；旧的 `java-ecommerce`、`live-drill` profile 移除。
