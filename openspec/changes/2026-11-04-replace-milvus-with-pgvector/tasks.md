## 1. 规格与存储适配器

- [x] 1.1 增加 pgvector 配置、显式连接生命周期和表初始化
- [x] 1.2 实现 tenant 范围的写入、向量搜索、chunk 列举和文档删除
- [x] 1.3 增加配置、权限过滤、维度验证和健康检查测试

## 2. 应用与本地运行时

- [x] 2.1 将应用 wiring、readiness 和配置检查切换为 pgvector
- [x] 2.2 用 PostgreSQL + pgvector 替换 Milvus Compose 服务
- [x] 2.3 将 Alertmanager 改为可选 profile，并更新 macOS/Linux 与 Windows 启动器
- [x] 2.4 更新配置模板和本地忽略配置

## 3. 文档与验证

- [x] 3.1 更新 README、infra 文档、安装指南和主规格
- [x] 3.2 运行目标 pytest、Ruff、Pyright、Compose config 和 OpenSpec 校验
- [x] 3.3 实际启动 PostgreSQL 并验证 pgvector extension、表和 readiness
