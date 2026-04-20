from fastapi import APIRouter

from .public_ticket import router

public_ticket_router = APIRouter()
public_ticket_router.include_router(router, tags=["公开工单模块"])

__all__ = ["public_ticket_router"]
