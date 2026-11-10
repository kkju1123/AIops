# 演练诊断评测

这份文档记录故障演练诊断的离线评测方法与结果。评测命令：

```bash
cd apps/backend
uv run python scripts/evaluate_drill_diagnoses.py --repeats 3 --label <标签>
```

原始结果（每次诊断一行 JSONL）与汇总表写入 `apps/backend/var/evaluations/<时间>-<标签>/`，该目录不提交。

## 方法

- **被评对象**：演练使用的真实诊断链路：检索知识库 → DeepSeek 排列计划 → 通过 MCP 调用故障模拟器查询日志与指标 → DeepSeek 写报告。评测脚本在进程内直接运行诊断，不发布告警、不启动后台 worker。
- **场景**：11 个故障场景，每个运行 3 次，共 33 次诊断。
- **标准答案**：每个场景在 fixture 中保存一条标准根因（`JavaEcommerceIncident.root_cause`），诊断过程看不到它。
- **评分**：用同一 DeepSeek 配置（关闭深度思考）作为评审，对照标准根因给出 correct / partial / incorrect，分别计 1 / 0.5 / 0 分。诊断失败或没有报告直接计为 incorrect。
- **手册命中**：检索返回的知识文档中是否包含该场景期望的文档。

## 结果一：改造前（场景 SOP 中写着根因）

2026-11-10。每个场景有一份专属 SOP，其中“已知根因假设”一节原样写着标准根因；模拟器日志只包含症状（异常类型、超时、错误率），没有能证实根因的证据。

| 场景 | 次数 | 根因得分 | 正确 / 部分 / 错误 | 手册命中率 | 平均工具调用 | 平均耗时 (s) |
|---|---|---|---|---|---|---|
| checkout-db-pool-exhausted | 3 | 50% | 0 / 3 / 0 | 100% | 2.0 | 31.9 |
| java-ecom-payment-gateway-timeout | 3 | 50% | 0 / 3 / 0 | 100% | 2.0 | 26.7 |
| java-ecom-inventory-lock-wait | 3 | 50% | 0 / 3 / 0 | 100% | 2.0 | 26.1 |
| java-ecom-order-db-pool-exhausted | 3 | 33% | 0 / 2 / 1 | 100% | 2.0 | 28.5 |
| java-ecom-cart-redis-latency | 3 | 0% | 0 / 0 / 3 | 100% | 2.0 | 29.9 |
| java-ecom-gateway-circuit-open | 3 | 50% | 0 / 3 / 0 | 100% | 2.0 | 27.5 |
| java-ecom-promotion-cpu-saturation | 3 | 0% | 0 / 0 / 3 | 100% | 2.0 | 27.6 |
| java-ecom-order-kafka-lag | 3 | 17% | 0 / 1 / 2 | 100% | 2.0 | 26.3 |
| java-ecom-search-es-timeout | 3 | 17% | 0 / 1 / 2 | 100% | 2.0 | 26.5 |
| java-ecom-auth-jwk-refresh | 3 | 50% | 0 / 3 / 0 | 100% | 2.0 | 26.2 |
| java-ecom-fulfillment-provider-503 | 3 | 50% | 0 / 3 / 0 | 100% | 2.0 | 25.8 |
| **全部场景** | 33 | 33% | 0 / 22 / 11 | 100% | 2.0 | 27.6 |

**解读**：答案就写在检索到的 SOP 里，但 33 次诊断没有一次被判为正确。报告普遍引用了 SOP 中的根因假设，同时说明“日志中没有能证实该假设的证据，无法确认根因”。诊断提示词要求结论必须有证据支持，模型照做了。所以当时的问题不只是答案泄露，更是**模拟器没有提供能推断根因的证据**。

## 结果二：改造后（类别手册 + 线索日志）

2026-11-10。改动：

- 11 份场景 SOP 替换为 7 份按故障类别编写的排查手册。每份列出 4 到 5 个候选根因及区分证据，不包含任何场景的标准根因，真实根因也不固定排在第一位。
- CloudWatch fixture 日志删除 `root_cause_hint`，告警 description 删除根因，演练告警删除 `incident_id` 标签。
- 模拟器为每个场景输出指向根因、但不直接写出根因的线索日志（例如 TLS 握手耗时、未提交的长事务、无 LIMIT 的慢 SQL、未知 JWT kid 与 DNS 解析失败），同时加入无关的干扰事件（较早的一次发布、GC 停顿）。日志工具结果新增按事件聚合的 `notableEvents`。

| 场景 | 次数 | 根因得分 | 正确 / 部分 / 错误 | 手册命中率 | 平均工具调用 | 平均耗时 (s) |
|---|---|---|---|---|---|---|
| checkout-db-pool-exhausted | 3 | 100% | 3 / 0 / 0 | 0% | 2.0 | 33.6 |
| java-ecom-payment-gateway-timeout | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 27.9 |
| java-ecom-inventory-lock-wait | 3 | 100% | 3 / 0 / 0 | 0% | 2.0 | 29.0 |
| java-ecom-order-db-pool-exhausted | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 27.5 |
| java-ecom-cart-redis-latency | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 27.1 |
| java-ecom-gateway-circuit-open | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 26.3 |
| java-ecom-promotion-cpu-saturation | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 26.7 |
| java-ecom-order-kafka-lag | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 28.3 |
| java-ecom-search-es-timeout | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 28.0 |
| java-ecom-auth-jwk-refresh | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 27.1 |
| java-ecom-fulfillment-provider-503 | 3 | 100% | 3 / 0 / 0 | 100% | 2.0 | 27.6 |
| **全部场景** | 33 | 100% | 33 / 0 / 0 | 82% | 2.0 | 28.1 |

**解读**：

- 根因从“说不清”变成全部答对，说明诊断链路能够读懂证据、排除干扰项并给出有依据的结论。
- **满分也说明这套场景太简单。** 每个场景的线索都在告警服务自己的日志里，查一次日志就能看到；当前计划固定为“查日志 + 查指标”两步，这套评测还测不出 agent 主动寻找证据的能力。
- **检索存在真实缺陷**：`checkout-db-pool-exhausted` 和 `java-ecom-inventory-lock-wait` 的告警检索不到数据库手册，排在前面的是下游依赖、缓存手册。这两个场景仍然答对，说明在当前场景下手册不是决定因素。

## 已知局限

- 评审模型与被评模型同源（都是 DeepSeek），可能偏宽松；每次评审都保留了理由，便于人工复核。
- 模拟器的日志与指标是按场景生成的合成数据，不是真实系统。
- 每个场景只运行 3 次，样本量小。
- 没有统计 token 用量与费用。

## 下一步

1. 加入更难的场景：线索在另一个服务（例如告警在网关，线索在下游库存服务的日志里），或者需要扩大时间窗口才能看到。
2. 把 replanner 改成由 LLM 读取证据后决定是否继续查询，再用更难的场景做对比实验。
3. 修复检索：数据库类告警应能检索到数据库手册。
