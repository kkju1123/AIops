## 1. 关闭思考

- [x] 1.1 `create_chat_model(thinking=False)` 发送 DeepSeek `thinking: disabled`，补充 provider 测试
- [x] 1.2 诊断计划与报告调用关闭思考；计划提示只携带 SOP 摘要
- [x] 1.3 实测计划与报告耗时（计划 59s→5～8s，报告 32s→9～12s，整体 132s→37～51s）

## 2. 流式报告

- [x] 2.1 报告节点批量输出 aiops `content.delta`，保留最终 `report` 与回退
- [x] 2.2 共享契约说明 aiops 通道的 `content.delta`；工作台 AIOps 解析器容忍该事件
- [x] 2.3 演练页边生成边展示报告，补充测试

## 3. 模型预热

- [x] 3.1 lifespan 在演练开启时后台预热 Embedding 与 Rerank，失败只记日志，补充测试

## 4. 故障模拟器

- [x] 4.1 新增 `super_ai.simulator`：场景化日志与指标生成器、FastMCP stdio Server
- [x] 4.2 `liveDemo.observability` 配置与模拟器连接；诊断服务对 `simulatedFault` 任务使用模拟器两步计划
- [x] 4.3 开放全部场景并补充 SOP 索引；页面与报告标注模拟数据
- [x] 4.4 测试：生成器可复现与场景对应、MCP 工具端到端、工作台诊断不使用模拟器、演练 API

## 5. 文档与验证

- [x] 5.1 更新 README、运维文档与配置模板
- [x] 5.2 运行 Ruff、Pyright、pytest（按文件逐个运行全部通过）、前端 typecheck/test/build、契约测试、docs build 与 OpenSpec 校验
- [x] 5.3 本地实测：模拟器模式热状态 22～25s 完成（原 80～130s），桌面与 390px 窄屏截图无横向溢出
