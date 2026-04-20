from fastapi import APIRouter

from .partner import router

partner_router = APIRouter()
partner_router.include_router(router, tags=["注册审核模块"])

__all__ = ["partner_router"]
