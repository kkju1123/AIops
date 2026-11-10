# macOS 安装指南

本指南用于在 macOS 上完整安装并启动 Agent Py。应用服务在本机运行，Docker 默认只运行 PostgreSQL + pgvector，Alertmanager 按需启动。

## 1. 安装基础工具

安装 Homebrew 后执行：

```bash
brew install git node uv
brew install --cask docker
```

启动 Docker Desktop，并确认命令可用：

```bash
git --version
node --version
npm --version
uv --version
docker --version
```

## 2. 配置 AWS 凭据

```bash
aws configure sso
aws sts get-caller-identity --profile <你的只读 profile>
```

项目已固定官方 CloudWatch MCP `awslabs.cloudwatch-mcp-server` 版本，后端会通过已安装的 `uvx` 按需启动，无需全局安装 MCP 包。

## 3. 获取并启动项目

```bash
git clone <你的私有仓库地址> agent_py
cd agent_py
./scripts/start-local.sh
```

首次启动会安装项目依赖、执行 SQLite 迁移并启动基础设施、后端和前端。打开 `http://127.0.0.1:5173` 开始使用。

## 4. 配置

从安全模板创建被 Git 忽略的本地配置：

```bash
cp config/project.template.json config/project.json
cp config/user.project.template.json config/user.project.json
```

在本地配置中填写 DeepSeek API Key 和可选 AWS profile，并核对 `eu-west-1` 与 `/super-ai/demo`。Embedding 与 Rerank 模型会在首次使用时下载到 Hugging Face 用户缓存。字段说明见[配置与运维教程](../operations-and-monitoring.md)。
