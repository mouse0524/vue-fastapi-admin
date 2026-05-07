#!/bin/sh
set -e

cleanup() {
  if [ -n "$FRONTEND_PID" ]; then
    kill "$FRONTEND_PID" 2>/dev/null || true
  fi
}

trap cleanup INT TERM EXIT

# 进入前端目录安装依赖和启动开发服务器
cd /opt/iandsec-uc/web
CI=true pnpm install --prefer-offline

# 启动前端开发服务器（后台运行，监听 0.0.0.0 以便容器外访问）
echo "Starting frontend development server on port 3100..."
pnpm run dev --host 0.0.0.0 --no-open &
FRONTEND_PID=$!

# 返回项目根目录
cd /opt/iandsec-uc

# 启动后端服务器
echo "Starting backend server on port 9999..."
python run.py
