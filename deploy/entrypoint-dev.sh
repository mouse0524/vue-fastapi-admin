#!/bin/sh
set -e

# 进入前端目录安装依赖和启动开发服务器
cd /opt/vue-fastapi-admin/web
pnpm install

# 启动前端开发服务器（后台运行，监听 0.0.0.0 以便容器外访问）
echo "Starting frontend development server on port 3100..."
pnpm run dev --host 0.0.0.0 &

# 返回项目根目录
cd /opt/vue-fastapi-admin

# 启动后端服务器
echo "Starting backend server on port 9999..."
python run.py
