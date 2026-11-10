## 1. 评测基础

- [x] 1.1 新增 `super_ai.evaluation`：评审 prompt 与结果解析、单次运行记录、汇总统计、Markdown 汇总表
- [x] 1.2 `api/app.py` 暴露评测用的诊断运行器与演练服务构造函数
- [x] 1.3 新增 `scripts/evaluate_drill_diagnoses.py`（场景、重复次数、输出目录参数）
- [x] 1.4 单元测试：评审解析、汇总、Markdown、检索命中判断
- [x] 1.5 在改造前运行一次评测，记录基线（存在泄露）

## 2. 去除答案泄露

- [x] 2.1 fixture：新增 7 份类别手册，场景映射到手册；移除场景 SOP 渲染
- [x] 2.2 CloudWatch fixture 日志去掉 `root_cause_hint`，告警 description 去掉根因，annotation 改为类别手册 ID
- [x] 2.3 演练告警去掉 `incident_id` 标签
- [x] 2.4 模拟器：场景线索日志、干扰事件、`notableEvents`
- [x] 2.5 种子脚本：`--profile runbooks`，删除旧场景 SOP
- [x] 2.6 测试：手册/日志/告警/模拟器输出不含任何标准根因；每个场景都有线索；`notableEvents` 覆盖一次性事件

## 3. 评测与文档

- [x] 3.1 重新索引服务账号知识库并运行改造后评测
- [x] 3.2 `docs/evaluation/` 记录方法、改造前后结果与局限；README 展示结果
- [x] 3.3 更新 README 与运维文档中的种子脚本用法
- [x] 3.4 运行 Ruff、Pyright、pytest、docs build；同步 WIKI
- [ ] 3.5 安装 OpenSpec CLI 后运行 `openspec validate --all`（本机未安装，尚未执行）
