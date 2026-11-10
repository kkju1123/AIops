## 1. 后端访客身份

- [x] 1.1 Alembic 迁移：`users.account_kind`（默认 `member`）与 `live_demo_runs.requester_user_id`，补充迁移测试
- [x] 1.2 `guestAccess` 配置加载与校验；更新两个配置模板
- [x] 1.3 `AuthService.create_guest` 与访客会话有效期；`POST /auth/guest`；用户 payload 增加 `accountKind`
- [x] 1.4 测试：访客创建、限额、过期、不能用密码登录、关闭时不可用

## 2. 访客权限与演练归属

- [x] 2.1 `_member_user` 依赖限制访客写操作，补充权限测试
- [x] 2.2 访客对话每小时限额，补充测试
- [x] 2.3 演练运行记录发起人；诊断读接口按发起人解析 owner；列表合并演练任务；`origin`/`simulated` 字段
- [x] 2.4 `GET /live-demo/sop-documents` 与详情接口（需登录、只读）
- [x] 2.5 测试：发起人可读、其他访客不可读、匿名演练不出现在任何人的历史、SOP 只读

## 3. 共享契约

- [x] 3.1 `AuthUser.accountKind`、`AiopsDiagnosticSummary.origin/simulated`、演练 `diagnosticId`、SOP 文档类型、OpenAPI 路径
- [x] 3.2 契约测试

## 4. 前端

- [x] 4.1 auth client/store：`enterAsGuest`、`isGuest`
- [x] 4.2 路由：`/drill` 子路由与自动访客会话，`/live` → `/drill`，移除 `/demo`
- [x] 4.3 导航“故障演练”入口与“模拟”标识；顶栏访客模式与演练环境标识
- [x] 4.4 演练页并入工作台，完成后跳转智能诊断
- [x] 4.5 智能诊断支持 `diagnosticId` 查询参数、访客只读入口、演练来源标识
- [x] 4.6 知识库访客只读 SOP 库；MCP 页面访客只读说明
- [x] 4.7 落地页按钮改为进入工作台；删除 `PublicDemoView`
- [x] 4.8 前端测试：store、路由守卫、导航、演练页、访客状态

## 5. 文档与验证

- [x] 5.1 更新 README、运维文档、`AGENTS.md` 数据边界条款，同步 WIKI
- [x] 5.2 运行 Ruff、Pyright、pytest、前端 typecheck/test/build、契约测试、docs build
- [x] 5.3 本地实测访客进入→演练→智能诊断，桌面与窄屏截图
- [ ] 5.4 安装 OpenSpec CLI 后运行 `openspec validate --all`（本机未安装，尚未执行）
