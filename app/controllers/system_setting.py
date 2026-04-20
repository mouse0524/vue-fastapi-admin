import os
import uuid
from datetime import datetime

from fastapi import HTTPException, UploadFile

from app.log import logger
from app.models.admin import SystemSetting
from app.settings import settings


class SystemSettingController:
    async def get_or_create(self) -> SystemSetting:
        setting = await SystemSetting.first()
        if not setting:
            setting = await SystemSetting.create()
            logger.info("[settings] create default setting_id={}", setting.id)
        return setting

    async def get_public_config(self) -> dict:
        setting = await self.get_or_create()
        data = await setting.to_dict(exclude_fields=["smtp_password"])
        logo_url = "/api/v1/base/site_logo" if data.get("site_logo") else ""
        return {
            "site_title": data.get("site_title"),
            "site_logo": logo_url,
            "allow_partner_register": data.get("allow_partner_register"),
            "ticket_categories": data.get("ticket_categories") or [],
        }

    async def update(self, payload: dict) -> SystemSetting:
        logger.info("[settings.update] start keys={}", sorted(list(payload.keys())))
        setting = await self.get_or_create()
        setting.update_from_dict(payload)
        await setting.save()
        logger.info("[settings.update] success setting_id={}", setting.id)
        return setting

    async def upload_logo(self, file: UploadFile) -> str:
        logger.info("[settings.logo] start filename={} content_type={}", file.filename, file.content_type)
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in {".jpg", ".jpeg", ".png", ".webp", ".svg"}:
            raise HTTPException(status_code=400, detail="Logo仅支持 jpg/jpeg/png/webp/svg")

        data = await file.read()
        if len(data) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="Logo文件大小超限")

        now = datetime.now()
        rel_dir = os.path.join("site", "logo", now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"))
        abs_dir = os.path.join(settings.UPLOAD_DIR, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{ext}"
        rel_path = os.path.join(rel_dir, filename).replace("\\", "/")
        abs_path = os.path.join(settings.UPLOAD_DIR, rel_path)

        with open(abs_path, "wb") as f:
            f.write(data)

        setting = await self.get_or_create()
        setting.site_logo = rel_path
        await setting.save()
        logger.info("[settings.logo] success setting_id={} path={}", setting.id, rel_path)
        return rel_path

    async def get_logo_abs_path(self) -> str:
        setting = await self.get_or_create()
        if not setting.site_logo:
            raise HTTPException(status_code=404, detail="未配置站点Logo")

        abs_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, setting.site_logo))
        upload_root = os.path.abspath(settings.UPLOAD_DIR)
        if not abs_path.startswith(upload_root):
            raise HTTPException(status_code=400, detail="Logo路径非法")
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="Logo文件不存在")
        return abs_path


system_setting_controller = SystemSettingController()
