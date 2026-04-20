from fastapi import APIRouter

from .kb import router

kb_router = APIRouter()
kb_router.include_router(router, tags=["AI知识库模块"])

__all__ = ["kb_router"]
