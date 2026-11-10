## 1. 契约与配置

- [x] 1.1 在 `packages/api-contracts` 新增 live-demo 类型、OpenAPI 路径与 `BUSINESS_RATE_LIMITED` 错误码，并补契约测试
- [x] 1.2 后端错误目录同步 `BUSINESS_RATE_LIMITED`
- [x] 1.3 配置模板新增 `liveDemo` 段，并实现加载与校验

## 2. 后端

- [x] 2.1 新增 `live_demo_runs` ORM 模型与 Alembic 迁移
- [x] 2.2 实现运行仓储、限流计数、运行令牌哈希与最近成功运行查询
- [x] 2.3 实现场景白名单、无根因告警构造与 Alertmanager 发布
- [x] 2.4 新增 `GET /live-demo`、`POST /live-demo/runs`、`POST /live-demo/runs/{runId}:stream`
- [x] 2.5 诊断服务对 `liveDemo` 任务跳过案例沉淀
- [x] 2.6 补充测试：令牌校验、白名单、限流、服务账号 owner、跳过案例、Bearer 隔离、迁移
- [x] 2.7 新增与 CloudWatch 定时日志对应的 `checkout-db-pool-exhausted` 场景与 SOP（`--profile live-drill`）
- [x] 2.8 诊断节点内事件通过 LangGraph custom 流即时推送并按 id 去重，补充顺序与去重测试

## 3. 前端

- [x] 3.1 新增 live-demo 客户端与 `/live` 页面（场景、触发、实时阶段、证据、报告、额度、兜底）
- [x] 3.2 公开介绍页主操作指向 `/live`
- [x] 3.3 补充 Vitest：路由公开访问、触发与事件渲染、限流与兜底展示

## 4. 文档与验证

- [x] 4.1 更新 README 与运维文档中的演练准备步骤
- [x] 4.2 运行 Ruff、Pyright、pytest（按文件逐个运行全部通过；单进程全量运行曾卡住，待排查）、前端 typecheck/test/build、契约测试与 OpenSpec 校验
- [x] 4.3 本地真实触发一次演练并截图确认
