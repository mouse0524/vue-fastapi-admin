from datetime import datetime

from fastapi import HTTPException
from tortoise.expressions import Q

from app.log import logger
from app.models.admin import Dept, DeptClosure, PartnerRegistration, Role, User
from app.models.enums import PartnerRegisterStatus, RegisterType
from app.controllers.mail import mail_controller
from app.utils.password import get_password_hash


class PartnerController:
    @staticmethod
    async def _build_unique_username(email: str) -> str:
        return email.strip().lower()

    @staticmethod
    async def _build_unique_dept_name(raw_name: str, fallback_name: str) -> str:
        max_len = 20
        base = (raw_name or "").strip() or fallback_name
        base = base[:max_len] or fallback_name[:max_len] or "部门"

        if not await Dept.filter(name=base).exists():
            return base

        index = 2
        while True:
            suffix = f"-{index}"
            keep_len = max_len - len(suffix)
            keep_len = keep_len if keep_len > 0 else 1
            candidate = f"{base[:keep_len]}{suffix}"
            if not await Dept.filter(name=candidate).exists():
                return candidate
            index += 1

    @staticmethod
    async def _ensure_dept(name: str, parent_id: int = 0, desc: str = "") -> Dept:
        dept_obj = await Dept.filter(name=name).first()
        if dept_obj:
            logger.info("[partner.dept] reuse dept name={} dept_id={} parent_id={}", name, dept_obj.id, dept_obj.parent_id)
            if dept_obj.is_deleted:
                dept_obj.is_deleted = False
                dept_obj.parent_id = parent_id
                dept_obj.desc = desc or dept_obj.desc
                await dept_obj.save()
                logger.info("[partner.dept] revive dept name={} dept_id={} parent_id={}", name, dept_obj.id, parent_id)
            return dept_obj

        dept_obj = await Dept.create(name=name, parent_id=parent_id, desc=desc, order=0, is_deleted=False)
        logger.info("[partner.dept] create dept name={} dept_id={} parent_id={}", name, dept_obj.id, parent_id)

        closure_rows = []
        if parent_id != 0:
            parent_paths = await DeptClosure.filter(descendant=parent_id)
            for item in parent_paths:
                closure_rows.append(DeptClosure(ancestor=item.ancestor, descendant=dept_obj.id, level=item.level + 1))
        closure_rows.append(DeptClosure(ancestor=dept_obj.id, descendant=dept_obj.id, level=0))
        await DeptClosure.bulk_create(closure_rows)
        return dept_obj

    async def _ensure_user_dept(self, register_obj: PartnerRegistration) -> Dept:
        if register_obj.register_type == RegisterType.CHANNEL:
            parent_name = "渠道部门"
        else:
            parent_name = "用户部门"

        parent_dept = await self._ensure_dept(parent_name, parent_id=0, desc="注册审核自动创建")
        child_name = await self._build_unique_dept_name(
            raw_name=(register_obj.company_name or "").strip() or register_obj.contact_name,
            fallback_name=register_obj.contact_name,
        )
        child_desc = f"{('渠道商' if register_obj.register_type == RegisterType.CHANNEL else '用户')}注册自动创建"
        child_dept = await self._ensure_dept(child_name, parent_id=parent_dept.id, desc=child_desc)
        return child_dept

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
        username = await self._build_unique_username(email)
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
        logger.info(
            "[partner.review] start register_id={} reviewer_id={} approved={} comment={}",
            register_id,
            reviewer_id,
            approved,
            comment,
        )
        register_obj = await PartnerRegistration.get(id=register_id)
        if register_obj.status != PartnerRegisterStatus.PENDING:
            raise HTTPException(status_code=400, detail="该申请已审核")

        register_obj.reviewer_id = reviewer_id
        register_obj.review_comment = comment
        register_obj.reviewed_at = datetime.now()

        if approved:
            try:
                username = register_obj.username
                if not username or len(username) > 255:
                    username = await self._build_unique_username(register_obj.email)
                    register_obj.username = username

                role_name = "渠道商" if register_obj.register_type == RegisterType.CHANNEL else "用户"
                role = await Role.filter(name=role_name).first()
                if not role and role_name == "渠道商":
                    role = await Role.filter(name="代理商").first()
                if not role:
                    raise HTTPException(status_code=500, detail=f"{role_name}角色不存在")

                if await User.filter(email=register_obj.email).exists():
                    raise HTTPException(status_code=400, detail="邮箱已被注册")
                if await User.filter(username=username).exists():
                    raise HTTPException(status_code=400, detail="用户名已存在")
                if await User.filter(phone=register_obj.phone).exists():
                    raise HTTPException(status_code=400, detail="手机号已被注册")
                if register_obj.hardware_id and await User.filter(hardware_id=register_obj.hardware_id).exists():
                    raise HTTPException(status_code=400, detail="产品硬件ID已被注册")

                dept_obj = await self._ensure_user_dept(register_obj)
                logger.info(
                    "[partner.review] dept_ready register_id={} dept_id={} dept_name={}",
                    register_obj.id,
                    dept_obj.id,
                    dept_obj.name,
                )

                user = await User.create(
                    username=username,
                    company_name=register_obj.company_name,
                    email=register_obj.email,
                    phone=register_obj.phone,
                    hardware_id=register_obj.hardware_id,
                    alias=register_obj.contact_name,
                    password=register_obj.password_hash,
                    is_active=True,
                    is_superuser=False,
                    dept_id=dept_obj.id,
                )
                await user.roles.add(role)
                register_obj.status = PartnerRegisterStatus.APPROVED
            except Exception:
                logger.exception(
                    "[partner.review] failed register_id={} email={} register_type={}",
                    register_obj.id,
                    register_obj.email,
                    register_obj.register_type,
                )
                raise
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

        logger.info(
            "[partner.review] success register_id={} status={} reviewer_id={}",
            register_obj.id,
            register_obj.status,
            reviewer_id,
        )

        return register_obj


partner_controller = PartnerController()
