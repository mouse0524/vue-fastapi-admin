from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from fastapi.responses import FileResponse

from app.log import logger
from app.controllers.user import user_controller
from app.controllers.captcha import captcha_controller
from app.controllers.mail import mail_controller
from app.controllers.system_setting import system_setting_controller
from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth
from app.models.admin import Api, AuditLog, Menu, PartnerRegistration, Role, Ticket, User
from app.models.enums import PartnerRegisterStatus, TicketStatus
from app.schemas.captcha import CaptchaOut
from app.schemas.mail import SendVerifyCodeIn
from app.schemas.base import Fail, Success
from app.schemas.login import *
from app.schemas.users import UpdatePassword
from app.settings import settings
from app.utils.jwt_utils import create_access_token
from app.utils.password import get_password_hash, verify_password

router = APIRouter()


@router.post("/access_token", summary="获取token")
async def login_access_token(credentials: CredentialsSchema):
    logger.info("[api.login] start username={}", credentials.username)
    valid = await captcha_controller.verify_captcha(credentials.captcha_id, credentials.captcha_code)
    if not valid:
        logger.warning("[api.login] captcha_invalid username={} captcha_id={}", credentials.username, credentials.captcha_id)
        return Fail(code=400, msg=f"登录验证码错误或已过期（最多{settings.CAPTCHA_MAX_RETRY}次）")

    user: User = await user_controller.authenticate(credentials)
    await user_controller.update_last_login(user.id)
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.now(timezone.utc) + access_token_expires

    data = JWTOut(
        access_token=create_access_token(
            data=JWTPayload(
                user_id=user.id,
                username=user.username,
                is_superuser=user.is_superuser,
                exp=expire,
            )
        ),
        username=user.username,
    )
    logger.info("[api.login] success username={} user_id={}", user.username, user.id)
    return Success(data=data.model_dump())


@router.get("/captcha", summary="获取图形验证码")
async def get_captcha():
    captcha_id, image_base64 = await captcha_controller.create_captcha()
    data = CaptchaOut(captcha_id=captcha_id, image_base64=image_base64)
    return Success(data=data.model_dump())


@router.get("/public_config", summary="获取公共站点配置")
async def get_public_config():
    data = await system_setting_controller.get_public_config()
    return Success(data=data)


@router.get("/site_logo", summary="获取站点Logo")
async def get_site_logo():
    abs_path = await system_setting_controller.get_logo_abs_path()
    return FileResponse(abs_path)


@router.post("/send_email_code", summary="发送邮箱验证码")
async def send_email_code(payload: SendVerifyCodeIn):
    config = await system_setting_controller.get_public_config()
    if not config.get("allow_partner_register", True):
        return Fail(code=403, msg="当前暂未开放注册，如需开通请联系平台管理员")

    email = payload.email.strip().lower()
    logger.info("[api.send_email_code] start email={}", email)
    if await User.filter(email=email).exists():
        logger.warning("[api.send_email_code] email_exists email={}", email)
        return Fail(code=400, msg="该邮箱已完成注册，可直接登录")

    if await PartnerRegistration.filter(status=PartnerRegisterStatus.PENDING, email=email).exists():
        return Fail(code=400, msg="该邮箱已有待审核申请，请耐心等待审核结果")

    valid = await captcha_controller.verify_captcha(payload.captcha_id, payload.captcha_code)
    if not valid:
        logger.warning("[api.send_email_code] captcha_invalid email={} captcha_id={}", email, payload.captcha_id)
        return Fail(code=400, msg=f"图形验证码错误或已失效，请重试（最多{settings.CAPTCHA_MAX_RETRY}次）")

    await mail_controller.send_partner_verify_code(email)
    logger.info("[api.send_email_code] success email={}", email)
    return Success(msg="验证码已发送，请查收邮箱")


@router.get("/workbench_stats", summary="工作台统计", dependencies=[DependAuth])
async def get_workbench_stats():
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)

    ticket_total = await Ticket.all().count()
    ticket_pending_review = await Ticket.filter(status=TicketStatus.PENDING_REVIEW).count()
    ticket_tech_processing = await Ticket.filter(status=TicketStatus.TECH_PROCESSING).count()
    ticket_today_created = await Ticket.filter(created_at__gte=today_start, created_at__lt=tomorrow_start).count()
    ticket_today_done = await Ticket.filter(
        status=TicketStatus.DONE,
        finished_at__gte=today_start,
        finished_at__lt=tomorrow_start,
    ).count()
    register_pending = await PartnerRegistration.filter(status=PartnerRegisterStatus.PENDING).count()
    user_total = await User.all().count()
    auditlog_today = await AuditLog.filter(created_at__gte=today_start, created_at__lt=tomorrow_start).count()

    return Success(
        data={
            "ticket_total": ticket_total,
            "ticket_pending_review": ticket_pending_review,
            "ticket_tech_processing": ticket_tech_processing,
            "ticket_today_created": ticket_today_created,
            "ticket_today_done": ticket_today_done,
            "register_pending": register_pending,
            "user_total": user_total,
            "auditlog_today": auditlog_today,
        }
    )


@router.get("/userinfo", summary="查看用户信息", dependencies=[DependAuth])
async def get_userinfo():
    user_id = CTX_USER_ID.get()
    user_obj = await user_controller.get(id=user_id)
    data = await user_obj.to_dict(exclude_fields=["password"])
    data["avatar"] = "https://avatars.githubusercontent.com/u/54677442?v=4"
    return Success(data=data)


@router.get("/usermenu", summary="查看用户菜单", dependencies=[DependAuth])
async def get_user_menu():
    user_id = CTX_USER_ID.get()
    user_obj = await User.filter(id=user_id).first()
    menus: list[Menu] = []
    if user_obj.is_superuser:
        menus = await Menu.all()
    else:
        role_objs: list[Role] = await user_obj.roles
        for role_obj in role_objs:
            menu = await role_obj.menus
            menus.extend(menu)
        menus = list(set(menus))
    parent_menus: list[Menu] = []
    for menu in menus:
        if menu.parent_id == 0:
            parent_menus.append(menu)
    res = []
    for parent_menu in parent_menus:
        parent_menu_dict = await parent_menu.to_dict()
        parent_menu_dict["children"] = []
        for menu in menus:
            if menu.parent_id == parent_menu.id:
                parent_menu_dict["children"].append(await menu.to_dict())
        res.append(parent_menu_dict)
    return Success(data=res)


@router.get("/userapi", summary="查看用户API", dependencies=[DependAuth])
async def get_user_api():
    user_id = CTX_USER_ID.get()
    user_obj = await User.filter(id=user_id).first()
    if user_obj.is_superuser:
        api_objs: list[Api] = await Api.all()
        apis = [api.method.lower() + api.path for api in api_objs]
        return Success(data=apis)
    role_objs: list[Role] = await user_obj.roles
    apis = []
    for role_obj in role_objs:
        api_objs: list[Api] = await role_obj.apis
        apis.extend([api.method.lower() + api.path for api in api_objs])
    apis = list(set(apis))
    return Success(data=apis)


@router.post("/update_password", summary="修改密码", dependencies=[DependAuth])
async def update_user_password(req_in: UpdatePassword):
    user_id = CTX_USER_ID.get()
    user = await user_controller.get(user_id)
    verified = verify_password(req_in.old_password, user.password)
    if not verified:
        return Fail(msg="旧密码验证错误！")
    user.password = get_password_hash(req_in.new_password)
    await user.save()
    return Success(msg="修改成功")
