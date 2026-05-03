from fastapi import APIRouter

from .ai_kb import router

ai_kb_router = APIRouter()
ai_kb_router.include_router(router, tags=["AI知识库模块"])

__all__ = ["ai_kb_router"]
