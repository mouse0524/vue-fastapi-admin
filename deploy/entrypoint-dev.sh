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

echo "Ensuring MySQL development user and database..."
python - <<'PY'
import asyncio
import os

import asyncmy


def quote_identifier(value: str) -> str:
    return "`" + value.replace("`", "``") + "`"


async def main() -> None:
    host = os.getenv("MYSQL_HOST", "mysql")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    root_password = os.getenv("MYSQL_ROOT_PASSWORD", "")
    database = os.getenv("MYSQL_DATABASE", "iandsec-user-center")
    user = os.getenv("MYSQL_USER", "iandsec-user-center")
    password = os.getenv("MYSQL_PASSWORD", "")

    conn = await asyncmy.connect(host=host, port=port, user="root", password=root_password, autocommit=True)
    try:
        async with conn.cursor() as cursor:
            db_name = quote_identifier(database)
            await cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            await cursor.execute("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s", (user, password))
            await cursor.execute("ALTER USER %s@'%%' IDENTIFIED BY %s", (user, password))
            await cursor.execute(f"GRANT ALL PRIVILEGES ON {db_name}.* TO %s@'%%'", (user,))
            await cursor.execute("FLUSH PRIVILEGES")
    finally:
        conn.close()


asyncio.run(main())
PY

# 启动后端服务器
echo "Starting backend server on port 9999..."
python run.py
