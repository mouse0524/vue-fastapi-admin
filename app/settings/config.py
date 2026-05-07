import os
import typing

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    VERSION: str = "0.1.0"
    APP_TITLE: str = "安得和众用户服务中心"
    PROJECT_NAME: str = "iandsec-uc"
    APP_DESCRIPTION: str = "Description"

    CORS_ORIGINS: typing.List = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: typing.List = ["*"]
    CORS_ALLOW_HEADERS: typing.List = ["*"]
    TRUST_PROXY_HEADERS: bool = False

    DEBUG: bool = True

    PROJECT_ROOT: str = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    BASE_DIR: str = os.path.abspath(os.path.join(PROJECT_ROOT, os.pardir))
    LOGS_ROOT: str = os.path.join(BASE_DIR, "app/logs")
    SECRET_KEY: str = "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf"  # openssl rand -hex 32
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 day
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    MYSQL_PORT: int = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "123456")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "iandsec-user-center")
    REDIS_HOST: str = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = 0
    REDIS_PASSWORD: str | None = os.getenv("REDIS_PASSWORD", "")
    CAPTCHA_TTL_SECONDS: int = 120
    CAPTCHA_MAX_RETRY: int = 3
    EMAIL_VERIFY_TTL_SECONDS: int = 600
    UPLOAD_DIR: str = os.path.join(BASE_DIR, "storage")
    MAX_UPLOAD_SIZE: int = 20 * 1024 * 1024
    ALLOWED_EXTENSIONS: typing.List[str] = [
        ".jpg",
        ".jpeg",
        ".png",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".txt",
        ".zip",
        ".rar",
    ]
    TORTOISE_ORM: dict = {
        "connections": {
            # SQLite configuration
            # "sqlite": {
            #     "engine": "tortoise.backends.sqlite",
            #     "credentials": {"file_path": f"{BASE_DIR}/db.sqlite3"},  # Path to SQLite database file
            # },
            # MySQL/MariaDB configuration
            # Install with: tortoise-orm[asyncmy]
            "mysql": {
                "engine": "tortoise.backends.mysql",
                "credentials": {
                    "host": MYSQL_HOST,  # Database host address
                    "port": MYSQL_PORT,  # Database port
                    "user": MYSQL_USER,  # Database username
                    "password": MYSQL_PASSWORD,  # Database password
                    "database": MYSQL_DATABASE,  # Database name
                },
            },
            # PostgreSQL configuration
            # Install with: tortoise-orm[asyncpg]
            # "postgres": {
            #     "engine": "tortoise.backends.asyncpg",
            #     "credentials": {
            #         "host": "localhost",  # Database host address
            #         "port": 5432,  # Database port
            #         "user": "yourusername",  # Database username
            #         "password": "yourpassword",  # Database password
            #         "database": "yourdatabase",  # Database name
            #     },
            # },
            # MSSQL/Oracle configuration
            # Install with: tortoise-orm[asyncodbc]
            # "oracle": {
            #     "engine": "tortoise.backends.asyncodbc",
            #     "credentials": {
            #         "host": "localhost",  # Database host address
            #         "port": 1433,  # Database port
            #         "user": "yourusername",  # Database username
            #         "password": "yourpassword",  # Database password
            #         "database": "yourdatabase",  # Database name
            #     },
            # },
            # SQLServer configuration
            # Install with: tortoise-orm[asyncodbc]
            # "sqlserver": {
            #     "engine": "tortoise.backends.asyncodbc",
            #     "credentials": {
            #         "host": "localhost",  # Database host address
            #         "port": 1433,  # Database port
            #         "user": "yourusername",  # Database username
            #         "password": "yourpassword",  # Database password
            #         "database": "yourdatabase",  # Database name
            #     },
            # },
        },
        "apps": {
            "models": {
                "models": ["app.models", "aerich.models"],
                "default_connection": "mysql",
            },
        },
        "use_tz": False,  # Whether to use timezone-aware datetimes
        "timezone": "Asia/Shanghai",  # Timezone setting
    }
    DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"
    KB_DEFAULT_TOP_K: int = 5
    KB_DEFAULT_MODEL: str = "mock-rag-v1"

settings = Settings()
