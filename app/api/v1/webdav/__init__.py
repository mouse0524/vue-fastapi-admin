from fastapi import APIRouter

from .webdav import public_router, router

webdav_router = APIRouter()
webdav_router.include_router(router, tags=["外发网盘模块"])

webdav_public_router = APIRouter()
webdav_public_router.include_router(public_router, tags=["外发网盘公开模块"])

__all__ = ["webdav_router", "webdav_public_router"]
