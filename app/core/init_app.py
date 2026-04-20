import shutil
import glob
import os

from aerich import Command
from fastapi import FastAPI
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from tortoise.expressions import Q

from app.api import api_router
from app.controllers.api import api_controller
from app.controllers.user import UserCreate, user_controller
from app.core.exceptions import (
    DoesNotExist,
    DoesNotExistHandle,
    HTTPException,
    HttpExcHandle,
    IntegrityError,
    IntegrityHandle,
    RequestValidationError,
    RequestValidationHandle,
    ResponseValidationError,
    ResponseValidationHandle,
)
from app.log import logger
from app.models.admin import Api, Menu, Role
from app.schemas.menus import MenuType
from app.settings.config import settings

from .middlewares import BackGroundTaskMiddleware, HttpAuditLogMiddleware


def make_middlewares():
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=settings.CORS_ORIGINS,
            allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
            allow_methods=settings.CORS_ALLOW_METHODS,
            allow_headers=settings.CORS_ALLOW_HEADERS,
        ),
        Middleware(BackGroundTaskMiddleware),
        Middleware(
            HttpAuditLogMiddleware,
            methods=["GET", "POST", "PUT", "DELETE"],
            exclude_paths=[
                "/api/v1/base/access_token",
                "/docs",
                "/openapi.json",
            ],
        ),
    ]
    return middleware


def register_exceptions(app: FastAPI):
    app.add_exception_handler(DoesNotExist, DoesNotExistHandle)
    app.add_exception_handler(HTTPException, HttpExcHandle)
    app.add_exception_handler(IntegrityError, IntegrityHandle)
    app.add_exception_handler(RequestValidationError, RequestValidationHandle)
    app.add_exception_handler(ResponseValidationError, ResponseValidationHandle)


def register_routers(app: FastAPI, prefix: str = "/api"):
    app.include_router(api_router, prefix=prefix)


async def init_superuser():
    user = await user_controller.model.exists()
    if not user:
        await user_controller.create_user(
            UserCreate(
                username="admin",
                email="admin@admin.com",
                password="123456",
                is_active=True,
                is_superuser=True,
            )
        )


