from __future__ import annotations

from dataclasses import dataclass

from app.controllers.system_setting import system_setting_controller
from app.core.redis_client import execute_redis


@dataclass
class LoginSecurityDecision:
    locked: bool
    scope: str | None = None
    ttl_seconds: int = 0


class LoginSecurityController:
    @staticmethod
    def _normalize_username(username: str) -> str:
        return (username or "").strip().lower()

    @staticmethod
    def _normalize_ip(ip: str) -> str:
        return (ip or "unknown").strip().lower() or "unknown"

    @classmethod
    def _account_ip_fail_key(cls, username: str, ip: str) -> str:
        return f"login_fail:account_ip:{cls._normalize_username(username)}:{cls._normalize_ip(ip)}"

    @classmethod
    def _account_ip_lock_key(cls, username: str, ip: str) -> str:
        return f"login_lock:account_ip:{cls._normalize_username(username)}:{cls._normalize_ip(ip)}"

    @classmethod
    def _ip_fail_key(cls, ip: str) -> str:
        return f"login_fail:ip:{cls._normalize_ip(ip)}"

    @classmethod
    def _ip_lock_key(cls, ip: str) -> str:
        return f"login_lock:ip:{cls._normalize_ip(ip)}"

    async def get_config(self) -> dict:
        return await system_setting_controller.get_public_config()

    async def check_lock(self, *, username: str, ip: str) -> LoginSecurityDecision:
        config = await self.get_config()
        if not config.get("login_security_enabled", True):
            return LoginSecurityDecision(locked=False)

        account_lock_key = self._account_ip_lock_key(username, ip)
        ip_lock_key = self._ip_lock_key(ip)

        account_lock = await execute_redis("get", account_lock_key)
        if account_lock:
            ttl = await execute_redis("ttl", account_lock_key)
            return LoginSecurityDecision(locked=True, scope="account_ip", ttl_seconds=max(int(ttl or 0), 0))

        ip_lock = await execute_redis("get", ip_lock_key)
        if ip_lock:
            ttl = await execute_redis("ttl", ip_lock_key)
            return LoginSecurityDecision(locked=True, scope="ip", ttl_seconds=max(int(ttl or 0), 0))

        return LoginSecurityDecision(locked=False)

    async def record_failure(self, *, username: str, ip: str) -> LoginSecurityDecision:
        config = await self.get_config()
        if not config.get("login_security_enabled", True):
            return LoginSecurityDecision(locked=False)

        window_seconds = int(config.get("login_fail_window_minutes", 60)) * 60
        account_fail_limit = int(config.get("login_account_ip_fail_limit", 5))
        account_lock_seconds = int(config.get("login_account_ip_lock_minutes", 60)) * 60
        ip_fail_limit = int(config.get("login_ip_fail_limit", 20))
        ip_lock_seconds = int(config.get("login_ip_lock_minutes", 60)) * 60

        account_fail_key = self._account_ip_fail_key(username, ip)
        ip_fail_key = self._ip_fail_key(ip)
        account_lock_key = self._account_ip_lock_key(username, ip)
        ip_lock_key = self._ip_lock_key(ip)

        account_count = await execute_redis("incr", account_fail_key)
        if int(account_count) == 1:
            await execute_redis("expire", account_fail_key, window_seconds)

        ip_count = await execute_redis("incr", ip_fail_key)
        if int(ip_count) == 1:
            await execute_redis("expire", ip_fail_key, window_seconds)

        if int(account_count) >= account_fail_limit:
            await execute_redis("setex", account_lock_key, account_lock_seconds, 1)
            await execute_redis("delete", account_fail_key)
            return LoginSecurityDecision(locked=True, scope="account_ip", ttl_seconds=account_lock_seconds)

        if int(ip_count) >= ip_fail_limit:
            await execute_redis("setex", ip_lock_key, ip_lock_seconds, 1)
            await execute_redis("delete", ip_fail_key)
            return LoginSecurityDecision(locked=True, scope="ip", ttl_seconds=ip_lock_seconds)

        return LoginSecurityDecision(locked=False)

    async def clear_success(self, *, username: str, ip: str) -> None:
        await execute_redis("delete", self._account_ip_fail_key(username, ip))


login_security_controller = LoginSecurityController()
