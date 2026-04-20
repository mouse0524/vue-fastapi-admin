from datetime import datetime
from typing import List, Optional

from fastapi.exceptions import HTTPException

from app.core.crud import CRUDBase
from app.log import logger
from app.models.admin import User
from app.schemas.login import CredentialsSchema
from app.schemas.users import UserCreate, UserUpdate
from app.utils.password import get_password_hash, verify_password

from .role import role_controller


class UserController(CRUDBase[User, UserCreate, UserUpdate]):
    def __init__(self):
        super().__init__(model=User)

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.model.filter(email=email).first()

    async def get_by_username(self, username: str) -> Optional[User]:
        return await self.model.filter(username=username).first()

    async def create_user(self, obj_in: UserCreate) -> User:
        logger.info("[user.create] start username={} email={} dept_id={}", obj_in.username, obj_in.email, obj_in.dept_id)
        obj_in.password = get_password_hash(password=obj_in.password)
        obj = await self.create(obj_in)
        logger.info("[user.create] success user_id={} username={}", obj.id, obj.username)
        return obj

    async def update_last_login(self, id: int) -> None:
        user = await self.model.get(id=id)
        user.last_login = datetime.now()
        await user.save()
        logger.info("[user.login] update_last_login user_id={} username={}", user.id, user.username)

    async def authenticate(self, credentials: CredentialsSchema) -> Optional["User"]:
        logger.info("[user.auth] start username={}", credentials.username)
        user = await self.model.filter(username=credentials.username).first()
        if not user:
            logger.warning("[user.auth] user_not_found username={}", credentials.username)
            raise HTTPException(status_code=400, detail="无效的用户名")
        verified = verify_password(credentials.password, user.password)
        if not verified:
            logger.warning("[user.auth] wrong_password username={} user_id={}", credentials.username, user.id)
            raise HTTPException(status_code=400, detail="密码错误!")
        if not user.is_active:
            logger.warning("[user.auth] disabled username={} user_id={}", user.username, user.id)
            raise HTTPException(status_code=400, detail="用户已被禁用")
        logger.info("[user.auth] success username={} user_id={}", user.username, user.id)
        return user

    async def update_roles(self, user: User, role_ids: List[int]) -> None:
        logger.info("[user.role] update start user_id={} role_ids={}", user.id, role_ids)
        await user.roles.clear()
        for role_id in role_ids:
            role_obj = await role_controller.get(id=role_id)
            await user.roles.add(role_obj)
        logger.info("[user.role] update success user_id={} role_count={}", user.id, len(role_ids))

    async def reset_password(self, user_id: int):
        logger.info("[user.reset_password] start user_id={}", user_id)
        user_obj = await self.get(id=user_id)
        if user_obj.is_superuser:
            logger.warning("[user.reset_password] deny_superuser user_id={}", user_id)
            raise HTTPException(status_code=403, detail="不允许重置超级管理员密码")
        user_obj.password = get_password_hash(password="123456")
        await user_obj.save()
        logger.info("[user.reset_password] success user_id={} username={}", user_obj.id, user_obj.username)


user_controller = UserController()
