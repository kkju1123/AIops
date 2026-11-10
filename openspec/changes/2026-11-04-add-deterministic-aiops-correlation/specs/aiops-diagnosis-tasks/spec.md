## MODIFIED Requirements

### Requirement: Plan-Execute-Replan diagnostic graph

后端 SHALL 通过具有命名 `Planner`、`Executor`、`Replanner`、`Correlator` 和 `Report` 节点的 LangGraph 工作流执行每个经过身份验证的 AIOps 诊断。`Correlator` SHALL 为不调用 LLM 的确定性节点。

#### Scenario: Diagnostic follows the graph lifecycle

- **WHEN** 已认证的 user 启动诊断任务
- **THEN** 后端 MUST 将任务保存为运行中，并在终端成功或失败前执行 Planner、Executor、Replanner、Correlator 和 Report 节点

#### Scenario: Replanner continues only when warranted

- **WHEN** Executor 仍有其他限定诊断步骤且之前执行未失败
- **THEN** Replanner MUST 返回 Executor；否则它 MUST 返回 Correlator

### Requirement: Evidence-based execution and reporting

Executor SHALL 仅调用真实注册的 MCP 工具、tenant 范围的知识检索工具或本地确定性工具。Correlator SHALL 仅从诊断查询、标准化告警、SOP 命中和真实执行证据生成可解释根因候选。Report SHALL 仅基于返回证据和这些候选得出结论。

#### Scenario: Deterministic candidate is supported by evidence

- **WHEN** 告警或成功工具证据命中一个或多个已知故障签名
- **THEN** Correlator MUST 生成稳定排序的候选，并包含规则 ID、分数、置信等级、匹配信号和关联证据 ID

#### Scenario: Query or SOP alone matches a signature

- **WHEN** 只有用户查询或 SOP 文本命中故障签名，告警和成功工具证据均未命中
- **THEN** Correlator MUST NOT 将其输出为根因候选

#### Scenario: No deterministic candidate is supported

- **WHEN** 告警和真实工具证据未支持任何已知签名
- **THEN** Report MUST 明确根因证据不足，不得由 LLM 创造新的已确认根因

### Requirement: Diagnostic workflow writes evidence-chain records

LangGraph Planner、Executor、Replanner、Correlator 和 Report 节点 SHALL 通过诊断证据链存储库边界持续保留其计划、执行、候选、证据和报告的来源信息。

#### Scenario: Correlation artifacts are persisted

- **WHEN** Correlator 完成候选分析
- **THEN** 后端 MUST 保存 correlator 步骤、checkpoint、确定性分析证据，并在最终报告 payload 中保存候选列表

