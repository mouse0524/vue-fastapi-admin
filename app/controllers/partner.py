from datetime import datetime

from fastapi import HTTPException
from tortoise.expressions import Q

from app.models.admin import PartnerRegistration, Role, User
from app.models.enums import PartnerRegisterStatus, RegisterType
from app.controllers.mail import mail_controller
from app.utils.password import get_password_hash


class PartnerController:
    @staticmethod
    async def has_pending_registration(
        *,
        email: str | None = None,
        phone: str | None = None,
        username: str | None = None,
        hardware_id: str | None = None,
    ) -> bool:
        q = Q(status=PartnerRegisterStatus.PENDING)
        condition = Q()
        has_any = False
        if email:
            condition |= Q(email=email.strip().lower())
            has_any = True
        if phone:
            condition |= Q(phone=phone.strip())
            has_any = True
        if username:
            condition |= Q(username=username.strip())
            has_any = True
        if hardware_id:
            condition |= Q(hardware_id=hardware_id.strip())
            has_any = True
        if not has_any:
            return False
        return await PartnerRegistration.filter(q & condition).exists()

    async def register(self, payload: dict) -> PartnerRegistration:
        email = payload["email"].strip().lower()
        username = email
        phone = payload["phone"].strip()
        register_type = payload.get("register_type") or RegisterType.CHANNEL
        hardware_id = (payload.get("hardware_id") or "").strip() or None

        payload["email"] = email
        payload["username"] = username
        payload["phone"] = phone
        payload["register_type"] = register_type
        payload["hardware_id"] = hardware_id

        if register_type == RegisterType.USER and not hardware_id:
            raise HTTPException(status_code=400, detail="用户注册必须填写产品硬件ID")

        if await User.filter(email=email).exists():
            raise HTTPException(status_code=400, detail="邮箱已被注册")
        if await User.filter(username=username).exists():
            raise HTTPException(status_code=400, detail="用户名已存在")
        if await User.filter(phone=phone).exists():
            raise HTTPException(status_code=400, detail="手机号已被注册")
        if hardware_id and await User.filter(hardware_id=hardware_id).exists():
            raise HTTPException(status_code=400, detail="产品硬件ID已被注册")

        email_pending = await PartnerRegistration.filter(status=PartnerRegisterStatus.PENDING, email=email).exists()
        if email_pending:
            raise HTTPException(status_code=400, detail="该邮箱已有待审核申请")

        username_pending = await PartnerRegistration.filter(
            status=PartnerRegisterStatus.PENDING,
            username=username,
        ).exists()
        if username_pending:
            raise HTTPException(status_code=400, detail="该用户名已有待审核申请")

        phone_pending = await PartnerRegistration.filter(status=PartnerRegisterStatus.PENDING, phone=phone).exists()
        if phone_pending:
            raise HTTPException(status_code=400, detail="该手机号已有待审核申请")

        if hardware_id:
            hardware_pending = await PartnerRegistration.filter(
                status=PartnerRegisterStatus.PENDING,
                hardware_id=hardware_id,
            ).exists()
            if hardware_pending:
                raise HTTPException(status_code=400, detail="该产品硬件ID已有待审核申请")

        payload.pop("email_code", None)
        payload["password_hash"] = get_password_hash(payload.pop("password"))
        return await PartnerRegistration.create(**payload)

    async def review(
        self, *, register_id: int, reviewer_id: int, approved: bool, comment: str | None
    ) -> PartnerRegistration:
        register_obj = await PartnerRegistration.get(id=register_id)
        if register_obj.status != PartnerRegisterStatus.PENDING:
            raise HTTPException(status_code=400, detail="该申请已审核")

        register_obj.reviewer_id = reviewer_id
        register_obj.review_comment = comment
        register_obj.reviewed_at = datetime.now()

        if approved:
            role_name = "渠道商" if register_obj.register_type == RegisterType.CHANNEL else "用户"
            role = await Role.filter(name=role_name).first()
            if not role and role_name == "渠道商":
                role = await Role.filter(name="代理商").first()
            if not role:
                raise HTTPException(status_code=500, detail=f"{role_name}角色不存在")

            if await User.filter(email=register_obj.email).exists():
                raise HTTPException(status_code=400, detail="邮箱已被注册")
            if await User.filter(username=register_obj.username).exists():
                raise HTTPException(status_code=400, detail="用户名已存在")
            if await User.filter(phone=register_obj.phone).exists():
                raise HTTPException(status_code=400, detail="手机号已被注册")
            if register_obj.hardware_id and await User.filter(hardware_id=register_obj.hardware_id).exists():
                raise HTTPException(status_code=400, detail="产品硬件ID已被注册")

            user = await User.create(
                username=register_obj.email,
                company_name=register_obj.company_name,
                email=register_obj.email,
                phone=register_obj.phone,
                hardware_id=register_obj.hardware_id,
                alias=register_obj.contact_name,
                password=register_obj.password_hash,
                is_active=True,
                is_superuser=False,
            )
            await user.roles.add(role)
            register_obj.status = PartnerRegisterStatus.APPROVED
        else:
            register_obj.status = PartnerRegisterStatus.REJECTED

        await register_obj.save()

        await mail_controller.send_register_review_notice(
            to_email=register_obj.email,
            contact_name=register_obj.contact_name,
            register_type=register_obj.register_type,
            approved=approved,
            reason=comment,
        )

        return register_obj


partner_controller = PartnerController()
