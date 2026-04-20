from fastapi import APIRouter

from app.core.dependency import DependPermission

from .apis import apis_router
from .auditlog import auditlog_router
from .base import base_router
from .depts import depts_router
from .menus import menus_router
from .partner import partner_router
from .public_ticket import public_ticket_router
from .roles import roles_router
from .settings import settings_router
from .tickets import tickets_router
from .users import users_router

v1_router = APIRouter()

v1_router.include_router(base_router, prefix="/base")
v1_router.include_router(partner_router, prefix="/partner")
v1_router.include_router(public_ticket_router, prefix="/public/ticket")
v1_router.include_router(users_router, prefix="/user", dependencies=[DependPermission])
v1_router.include_router(roles_router, prefix="/role", dependencies=[DependPermission])
v1_router.include_router(menus_router, prefix="/menu", dependencies=[DependPermission])
v1_router.include_router(apis_router, prefix="/api", dependencies=[DependPermission])
v1_router.include_router(depts_router, prefix="/dept", dependencies=[DependPermission])
v1_router.include_router(auditlog_router, prefix="/auditlog", dependencies=[DependPermission])
v1_router.include_router(tickets_router, prefix="/ticket", dependencies=[DependPermission])
v1_router.include_router(settings_router, prefix="/settings", dependencies=[DependPermission])
