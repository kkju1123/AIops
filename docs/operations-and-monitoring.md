# 配置与运维

应用只读取本地 `config/project.json` 和可选的 `config/user.project.json`，不读取本机环境变量。两个文件都被 Git 忽略；仓库只保留不含真实凭据的模板。不要为本项目创建 `.env` 文件，也不要提交本地配置。

首次使用时，在仓库根目录执行：

```bash
cp config/project.template.json config/project.json
cp config/user.project.template.json config/user.project.json
```

## 项目交付后的个人配置

在本地 `config/user.project.json` 中填写使用者自己的模型密钥和可选 AWS profile。CloudWatch 区域与日志组等共享参数在 `config/project.json` 中调整：

| 配置字段 | 替换为 |
| --- | --- |
| `llm.apiKey` | 使用者自己的模型服务密钥 |
| `observability.awsCloudWatch.profile` | 本机可选 AWS CLI/SSO profile；部署使用工作负载角色时留空 |
| `observability.awsCloudWatch.region` | CloudWatch 区域，例如 `eu-west-1` |
| `observability.awsCloudWatch.logGroupNames` | 允许诊断查询的日志组，例如 `/super-ai/demo` |
| `observability.awsCloudWatch.timeoutSeconds` | 官方 MCP 单次 discovery/call 超时 |

模板中的 profile 保持为空，仓库中不得出现 AWS access key、secret key 或 session token。本地优先使用 AWS SSO/profile，部署优先使用工作负载角色；已暴露的密钥应立即轮换。

## 真实日志与本地告警样例

AWS 演示资源使用 `/super-ai/demo`、`SuperAI/Demo` 指标命名空间和定时 Lambda fixture。应用使用官方 CloudWatch MCP 的只读工具查询它们；fixture 写权限与应用读权限应使用不同 IAM role。

## 公开实时故障演练

故障演练位于工作台的 `/drill`（旧地址 `/live` 重定向至此），面向简历面试官等访客：未登录访问时前端自动调用 `POST /auth/guest` 创建临时访客账号，随后即可触发一次告警与完整诊断。演练相关配置位于 `config/project.json` 的 `liveDemo` 段：

| 配置字段 | 说明 |
|----------|------|
| `liveDemo.enabled` | 是否开放演练；模板默认 `false` |
| `liveDemo.serviceAccountEmail` | 执行演练诊断的已注册账号，需预先索引 SOP |
| `liveDemo.observability` | `simulator`（默认）：日志与指标来自故障模拟器 MCP Server，并标注“故障模拟器生成”；`aws-cloudwatch`：查询 CloudWatch |
| `liveDemo.scenarioIds` | 开放的场景白名单；模板默认开放全部 11 个场景 |
| `liveDemo.perVisitorHourlyLimit` | 同一访客（IP 哈希）每小时可触发次数 |
| `liveDemo.dailyLimit` | 全站最近 24 小时可触发次数 |
| `liveDemo.maxConcurrentRuns` | 同时运行的演练上限 |
| `liveDemo.runTimeoutSeconds` | 超过该时长的运行不再计入并发 |
| `liveDemo.trustForwardedFor` | 仅在可信反向代理之后设为 `true`，以读取 `X-Forwarded-For` |

事件流只接受单次运行的 `X-Live-Demo-Token`，服务端仅保存其 SHA-256 哈希。创建运行时若携带 Bearer token，后端记录发起人（`live_demo_runs.requester_user_id`）；诊断任务仍归服务账号所有，但发起人可以通过 `/aiops/diagnostics` 系列接口只读查看，任务带 `origin=live-drill` 与 `simulated` 标识。匿名运行不会出现在任何人的诊断历史中。超限返回 `BUSINESS_RATE_LIMITED`（HTTP 429）；演练任务不会沉淀为故障案例或知识。已登录用户可通过 `GET /live-demo/sop-documents` 只读浏览服务账号的 SOP。

### 访客模式

访客模式由 `guestAccess` 段控制：

| 配置字段 | 说明 |
|----------|------|
| `guestAccess.enabled` | 是否允许 `POST /auth/guest`；模板默认 `false` |
| `guestAccess.sessionTtlHours` | 访客会话有效期（小时，至少 1），过期后返回 `AUTH_SESSION_REVOKED` |
| `guestAccess.hourlyCreationLimit` | 全站每小时最多创建的访客数，超出返回 `BUSINESS_RATE_LIMITED` |
| `guestAccess.chatMessagesPerHour` | 每位访客每小时可发送的对话消息数 |

访客账号使用无法获知的随机密码（Argon2 哈希），不能通过 `/auth/login` 登录。访客调用创建工作台诊断、读取真实活跃告警、保存诊断为知识、上传/删除/重新索引文档、管理或检查 MCP 连接时返回 `AUTH_FORBIDDEN`。访客账号目前不会自动清理，由 `hourlyCreationLimit` 控制规模。服务账号 SOP 通过 `--profile live-drill` 与 `--profile java-ecommerce` 两次运行 `uv run python scripts/seed_ecommerce_aiops_sop.py` 索引。

模拟模式下，后端为每次运行以 stdio 启动 `python -m super_ai.simulator.server`，并通过子进程环境变量 `SUPER_AI_SIMULATED_FAULT` 传入本次注入的故障（这是进程间参数，不是项目配置）。只有同时带有 `liveDemo=true` 的演练任务才会使用模拟器，认证工作台的诊断始终走 CloudWatch。后端启动且演练开启时会在后台预热检索模型，日志事件为 `live_demo.models.warmed` 或 `live_demo.models.warmup_failed`。

