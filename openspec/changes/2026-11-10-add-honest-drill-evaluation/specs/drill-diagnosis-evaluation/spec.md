## ADDED Requirements

### Requirement: Drill data does not reveal ground truth
演练使用的知识文档、模拟器日志与指标、告警 payload SHALL NOT 包含任何场景标准根因的原文；标准根因 MUST 只作为评测答案保存在 fixture 中。

#### Scenario: Runbooks are category-level
- **WHEN** 构建演练服务账号的排查手册
- **THEN** 每份手册 MUST 对应一个故障类别并列出多个候选根因，且 MUST NOT 包含任何场景 `root_cause` 原文

#### Scenario: Simulator output hides the answer
- **WHEN** 模拟器为任一场景生成日志与指标
- **THEN** 输出 MUST NOT 包含该场景 `root_cause` 原文，且 MUST 至少包含一条该场景定义的线索日志

#### Scenario: Alerts hide the answer
- **WHEN** 构建演练告警或 CloudWatch fixture 告警
- **THEN** 告警 MUST NOT 包含场景 `root_cause` 原文、场景专属 SOP 标识或 `incident_id` 演练标签

### Requirement: Simulator surfaces notable events
模拟器日志工具 SHALL 在结果摘要中按事件聚合返回非常规事件（`notableEvents`），包括计数、级别、首末时间与示例消息。

#### Scenario: One-off event outside the record limit
- **WHEN** 一次性线索事件早于返回的最新日志记录
- **THEN** 该事件 MUST 仍出现在 `notableEvents` 中

### Requirement: Offline drill diagnosis evaluation
系统 SHALL 提供显式命令，对演练场景重复运行真实诊断，并用 LLM 评审对照标准根因打分。命令 MUST NOT 在应用启动时运行，MUST NOT 发布告警，评测任务 MUST 带 `evaluation` 标记且没有演练发起人。

#### Scenario: Run is graded
- **WHEN** 某次评测诊断完成
- **THEN** 结果 MUST 记录场景、评审结论（`correct`/`partial`/`incorrect`）与理由、得分、检索到的文档、期望文档是否命中、工具调用数、证据数、耗时与任务状态

#### Scenario: Failed diagnosis is scored
- **WHEN** 诊断失败或没有报告
- **THEN** 该次运行 MUST 记为 `incorrect` 并计入准确率，不得被跳过

#### Scenario: Summary is produced
- **WHEN** 评测结束
- **THEN** 命令 MUST 输出 JSONL 原始结果与按场景汇总的 Markdown 表，包含总体根因准确率与检索命中率

#### Scenario: Unparseable judge output
- **WHEN** 评审输出无法解析为预期 JSON
- **THEN** 该次运行 MUST 记为 `incorrect` 并保留原始评审输出摘要
