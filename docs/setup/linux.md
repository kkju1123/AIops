# Linux 安装指南

本指南以 Debian/Ubuntu 为例。应用服务在本机运行，Docker 默认只运行 PostgreSQL + pgvector，Alertmanager 按需启动。

## 1. 安装基础工具

```bash
sudo apt update
sudo apt install -y git curl ca-certificates docker.io docker-compose-plugin nodejs npm
curl -LsSf https://astral.sh/uv/install.sh | sh
```

重新打开终端后，确认工具可用：

```bash
git --version
node --version
npm --version
uv --version
docker --version
```

如需免 sudo 使用 Docker，请按 Docker Engine 官方文檔把当前用户加入 `docker` 组后重新登錄。

## 2. 配置 AWS 凭据

```bash
aws configure sso
aws sts get-caller-identity --profile <你的只读 profile>
```

## 3. 获取并启动项目

```bash
git clone <你的私有仓库地址> agent_py
cd agent_py
./scripts/start-local.sh
```

首次启动会安装项目依赖、执行 SQLite 迁移并启动基础设施、后端和前端。CloudWatch MCP 由后端通过 `uvx` 按需启动。

## 4. 配置

在启动前从安全模板创建被 Git 忽略的本地配置：

```bash
cp config/project.template.json config/project.json
cp config/user.project.template.json config/user.project.json
```

在本地配置中填写 DeepSeek API Key 和可选 AWS profile，并核对 CloudWatch 区域与日志组。Embedding 与 Rerank 模型会在首次使用时下载到 Hugging Face 用户缓存。字段说明见[配置与运维教程](../operations-and-monitoring.md)。
