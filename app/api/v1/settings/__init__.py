from fastapi import APIRouter

from .settings import router

settings_router = APIRouter()
settings_router.include_router(router, tags=["系统设置模块"])

__all__ = ["settings_router"]
