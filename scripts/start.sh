#!/usr/bin/env bash
# 本机启动脚本。用法：APP_ENV=dev|prod PORT=8000 scripts/start.sh
set -euo pipefail
cd "$(dirname "$0")/.."

export APP_ENV="${APP_ENV:-dev}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8000}"

args=(--host "$HOST" --port "$PORT" --timeout-graceful-shutdown 30)
if [ "$APP_ENV" = "dev" ]; then
  args+=(--reload)
fi

# exec 让 uvicorn 直接接收 SIGTERM，等待在途请求完成后退出
exec python -m uvicorn app.main:app "${args[@]}"
