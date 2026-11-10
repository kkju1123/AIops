# 1. 规格与配置边界

- [x] 1.1 增加 CloudWatch observability 与项目默认 stdio MCP 配置规格
- [x] 1.2 更新配置模板和校验，确保模板不包含 AWS 凭据
- [x] 1.3 增加 stdio transport 单元测试

# 2. MCP 运行时

- [x] 2.1 为 MCP client 增加 stdio discovery、调用、超时和重试
- [x] 2.2 合并项目默认 CloudWatch 连接与用户启用的远程连接
- [x] 2.3 更新 readiness，返回 transport/provider 级安全状态

# 3. AIOps 与证据

- [x] 3.1 将 CLS 专用 Planner 改为 provider-neutral 工具选择
- [x] 3.2 为 `execute_cwl_insights_batch` 生成有界 CloudWatch 查询
- [x] 3.3 标准化日志证据摘要并保留失败语义
- [x] 3.4 更新后端与前端回归测试

# 4. 交互与文档

- [x] 4.1 更新 MCP 页面和诊断证据中的 AWS CloudWatch 术语
- [x] 4.2 更新本地启动脚本、README 和运维指南
- [ ] 4.3 同步 OpenSpec WIKI

# 5. 验证

- [x] 5.1 运行目标 pytest、Ruff 和 Pyright
- [x] 5.2 运行前端 typecheck、Vitest 和 build
- [ ] 5.3 运行 `openspec validate --all` 与文档构建
- [x] 5.4 执行真实 MCP discovery/query 和应用诊断端到端验证；见 smoke-results.md。使用现有 profile，仅执行只读查询，尚未验证最小权限角色。