async def init_menus():
    menus = await Menu.exists()
    if not menus:
        parent_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="系统管理",
            path="/system",
            order=1,
            parent_id=0,
            icon="carbon:gui-management",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/system/user",
        )
        children_menu = [
            Menu(
                menu_type=MenuType.MENU,
                name="用户管理",
                path="user",
                order=1,
                parent_id=parent_menu.id,
                icon="material-symbols:person-outline-rounded",
                is_hidden=False,
                component="/system/user",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="角色管理",
                path="role",
                order=2,
                parent_id=parent_menu.id,
                icon="carbon:user-role",
                is_hidden=False,
                component="/system/role",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="菜单管理",
                path="menu",
                order=3,
                parent_id=parent_menu.id,
                icon="material-symbols:list-alt-outline",
                is_hidden=False,
                component="/system/menu",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="API管理",
                path="api",
                order=4,
                parent_id=parent_menu.id,
                icon="ant-design:api-outlined",
                is_hidden=False,
                component="/system/api",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="部门管理",
                path="dept",
                order=5,
                parent_id=parent_menu.id,
                icon="mingcute:department-line",
                is_hidden=False,
                component="/system/dept",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="审计日志",
                path="auditlog",
                order=6,
                parent_id=parent_menu.id,
                icon="ph:clipboard-text-bold",
                is_hidden=False,
                component="/system/auditlog",
                keepalive=False,
            ),
            Menu(
                menu_type=MenuType.MENU,
                name="系统设置",
                path="settings",
                order=7,
                parent_id=parent_menu.id,
                icon="material-symbols:settings-outline",
                is_hidden=False,
                component="/system/settings",
                keepalive=False,
            ),
        ]
        await Menu.bulk_create(children_menu)
        await Menu.create(
            menu_type=MenuType.MENU,
            name="一级菜单",
            path="/top-menu",
            order=2,
            parent_id=0,
            icon="material-symbols:featured-play-list-outline",
            is_hidden=False,
            component="/top-menu",
            keepalive=False,
            redirect="",
        )

    ticket_parent = await Menu.filter(path="/ticket").first()
    if not ticket_parent:
        ticket_parent = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="工单中心",
            path="/ticket",
            order=3,
            parent_id=0,
            icon="tabler:ticket",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/ticket/submit",
        )

    ticket_children = [
        {
            "name": "提交工单",
            "path": "submit",
            "order": 1,
            "icon": "material-symbols:upload-file-outline",
            "component": "/ticket/submit",
        },
        {
            "name": "我的工单",
            "path": "my",
            "order": 2,
            "icon": "mdi:ticket-account",
            "component": "/ticket/my",
        },
        {
            "name": "工单审核",
            "path": "review",
            "order": 3,
            "icon": "material-symbols:checklist",
            "component": "/ticket/review",
        },
        {
            "name": "技术处理",
            "path": "tech",
            "order": 4,
            "icon": "mdi:tools",
            "component": "/ticket/tech",
        },
    ]
    for child in ticket_children:
        exists = await Menu.filter(parent_id=ticket_parent.id, path=child["path"]).exists()
        if not exists:
            await Menu.create(
                menu_type=MenuType.MENU,
                parent_id=ticket_parent.id,
                is_hidden=False,
                keepalive=False,
                redirect="",
                **child,
            )

    partner_parent = await Menu.filter(path="/partner").first()
    if not partner_parent:
        partner_parent = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="代理商中心",
            path="/partner",
            order=4,
            parent_id=0,
            icon="mdi:account-group-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/partner/review",
        )

    if not await Menu.filter(parent_id=partner_parent.id, path="review").exists():
        await Menu.create(
            menu_type=MenuType.MENU,
            name="注册审核",
            path="review",
            order=1,
            parent_id=partner_parent.id,
            icon="mdi:file-document-edit-outline",
            is_hidden=False,
            component="/partner/review",
            keepalive=False,
            redirect="",
        )

    if not await Menu.filter(component="/system/settings").exists():
        system_parent = await Menu.filter(path="/system").first()
        if system_parent:
            await Menu.create(
                menu_type=MenuType.MENU,
                name="系统设置",
                path="settings",
                order=7,
                parent_id=system_parent.id,
                icon="material-symbols:settings-outline",
                is_hidden=False,
                component="/system/settings",
                keepalive=False,
                redirect="",
            )

    outbound_parent = await Menu.filter(path="/outbound").first()
    if not outbound_parent:
        outbound_parent = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="外发管理",
            path="/outbound",
            order=5,
            parent_id=0,
            icon="material-symbols:outbox-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/outbound/webdav",
        )
    else:
        outbound_parent.menu_type = MenuType.CATALOG
        outbound_parent.name = "外发管理"
        outbound_parent.order = 5
        outbound_parent.parent_id = 0
        outbound_parent.icon = "material-symbols:outbox-outline"
        outbound_parent.is_hidden = False
        outbound_parent.component = "Layout"
        outbound_parent.keepalive = False
        outbound_parent.redirect = "/outbound/webdav"
        await outbound_parent.save()

    webdav_menu = await Menu.filter(
        Q(component="/system/webdav") | Q(path="webdav", parent_id=outbound_parent.id) | Q(name="外发网盘")
    ).first()
    if webdav_menu:
        webdav_menu.name = "外发网盘"
        webdav_menu.path = "webdav"
        webdav_menu.order = 1
        webdav_menu.parent_id = outbound_parent.id
        webdav_menu.icon = "material-symbols:cloud-sync-outline"
        webdav_menu.is_hidden = False
        webdav_menu.keepalive = False
        webdav_menu.redirect = ""
        await webdav_menu.save()
    else:
        await Menu.create(
            menu_type=MenuType.MENU,
            name="外发网盘",
            path="webdav",
            order=1,
            parent_id=outbound_parent.id,
            icon="material-symbols:cloud-sync-outline",
            is_hidden=False,
            component="/system/webdav",
            keepalive=False,
            redirect="",
        )

    share_menu = await Menu.filter(
        Q(component="/system/webdav-share") | Q(path="webdav-share", parent_id=outbound_parent.id) | Q(name="分享记录")
    ).first()
    if share_menu:
        share_menu.name = "分享记录"
        share_menu.path = "webdav-share"
        share_menu.order = 2
        share_menu.parent_id = outbound_parent.id
        share_menu.icon = "material-symbols:link-rounded"
        share_menu.is_hidden = False
        share_menu.keepalive = False
        share_menu.redirect = ""
        await share_menu.save()
    else:
        await Menu.create(
            menu_type=MenuType.MENU,
            name="分享记录",
            path="webdav-share",
            order=2,
            parent_id=outbound_parent.id,
            icon="material-symbols:link-rounded",
            is_hidden=False,
            component="/system/webdav-share",
            keepalive=False,
            redirect="",
        )

    kb_parent = await Menu.filter(path="/kb").first()
    if not kb_parent:
        kb_parent = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="AI知识库",
            path="/kb",
            order=6,
            parent_id=0,
            icon="material-symbols:auto-awesome-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/kb/chat",
        )
    else:
        kb_parent.menu_type = MenuType.CATALOG
        kb_parent.name = "AI知识库"
        kb_parent.order = 6
        kb_parent.parent_id = 0
        kb_parent.icon = "material-symbols:auto-awesome-outline"
        kb_parent.is_hidden = False
        kb_parent.component = "Layout"
        kb_parent.keepalive = False
        kb_parent.redirect = "/kb/chat"
        await kb_parent.save()

    kb_children = [
        {
            "name": "知识空间",
            "path": "space",
            "order": 1,
            "icon": "material-symbols:hub-outline",
            "component": "/kb/space",
        },
        {
            "name": "文档中心",
            "path": "document",
            "order": 2,
            "icon": "material-symbols:docs-outline",
            "component": "/kb/document",
        },
        {
            "name": "智能问答",
            "path": "chat",
            "order": 3,
            "icon": "material-symbols:chat-outline",
            "component": "/kb/chat",
        },
        {
            "name": "反馈标注",
            "path": "feedback",
            "order": 5,
            "icon": "material-symbols:feedback-outline",
            "component": "/kb/feedback",
        },
        {
            "name": "会话记录",
            "path": "session",
            "order": 4,
            "icon": "material-symbols:history",
            "component": "/kb/session",
        },
        {
            "name": "模型日志",
            "path": "llm-log",
            "order": 6,
            "icon": "material-symbols:monitoring-outline",
            "component": "/kb/llm-log",
        },
    ]
    for child in kb_children:
        child_menu = await Menu.filter(
            Q(parent_id=kb_parent.id, path=child["path"]) | Q(component=child["component"])
        ).first()
        if child_menu:
            child_menu.name = child["name"]
            child_menu.path = child["path"]
            child_menu.order = child["order"]
            child_menu.parent_id = kb_parent.id
            child_menu.icon = child["icon"]
            child_menu.is_hidden = False
            child_menu.component = child["component"]
            child_menu.keepalive = False
            child_menu.redirect = ""
            await child_menu.save()
        else:
            await Menu.create(
                menu_type=MenuType.MENU,
                name=child["name"],
                path=child["path"],
                order=child["order"],
                parent_id=kb_parent.id,
                icon=child["icon"],
                is_hidden=False,
                component=child["component"],
                keepalive=False,
                redirect="",
            )


