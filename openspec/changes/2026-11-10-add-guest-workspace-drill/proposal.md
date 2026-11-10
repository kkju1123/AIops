## Why

面试官目前看到三个互不相连的页面：落地页、全是“PREVIEW ONLY”说明卡片的 `/demo` 公开导览，以及孤立的 `/live` 实时演练页。真实功能都在需要登录的工作台里，面试官进不去；演练跑完一份报告就结束，结果没有出现在真实的智能诊断界面中，整体像一个玩具。

## What Changes

- 新增访客身份：`POST /auth/guest` 为每位访客签发独立的短期临时账号（`accountKind=guest`），复用现有的 Argon2 和 token 哈希会话机制。不共享账号，访客之间数据隔离。
- 访客权限：可以浏览工作台、触发演练、查看自己触发的演练诊断、在限额内对话、只读查看演练 SOP 库。不能新建工作台诊断、上传或删除知识、管理 MCP 连接、把诊断保存为知识。
- 故障演练并入工作台：新增 `/drill` 路由，作为导航第一项（标注“模拟”）。未登录访问 `/drill` 时自动创建访客会话；`/live` 重定向到 `/drill`。
- 演练结果进入智能诊断：演练运行记录发起人（`requester_user_id`）。发起人可以在 `/aiops` 的历史中看到并打开这次诊断，复用现有时间线、报告和证据链组件，并带“故障演练 · 模拟数据”标识。
- 新增 `GET /live-demo/sop-documents` 与 `GET /live-demo/sop-documents/{documentId}`，让已登录用户只读查看演练使用的 SOP 文档。
- 删除 `/demo` 静态公开导览，落地页主按钮改为“进入工作台”。
- 顶栏显示访客模式和演练环境标识；访客可以随时切换为所有者登录。
- 修订数据边界：故障模拟器数据只能出现在演练产生的诊断中，必须带“故障模拟器生成”标识，不得作为工作台诊断证据，也不得进入知识库。

## Capabilities

### New Capabilities

- `guest-workspace`: 访客身份、访客权限边界、工作台内的故障演练、演练诊断在智能诊断中的只读呈现和演练 SOP 库。

### Modified Capabilities

- 无（`live-incident-drill` 与 `public-portfolio-demo` 仍在未归档 change 中；本 change 用新增需求覆盖 `/demo` 移除与 `/live` 重定向）。

## Impact

- 后端：`auth/`（访客账号、会话有效期）、新模块 `guest_access.py`、`live_demo.py`（发起人）、`api/app.py`（访客路由、权限依赖、诊断读取解析、SOP 只读接口、对话限额）、Alembic 新迁移（`users.account_kind`、`live_demo_runs.requester_user_id`）。
- 共享契约：`AuthUser.accountKind`、`AiopsDiagnosticSummary.origin/simulated`、演练运行 `diagnosticId`、SOP 文档类型与 OpenAPI 路径。
- 前端：路由、导航、`WorkspaceLayout`、演练页、智能诊断、知识库、MCP 页面的访客状态；删除 `PublicDemoView`。
- 配置：新增 `guestAccess` 段；文档、README、`AGENTS.md` 数据边界条款同步更新。
