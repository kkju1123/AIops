# Docker Compose 基础设施

`infra/compose.yaml` 默认只管理本机开发所需的 **PostgreSQL + pgvector**。Alertmanager 位于可选 `observability` profile。后端、前端和腾讯云 CLS MCP Server 由根目录启动脚本直接在本机运行。

## 启动基础设施

```bash
docker compose -f infra/compose.yaml up -d --wait postgres
```

PostgreSQL 地址为 `127.0.0.1:5432`，本地开发数据库、用户和密码均为 `oncall`。

需要告警演示时启动 Alertmanager：

```bash
docker compose -f infra/compose.yaml --profile observability up -d alertmanager
```

Alertmanager 地址为 `http://127.0.0.1:9093`。

停止基础设施：

```bash
docker compose -f infra/compose.yaml down
```

仅在明确需要清除本地状态时才执行 `docker compose -f infra/compose.yaml down -v`；该命令会删除 PostgreSQL 和 Alertmanager 的本地卷。

文档上传与知识索引不会在启动时自动执行。已有 Milvus 本地向量不会自动迁移，需要通过现有“重建索引”操作写入 pgvector。
