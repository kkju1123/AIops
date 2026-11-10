# aiops-evidence-chain Specification Delta

## MODIFIED Requirements

### Requirement: Tool log evidence is provider normalized

后端 SHALL 保存真实工具原始结果，并 SHALL 为报告与 operator 界面生成包含 provider、kind、region、source、tool、recordCount、records、query 和 queryId 的有界标准化摘要。

#### Scenario: CloudWatch returns log records
- **WHEN** `execute_cwl_insights_batch` 返回真实记录
- **THEN** 证据摘要 MUST 标记 provider 为 `aws-cloudwatch` 并保留真实日志组、区域、时间戳、消息和可用关联 ID

#### Scenario: Tool output cannot be parsed
- **WHEN** 真实工具返回未识别结构
- **THEN** 摘要 MUST 标记未解析并保留有界文本，MUST NOT 构造不存在的记录
