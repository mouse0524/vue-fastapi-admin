import os
import uuid
from datetime import datetime

from fastapi import HTTPException, UploadFile
from tortoise.expressions import Q

from app.log import logger
from app.controllers.system_setting import system_setting_controller
from app.models.admin import Ticket, TicketActionLog, TicketAttachment, User
from app.models.enums import TicketActionType, TicketStatus
from app.settings import settings
from app.utils.http_headers import build_download_content_disposition


class TicketController:
    @staticmethod
    def _next_ticket_no() -> str:
        return f"TK{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:6].upper()}"

    async def _write_action(
        self,
        *,
        ticket_id: int,
        action: TicketActionType,
        from_status: TicketStatus | None,
        to_status: TicketStatus,
        operator_id: int,
        comment: str | None,
    ) -> None:
        await TicketActionLog.create(
            ticket_id=ticket_id,
            action=action,
            from_status=from_status,
            to_status=to_status,
            operator_id=operator_id,
            comment=comment,
        )

    async def create_ticket(self, *, submitter_id: int, payload: dict) -> Ticket:
        logger.info("[ticket.create] start submitter_id={} category={} title={}", submitter_id, payload.get("category"), payload.get("title"))
        attachment_ids = payload.pop("attachment_ids", [])
        ticket = await Ticket.create(
            ticket_no=self._next_ticket_no(),
            submitter_id=submitter_id,
            status=TicketStatus.PENDING_REVIEW,
            **payload,
        )
        if attachment_ids:
            await TicketAttachment.filter(
                id__in=attachment_ids,
                uploader_id=submitter_id,
                ticket_id=None,
            ).update(ticket_id=ticket.id)
        await self._write_action(
            ticket_id=ticket.id,
            action=TicketActionType.SUBMIT,
            from_status=None,
            to_status=TicketStatus.PENDING_REVIEW,
            operator_id=submitter_id,
            comment=None,
        )
        logger.info(
            "[ticket.create] success ticket_id={} ticket_no={} submitter_id={} attachment_count={}",
            ticket.id,
            ticket.ticket_no,
            submitter_id,
            len(attachment_ids),
        )
        return ticket

    async def get_ticket(self, ticket_id: int) -> Ticket:
        return await Ticket.get(id=ticket_id)

    async def list_tickets(self, *, page: int, page_size: int, search: Q) -> tuple[int, list[Ticket]]:
        query = Ticket.filter(search)
        total = await query.count()
        rows = await query.offset((page - 1) * page_size).limit(page_size).order_by("-id")
        logger.info("[ticket.list] page={} page_size={} total={}", page, page_size, total)
        return total, rows

    async def set_customer_service_review(
        self, *, ticket_id: int, reviewer_id: int, approved: bool, comment: str | None
    ) -> Ticket:
        logger.info(
            "[ticket.cs_review] start ticket_id={} reviewer_id={} approved={} comment={}",
            ticket_id,
            reviewer_id,
            approved,
            comment,
        )
        ticket = await self.get_ticket(ticket_id)
        if ticket.status != TicketStatus.PENDING_REVIEW:
            raise HTTPException(status_code=400, detail="当前状态不可进行客服审核")

        old_status = ticket.status
        if approved:
            ticket.status = TicketStatus.TECH_PROCESSING
            ticket.reviewer_id = reviewer_id
            ticket.reject_reason = None
            action = TicketActionType.CS_APPROVE
        else:
            ticket.status = TicketStatus.CS_REJECTED
            ticket.reviewer_id = reviewer_id
            ticket.reject_reason = comment or "客服驳回"
            action = TicketActionType.CS_REJECT

        await ticket.save()
        await self._write_action(
            ticket_id=ticket.id,
            action=action,
            from_status=old_status,
            to_status=ticket.status,
            operator_id=reviewer_id,
            comment=comment,
        )
        logger.info(
            "[ticket.cs_review] success ticket_id={} from_status={} to_status={} reviewer_id={}",
            ticket.id,
            old_status,
            ticket.status,
            reviewer_id,
        )
        return ticket

    async def set_tech_action(
        self, *, ticket_id: int, tech_id: int, action: TicketActionType, comment: str | None, root_cause: str | None
    ) -> Ticket:
        logger.info(
            "[ticket.tech_action] start ticket_id={} tech_id={} action={} comment={}",
            ticket_id,
            tech_id,
            action,
            comment,
        )
        ticket = await self.get_ticket(ticket_id)
        if ticket.status != TicketStatus.TECH_PROCESSING:
            raise HTTPException(status_code=400, detail="当前状态不可进行技术处理")

        if action not in {TicketActionType.TECH_START, TicketActionType.TECH_REJECT, TicketActionType.FINISH}:
            raise HTTPException(status_code=400, detail="不支持的技术操作")

        if action == TicketActionType.FINISH:
            setting = await system_setting_controller.get_public_config()
            root_causes = setting.get("ticket_root_causes") or []
            normalized_root_cause = (root_cause or "").strip()
            if not normalized_root_cause:
                raise HTTPException(status_code=400, detail="处理完成时必须选择问题根因")
            if root_causes and normalized_root_cause not in root_causes:
                raise HTTPException(status_code=400, detail="问题根因不合法，请刷新页面后重试")
        else:
            normalized_root_cause = None

        old_status = ticket.status
        if action == TicketActionType.TECH_REJECT:
            ticket.status = TicketStatus.PENDING_REVIEW
            ticket.reject_reason = comment or "技术驳回"
        elif action == TicketActionType.FINISH:
            ticket.status = TicketStatus.DONE
            ticket.reject_reason = None
            ticket.root_cause = normalized_root_cause
            ticket.finished_at = datetime.now()
        else:
            ticket.status = TicketStatus.TECH_PROCESSING
            ticket.reject_reason = None

        ticket.tech_id = tech_id
        await ticket.save()
        await self._write_action(
            ticket_id=ticket.id,
            action=action,
            from_status=old_status,
            to_status=ticket.status,
            operator_id=tech_id,
            comment=comment,
        )
        logger.info(
            "[ticket.tech_action] success ticket_id={} from_status={} to_status={} tech_id={}",
            ticket.id,
            old_status,
            ticket.status,
            tech_id,
        )
        return ticket

    async def resubmit_ticket(
        self, *, ticket_id: int, submitter_id: int, description: str | None, attachment_ids: list[int]
    ) -> Ticket:
        logger.info(
            "[ticket.resubmit] start ticket_id={} submitter_id={} attachment_count={} has_description={}",
            ticket_id,
            submitter_id,
            len(attachment_ids),
            bool(description),
        )
        ticket = await self.get_ticket(ticket_id)
        if ticket.submitter_id != submitter_id:
            raise HTTPException(status_code=403, detail="只能由提交人重提工单")
        if ticket.status not in {TicketStatus.CS_REJECTED, TicketStatus.TECH_REJECTED}:
            raise HTTPException(status_code=400, detail="当前状态不可重提")

        old_status = ticket.status
        ticket.status = TicketStatus.PENDING_REVIEW
        if description:
            ticket.description = description
        ticket.reject_reason = None
        await ticket.save()

        if attachment_ids:
            await TicketAttachment.filter(
                id__in=attachment_ids,
                uploader_id=submitter_id,
                ticket_id=None,
            ).update(ticket_id=ticket.id)

        await self._write_action(
            ticket_id=ticket.id,
            action=TicketActionType.RESUBMIT,
            from_status=old_status,
            to_status=ticket.status,
            operator_id=submitter_id,
            comment="重提工单",
        )
        logger.info(
            "[ticket.resubmit] success ticket_id={} from_status={} to_status={} submitter_id={}",
            ticket.id,
            old_status,
            ticket.status,
            submitter_id,
        )
        return ticket

    async def upload_attachment(self, *, uploader_id: int, file: UploadFile) -> TicketAttachment:
        logger.info("[ticket.upload] start uploader_id={} filename={} content_type={}", uploader_id, file.filename, file.content_type)
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="不支持的文件类型")

        data = await file.read()
        if len(data) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="文件大小超限")

        now = datetime.now()
        rel_dir = os.path.join("tickets", now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"))
        abs_dir = os.path.join(settings.UPLOAD_DIR, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{ext}"
        rel_path = os.path.join(rel_dir, filename).replace("\\", "/")
        abs_path = os.path.join(settings.UPLOAD_DIR, rel_path)

        with open(abs_path, "wb") as f:
            f.write(data)

        attachment = await TicketAttachment.create(
            ticket_id=None,
            origin_name=file.filename or filename,
            file_path=rel_path,
            file_size=len(data),
            mime_type=file.content_type or "application/octet-stream",
            uploader_id=uploader_id,
        )
        logger.info(
            "[ticket.upload] success attachment_id={} uploader_id={} size={} path={}",
            attachment.id,
            uploader_id,
            attachment.file_size,
            attachment.file_path,
        )
        return attachment

    async def get_ticket_detail(self, ticket_id: int) -> dict:
        ticket = await self.get_ticket(ticket_id)
        data = await ticket.to_dict()
        data["attachments"] = [
            await item.to_dict() for item in await TicketAttachment.filter(ticket_id=ticket_id).order_by("id")
        ]
        data["actions"] = [
            await item.to_dict() for item in await TicketActionLog.filter(ticket_id=ticket_id).order_by("id")
        ]
        submitter = await User.filter(id=ticket.submitter_id).first()
        data["submitter_name"] = submitter.username if submitter else ""
        return data

    async def get_attachment_download(self, *, attachment_id: int, user: User, role_names: list[str]) -> dict:
        attachment = await TicketAttachment.filter(id=attachment_id).first()
        if not attachment:
            raise HTTPException(status_code=404, detail="附件不存在")
        if not attachment.ticket_id:
            raise HTTPException(status_code=400, detail="附件尚未绑定工单")

        ticket = await Ticket.filter(id=attachment.ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="所属工单不存在")

        if not user.is_superuser and "管理员" not in role_names and "客服" not in role_names:
            if "技术" in role_names:
                if ticket.submitter_id != user.id and ticket.tech_id != user.id:
                    raise HTTPException(status_code=403, detail="无权限下载该附件")
            elif ticket.submitter_id != user.id:
                raise HTTPException(status_code=403, detail="无权限下载该附件")

        abs_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, attachment.file_path))
        upload_root = os.path.abspath(settings.UPLOAD_DIR)
        if not abs_path.startswith(upload_root):
            raise HTTPException(status_code=400, detail="附件路径非法")
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="附件文件不存在")

        return {
            "abs_path": abs_path,
            "filename": attachment.origin_name or os.path.basename(attachment.file_path),
            "media_type": attachment.mime_type or "application/octet-stream",
            "headers": {"Content-Disposition": build_download_content_disposition(attachment.origin_name or "download")},
        }


ticket_controller = TicketController()
