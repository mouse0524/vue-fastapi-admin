from fastapi import APIRouter, Query
from tortoise.expressions import Q

from app.controllers.mail import mail_controller
from app.controllers.partner import partner_controller
from app.controllers.system_setting import system_setting_controller
from app.core.ctx import CTX_USER_ID
from app.core.dependency import DependAuth
from app.models.admin import PartnerRegistration, User
from app.models.enums import PartnerRegisterStatus, RegisterType
from app.schemas.base import Fail, Success, SuccessExtra
from app.schemas.partner import PartnerRegisterIn, PartnerReviewIn, UserRegisterIn

router = APIRouter()


async def _is_cs_or_admin(user_id: int) -> bool:
    user = await User.filter(id=user_id).first()
    if not user:
        return False
    if user.is_superuser:
        return True
    roles = await user.roles
    role_names = [role.name for role in roles]
    return "管理员" in role_names or "客服" in role_names


@router.post("/register", summary="渠道商/用户注册")
async def partner_register(payload: PartnerRegisterIn):
    config = await system_setting_controller.get_public_config()
    if not config.get("allow_partner_register", True):
        return Fail(code=403, msg="当前未开放注册")

    email_valid = await mail_controller.verify_email_code(payload.email, payload.email_code)
    if not email_valid:
        return Fail(code=400, msg="邮箱验证码错误或已过期")

    data = payload.model_dump()
    register_obj = await partner_controller.register(data)
    return Success(msg="注册成功，请等待审核", data=await register_obj.to_dict(exclude_fields=["password_hash"]))


@router.post("/register/channel", summary="渠道商注册")
async def channel_register(payload: PartnerRegisterIn):
    payload.register_type = RegisterType.CHANNEL
    return await partner_register(payload)


@router.post("/register/user", summary="用户注册")
async def user_register(payload: UserRegisterIn):
    payload.register_type = RegisterType.USER
    return await partner_register(payload)


@router.get("/register/list", summary="注册申请列表", dependencies=[DependAuth])
async def partner_register_list(
    page: int = Query(1, description="页码"),
    page_size: int = Query(10, description="每页数量"),
    status: PartnerRegisterStatus | None = Query(None, description="审核状态"),
    keyword: str | None = Query(None, description="关键词"),
):
    user_id = CTX_USER_ID.get()
    if not await _is_cs_or_admin(user_id):
        return Fail(code=403, msg="无权限查看申请列表")

    q = Q()
    if status:
        q &= Q(status=status)
    if keyword:
        q &= Q(company_name__contains=keyword) | Q(contact_name__contains=keyword) | Q(email__contains=keyword)

    query = PartnerRegistration.filter(q)
    total = await query.count()
    rows = await query.offset((page - 1) * page_size).limit(page_size).order_by("-id")
    data = [await item.to_dict(exclude_fields=["password_hash"]) for item in rows]
    return SuccessExtra(data=data, total=total, page=page, page_size=page_size)


@router.post("/register/review", summary="审核注册", dependencies=[DependAuth])
async def partner_register_review(payload: PartnerReviewIn):
    user_id = CTX_USER_ID.get()
    if not await _is_cs_or_admin(user_id):
        return Fail(code=403, msg="无权限审核")

    if not payload.approved and not (payload.comment or "").strip():
        return Fail(code=400, msg="驳回时必须填写驳回理由")

    obj = await partner_controller.review(
        register_id=payload.id,
        reviewer_id=user_id,
        approved=payload.approved,
        comment=payload.comment,
    )
    return Success(msg="审核完成", data=await obj.to_dict(exclude_fields=["password_hash"]))