async def init_apis():
    await api_controller.refresh_api()


async def init_db():
    command = Command(tortoise_config=settings.TORTOISE_ORM)
    try:
        await command.init_db(safe=True)
    except FileExistsError:
        pass

    await command.init()

    migration_files = glob.glob(os.path.join("migrations", "models", "3_*.py"))
    if len(migration_files) > 1:
        migration_files.sort(key=os.path.getmtime, reverse=True)
        keep = migration_files[0]
        for file in migration_files[1:]:
            try:
                os.remove(file)
                logger.warning(f"removed duplicated migration file: {file}, keep: {keep}")
            except OSError:
                pass

    try:
        await command.upgrade(run_in_transaction=True)
    except AttributeError:
        logger.warning("unable to retrieve model history from database, model history will be created from scratch")
        shutil.rmtree("migrations")
        await command.init_db(safe=True)


async def init_roles():
    old_partner_role = await Role.filter(name="代理商").first()
    if old_partner_role:
        old_partner_role.name = "渠道商"
        old_partner_role.desc = "渠道商角色"
        await old_partner_role.save()

    role_desc_map = {
        "管理员": "管理员角色",
        "渠道商": "渠道商角色",
        "用户": "用户角色",
        "技术": "技术角色",
        "客服": "客服角色",
    }

    role_map: dict[str, Role] = {}
    for role_name, role_desc in role_desc_map.items():
        role_obj, _ = await Role.get_or_create(name=role_name, defaults={"desc": role_desc})
        role_map[role_name] = role_obj

    all_apis = await Api.all()
    all_menus = await Menu.all()

    admin_role = role_map["管理员"]
    await admin_role.apis.add(*all_apis)
    await admin_role.menus.add(*all_menus)

    ticket_submit_apis = await Api.filter(
        path__in=[
            "/api/v1/ticket/upload",
            "/api/v1/ticket/create",
            "/api/v1/ticket/list",
            "/api/v1/ticket/get",
            "/api/v1/ticket/resubmit",
            "/api/v1/ticket/actions",
        ]
    )
    ticket_tech_apis = await Api.filter(path__in=["/api/v1/ticket/tech/action"])
    ticket_review_apis = await Api.filter(path__in=["/api/v1/ticket/review"])
    partner_review_apis = await Api.filter(
        path__in=["/api/v1/partner/register/list", "/api/v1/partner/register/review"]
    )
    settings_apis = await Api.filter(path__in=["/api/v1/settings/get", "/api/v1/settings/update"])
    webdav_apis = await Api.filter(
        path__in=[
            "/api/v1/webdav/list",
            "/api/v1/webdav/share/create",
            "/api/v1/webdav/share/list",
            "/api/v1/webdav/share/delete",
        ]
    )
    kb_apis = await Api.filter(
        path__in=[
            "/api/v1/kb/space/list",
            "/api/v1/kb/space/create",
            "/api/v1/kb/space/update",
            "/api/v1/kb/document/list",
            "/api/v1/kb/document/create",
            "/api/v1/kb/document/upload",
            "/api/v1/kb/document/reparse",
            "/api/v1/kb/document/delete",
            "/api/v1/kb/session/list",
            "/api/v1/kb/session/create",
            "/api/v1/kb/session/messages",
            "/api/v1/kb/chat/ask",
            "/api/v1/kb/feedback/create",
            "/api/v1/kb/feedback/list",
            "/api/v1/kb/llm/log/list",
            "/api/v1/kb/llm/test",
        ]
    )
    basic_apis = await Api.filter(
        Q(method__in=["GET"]) | Q(tags="基础模块") | Q(path__in=["/api/v1/base/update_password"])
    )

    submit_menus = await Menu.filter(Q(path="/ticket") | Q(component="/ticket/submit") | Q(component="/ticket/my"))
    tech_menus = await Menu.filter(Q(path="/ticket") | Q(component="/ticket/tech") | Q(component="/ticket/my"))
    review_menus = await Menu.filter(Q(path="/ticket") | Q(component="/ticket/review"))
    partner_review_menus = await Menu.filter(Q(path="/partner") | Q(component="/partner/review"))
    settings_menus = await Menu.filter(Q(component="/system/settings"))
    webdav_menus = await Menu.filter(
        Q(path="/outbound") | Q(component="/system/webdav") | Q(component="/system/webdav-share")
    )
    kb_menus = await Menu.filter(
        Q(path="/kb") | Q(component__startswith="/kb/")
    )

    for role_name in ["用户", "渠道商", "技术", "客服"]:
        role_obj = role_map[role_name]
        await role_obj.apis.add(*basic_apis)

    await role_map["用户"].apis.add(*ticket_submit_apis)
    await role_map["用户"].menus.add(*submit_menus)

    await role_map["渠道商"].apis.add(*ticket_submit_apis)
    await role_map["渠道商"].menus.add(*submit_menus)

    await role_map["技术"].apis.add(*ticket_submit_apis)
    await role_map["技术"].apis.add(*ticket_tech_apis)
    await role_map["技术"].menus.add(*tech_menus)

    await role_map["客服"].apis.add(*ticket_review_apis)
    await role_map["客服"].apis.add(*partner_review_apis)
    await role_map["客服"].apis.add(
        *await Api.filter(path__in=["/api/v1/ticket/list", "/api/v1/ticket/get", "/api/v1/ticket/actions"])
    )
    await role_map["客服"].menus.add(*review_menus)
    await role_map["客服"].menus.add(*partner_review_menus)

    await role_map["管理员"].apis.add(*settings_apis)
    await role_map["管理员"].apis.add(*webdav_apis)
    await role_map["管理员"].apis.add(*kb_apis)
    await role_map["管理员"].menus.add(*settings_menus)
    await role_map["管理员"].menus.add(*webdav_menus)
    await role_map["管理员"].menus.add(*kb_menus)


async def init_data():
    await init_db()
    await init_superuser()
    await init_menus()
    await init_apis()
    await init_roles()
