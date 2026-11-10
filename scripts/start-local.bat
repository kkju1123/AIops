@echo off
setlocal EnableExtensions

set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

where docker >nul 2>nul || (echo 缺少必需命令：docker & exit /b 1)
where npm >nul 2>nul || (echo 缺少必需命令：npm & exit /b 1)
where uv >nul 2>nul || (echo 缺少必需命令：uv & exit /b 1)

docker compose -f infra/compose.yaml up -d --wait postgres

pushd apps\backend
if not exist var mkdir var
uv sync
if errorlevel 1 exit /b 1
uv run alembic upgrade head
if errorlevel 1 exit /b 1
start "Agent Py Backend" /D "%CD%" cmd /c "uv run uvicorn super_ai.api.app:create_app --factory --host 127.0.0.1 --port 8000 > var\backend-local.log 2>&1"
popd

pushd apps\frontend
if not exist node_modules npm install
if errorlevel 1 exit /b 1
start "Agent Py Frontend" /D "%CD%" cmd /c "npm run dev -- --host 127.0.0.1 > ..\backend\var\frontend-local.log 2>&1"
popd

echo 前端：     http://127.0.0.1:5173
echo 后端：     http://127.0.0.1:8000
echo MCP：      AWS CloudWatch（后端按需启动 stdio Server）
echo 本地日志： apps\backend\var
