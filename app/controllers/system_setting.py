import os
import uuid
from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import HTTPException, UploadFile

from app.log import logger
from app.models.admin import SystemSetting
from app.settings import settings


class SystemSettingController:
    @staticmethod
    def _mask_secret(value: str | None) -> str:
        if not value:
            return ""
        return "******"

    async def get_safe_dict(self) -> dict:
        setting = await self.get_or_create()
        data = await setting.to_dict()
        data["smtp_password"] = self._mask_secret(data.get("smtp_password"))
        data["webdav_password"] = self._mask_secret(data.get("webdav_password"))
        data["llm_api_key"] = self._mask_secret(data.get("llm_api_key"))
        return data

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

    async def test_webdav_connection(self, payload: dict | None = None) -> dict:
        setting = await self.get_or_create()
        db_data = await setting.to_dict()
        req_data = payload or {}

        enabled = req_data.get("webdav_enabled", db_data.get("webdav_enabled"))
        base_url = (req_data.get("webdav_base_url") if req_data.get("webdav_base_url") is not None else db_data.get("webdav_base_url"))
        username = (req_data.get("webdav_username") if req_data.get("webdav_username") is not None else db_data.get("webdav_username"))
        pwd_input = req_data.get("webdav_password")
        if pwd_input == "******":
            password = db_data.get("webdav_password")
        elif pwd_input is None:
            password = db_data.get("webdav_password")
        else:
            password = pwd_input

        if not enabled:
            raise HTTPException(status_code=400, detail="WebDAV未启用，请先开启")
        if not base_url:
            raise HTTPException(status_code=400, detail="WebDAV Base URL 未配置")
        if not username or not password:
            raise HTTPException(status_code=400, detail="WebDAV账号或密码未配置")

        test_url = base_url.rstrip("/") + quote("/", safe="/")
        body = """<?xml version=\"1.0\" encoding=\"utf-8\" ?><d:propfind xmlns:d=\"DAV:\"><d:allprop/></d:propfind>"""

        logger.info("[settings.webdav.test] start base_url={} username={}", base_url, username)
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.request(
                    "PROPFIND",
                    test_url,
                    content=body,
                    headers={"Depth": "0", "Content-Type": "application/xml"},
                    auth=(username, password),
                )
        except Exception as exc:
            logger.exception("[settings.webdav.test] network_error base_url={} username={}", base_url, username)
            raise HTTPException(status_code=400, detail=f"连接失败：{exc}")

        if response.status_code not in {200, 207}:
            logger.warning(
                "[settings.webdav.test] failed status={} base_url={} username={}",
                response.status_code,
                base_url,
                username,
            )
            raise HTTPException(status_code=400, detail=f"连接失败，HTTP状态码：{response.status_code}")

        logger.info("[settings.webdav.test] success base_url={} username={}", base_url, username)
        return {
            "ok": True,
            "status_code": response.status_code,
            "message": "WebDAV连接成功",
        }

    async def update(self, payload: dict) -> SystemSetting:
        logger.info("[settings.update] start keys={}", sorted(list(payload.keys())))
        setting = await self.get_or_create()
        if payload.get("smtp_password") == "******":
            payload.pop("smtp_password", None)
        if payload.get("webdav_password") == "******":
            payload.pop("webdav_password", None)
        if payload.get("llm_api_key") == "******":
            payload.pop("llm_api_key", None)
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
