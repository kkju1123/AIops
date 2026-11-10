## Why

简历访客（面试官）打开项目链接后，现有公开介绍页和 `/demo` 导览只有静态文字说明，并大量强调“不调用真实服务”。访客无法在 30 秒内理解系统做什么，也无法亲手看到真实诊断。项目所有者希望面试官无需注册登录，点一个按钮就能触发一次真实的故障与诊断流程。

## What Changes

- 新增无需登录的 `/live` 实时故障演练页：选择场景，点击“触发故障”后实时展示告警、SOP 检索、计划、CloudWatch 日志查询、重规划和最终报告。
- 新增公开 API：`GET /live-demo` 返回场景、额度和最近一次真实成功运行；`POST /live-demo/runs` 发布真实告警并创建真实诊断；`POST /live-demo/runs/{runId}:stream` 使用一次性运行令牌读取该次运行的 SSE。
- 演练使用服务端配置的专用服务账号执行，访客不获得任何用户会话，只获得单次运行的只读令牌（服务端只保存哈希）。
- 按访客（IP 哈希）每小时限次、全站每日限次、并发上限保护 DeepSeek 与 AWS 费用，超限返回新错误码 `BUSINESS_RATE_LIMITED`（HTTP 429）。
- 演练运行不沉淀为故障案例，避免污染服务账号知识库。
- 公开介绍页的主操作改为进入实时演练。

## Capabilities

### New Capabilities

- `live-incident-drill`: 面向匿名访客、带限流与费用保护的一键真实故障诊断演练。

### Modified Capabilities

- 无。现有认证工作台、诊断 API 与公开导览的行为保持不变。

## Impact

- 后端：新增 `live_demo` 模块、`live_demo_runs` 表与 Alembic 迁移、公开路由、错误码、`liveDemo` 配置段；诊断服务在演练任务上跳过案例沉淀。
- 共享契约：新增 live-demo 类型、OpenAPI 路径和错误码。
- 前端：新增 `/live` 页面、客户端与测试；公开介绍页 CTA 调整。
- 配置与文档：模板新增 `liveDemo`，README 与运维文档说明如何准备服务账号和 SOP。
