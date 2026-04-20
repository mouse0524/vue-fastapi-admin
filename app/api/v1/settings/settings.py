from fastapi import APIRouter, File, UploadFile

from app.controllers.system_setting import system_setting_controller
from app.schemas.base import Success
from app.schemas.settings import SystemSettingUpdateIn

router = APIRouter()


@router.get("/get", summary="获取系统设置")
async def get_system_setting():
    setting = await system_setting_controller.get_or_create()
    data = await setting.to_dict()
    return Success(data=data)


@router.post("/update", summary="更新系统设置")
async def update_system_setting(payload: SystemSettingUpdateIn):
    setting = await system_setting_controller.update(payload.model_dump())
    data = await setting.to_dict(exclude_fields=["smtp_password"])
    return Success(msg="保存成功", data=data)


@router.post("/upload_logo", summary="上传站点Logo")
async def upload_site_logo(file: UploadFile = File(...)):
    rel_path = await system_setting_controller.upload_logo(file)
    return Success(msg="上传成功", data={"site_logo": rel_path, "site_logo_url": "/api/v1/base/site_logo"})
