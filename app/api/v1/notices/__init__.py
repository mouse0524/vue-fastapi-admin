from fastapi import APIRouter

from .notices import router

notices_router = APIRouter()
notices_router.include_router(router, tags=["全局通知"])

__all__ = ["notices_router"]
