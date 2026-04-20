from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.settings import settings


_redis_client: Redis | None = None


def _create_redis_client() -> Redis:
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        password=settings.REDIS_PASSWORD,
        decode_responses=True,
        socket_keepalive=True,
        health_check_interval=30,
        socket_connect_timeout=3,
        socket_timeout=3,
        retry_on_timeout=True,
    )


def get_redis() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = _create_redis_client()
    return _redis_client


async def reset_redis() -> None:
    global _redis_client
    old_client = _redis_client
    _redis_client = None
    if old_client is None:
        return
    try:
        if hasattr(old_client, "aclose"):
            await old_client.aclose()
        else:
            await old_client.close()
    except Exception:
        pass


async def execute_redis(command: str, *args, **kwargs):
    for idx in range(2):
        client = get_redis()
        try:
            fn = getattr(client, command)
            return await fn(*args, **kwargs)
        except (RedisConnectionError, RedisTimeoutError, OSError):
            await reset_redis()
            if idx == 1:
                raise
