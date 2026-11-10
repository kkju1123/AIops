# Windows 安装指南

本指南使用 Windows 10/11、PowerShell 和 Docker Desktop。应用服务在本机运行，Docker 默认只运行 PostgreSQL + pgvector，Alertmanager 按需启动。

## 1. 安装基础工具

以管理员身份打开 PowerShell：

```powershell
winget install Git.Git
winget install Docker.DockerDesktop
winget install OpenJS.NodeJS.LTS
winget install astral-sh.uv
```

安装完成后启动 Docker Desktop，并新开一个命令提示符确认：

```text
git --version
node --version
npm --version
uv --version
docker --version
```

## 2. 配置 AWS 凭据

```text
aws configure sso
aws sts get-caller-identity --profile <你的只读 profile>
```

## 3. 获取并启动项目

```text
git clone <你的私有仓库地址> agent_py
cd agent_py
scripts\start-local.bat
```

首次启动会安装项目依赖、执行 SQLite 迁移并启动基础设施、后端和前端。CloudWatch MCP 由后端通过 `uv` 按需启动。

## 4. 配置

在启动前从安全模板创建被 Git 忽略的本地配置：

```powershell
Copy-Item config/project.template.json config/project.json
Copy-Item config/user.project.template.json config/user.project.json
```

在本地配置中填写 DeepSeek API Key 和可选 AWS profile，并核对 CloudWatch 区域与日志组。Embedding 与 Rerank 模型会在首次使用时下载到 Hugging Face 用户缓存。字段说明见[配置与运维教程](../operations-and-monitoring.md)。
