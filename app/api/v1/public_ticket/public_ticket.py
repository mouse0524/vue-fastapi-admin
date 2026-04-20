from fastapi import APIRouter, File, Query, UploadFile

from app.controllers.captcha import captcha_controller
from app.controllers.partner import partner_controller
from app.controllers.system_setting import system_setting_controller
from app.controllers.ticket import ticket_controller
from app.models.admin import TicketAttachment
from app.schemas.base import Fail, Success
from app.schemas.tickets import TicketCreate

router = APIRouter()


@router.post("/upload", summary="游客上传工单附件")
async def upload_public_ticket_attachment(file: UploadFile = File(...)):
    attachment = await ticket_controller.upload_attachment(uploader_id=0, file=file)
    return Success(data=await attachment.to_dict())


@router.post("/create", summary="游客提交工单")
async def create_public_ticket(payload: TicketCreate):
    pending = await partner_controller.has_pending_registration(email=payload.email, phone=payload.phone)
    if pending:
        return Fail(code=403, msg="当前账号存在待审核注册申请，暂不允许提交工单")

    valid = await captcha_controller.verify_captcha(payload.captcha_id, payload.captcha_code)
    if not valid:
        return Fail(code=400, msg="验证码错误或已过期")

    config = await system_setting_controller.get_public_config()
    categories = config.get("ticket_categories") or []
    if categories and payload.category not in categories:
        return Fail(code=400, msg="问题分类不合法，请刷新页面后重试")

    body = payload.model_dump(exclude={"captcha_id", "captcha_code"})
    ticket = await ticket_controller.create_ticket(submitter_id=0, payload=body)
    return Success(msg="提交成功", data=await ticket.to_dict())


@router.get("/attachments", summary="游客工单附件列表")
async def list_public_attachments(ids: str = Query("", description="附件ID，逗号分隔")):
    id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
    if not id_list:
        return Success(data=[])
    rows = await TicketAttachment.filter(id__in=id_list, uploader_id=0).order_by("id")
    data = [await item.to_dict() for item in rows]
    return Success(data=data)
