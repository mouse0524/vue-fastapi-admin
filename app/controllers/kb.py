from datetime import datetime
import os
import uuid

from fastapi import HTTPException, UploadFile
from tortoise.expressions import Q

from app.controllers.agent_orchestrator import agent_orchestrator
from app.controllers.llm_gateway import llm_gateway
from app.models.kb import KbChunk, KbCitation, KbDocument, KbFeedback, KbLlmCallLog, KbMessage, KbSession, KbSpace
from app.settings import settings


class KbController:
    @staticmethod
    def _parse_text_content(filename: str, data: bytes) -> str | None:
        ext = os.path.splitext(filename or "")[1].lower()
        if ext in {".txt", ".md", ".log", ".csv", ".json"}:
            return data.decode("utf-8", errors="ignore")
        return None

    async def list_spaces(self, *, page: int, page_size: int, keyword: str | None, owner_id: int, is_admin: bool):
        q = Q(status=True)
        if keyword:
            q &= Q(name__contains=keyword)
        if not is_admin:
            q &= Q(owner_id=owner_id) | Q(is_public=True)

        query = KbSpace.filter(q).order_by("-id")
        total = await query.count()
        rows = await query.offset((page - 1) * page_size).limit(page_size)
        return total, rows

    async def create_space(self, *, owner_id: int, payload: dict) -> dict:
        obj = await KbSpace.create(owner_id=owner_id, **payload)
        return await obj.to_dict()

    async def update_space(self, *, owner_id: int, payload: dict, is_admin: bool) -> dict:
        space_id = payload.pop("id")
        obj = await KbSpace.filter(id=space_id).first()
        if not obj:
            raise HTTPException(status_code=404, detail="知识空间不存在")
        if not is_admin and obj.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="无权限修改该知识空间")

        obj.update_from_dict({k: v for k, v in payload.items() if v is not None})
        await obj.save()
        return await obj.to_dict()

    async def list_documents(
        self,
        *,
        page: int,
        page_size: int,
        space_id: int | None,
        keyword: str | None,
        owner_id: int,
        is_admin: bool,
    ):
        q = Q(is_deleted=False)
        if space_id:
            q &= Q(space_id=space_id)
        if keyword:
            q &= Q(title__contains=keyword)
        if not is_admin:
            owned_space_ids = await KbSpace.filter(Q(owner_id=owner_id) | Q(is_public=True)).values_list("id", flat=True)
            if not owned_space_ids:
                return 0, []
            q &= Q(space_id__in=owned_space_ids)

        query = KbDocument.filter(q).order_by("-id")
        total = await query.count()
        rows = await query.offset((page - 1) * page_size).limit(page_size)
        return total, rows

    async def create_document(self, *, owner_id: int, payload: dict, is_admin: bool) -> dict:
        space = await KbSpace.filter(id=payload["space_id"]).first()
        if not space:
            raise HTTPException(status_code=404, detail="知识空间不存在")
        if not is_admin and space.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="无权限向该空间写入文档")

        content = payload.pop("content")
        now = datetime.now().strftime("%Y%m%d%H%M%S")
        title = payload.get("title")
        obj = await KbDocument.create(
            created_by=owner_id,
            parse_status="success",
            file_name=title,
            file_ext=".txt",
            storage_path=f"kb/manual/{space.id}/{now}.txt",
            **payload,
        )
        await KbChunk.create(
            space_id=space.id,
            document_id=obj.id,
            chunk_index=0,
            content=content,
            token_count=max(1, len(content) // 2),
            metadata_json={"source": "manual"},
        )
        return await obj.to_dict()

    async def upload_document(
        self,
        *,
        owner_id: int,
        space_id: int,
        title: str | None,
        file: UploadFile,
        is_admin: bool,
    ) -> dict:
        space = await KbSpace.filter(id=space_id).first()
        if not space:
            raise HTTPException(status_code=404, detail="知识空间不存在")
        if not is_admin and space.owner_id != owner_id:
            raise HTTPException(status_code=403, detail="无权限向该空间写入文档")

        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        ext = os.path.splitext(filename)[1].lower()
        if ext and ext not in settings.ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="不支持的文件类型")

        data = await file.read()
        if len(data) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="文件大小超限")

        now = datetime.now()
        rel_dir = os.path.join("kb", now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"))
        abs_dir = os.path.join(settings.UPLOAD_DIR, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}{ext}"
        rel_path = os.path.join(rel_dir, stored_name).replace("\\", "/")
        abs_path = os.path.join(settings.UPLOAD_DIR, rel_path)
        with open(abs_path, "wb") as f:
            f.write(data)

        text_content = self._parse_text_content(filename, data)
        parse_status = "success" if text_content else "pending"
        parse_error = None if text_content else "当前文件类型待异步解析"
        doc_title = (title or "").strip() or filename

        obj = await KbDocument.create(
            space_id=space_id,
            title=doc_title,
            source_type="upload",
            source_url=None,
            file_name=filename,
            file_ext=ext,
            file_size=len(data),
            file_hash=None,
            storage_path=rel_path,
            parse_status=parse_status,
            parse_error=parse_error,
            version=1,
            is_deleted=False,
            created_by=owner_id,
        )
        if text_content:
            await KbChunk.create(
                space_id=space_id,
                document_id=obj.id,
                chunk_index=0,
                content=text_content,
                token_count=max(1, len(text_content) // 2),
                metadata_json={"source": "upload", "file_name": filename},
            )
        return await obj.to_dict()

    async def reparse_document(self, *, document_id: int, owner_id: int, is_admin: bool) -> dict:
        doc = await KbDocument.filter(id=document_id, is_deleted=False).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        space = await KbSpace.filter(id=doc.space_id).first()
        if not space:
            raise HTTPException(status_code=404, detail="所属空间不存在")
        if not is_admin and not (doc.created_by == owner_id or space.owner_id == owner_id):
            raise HTTPException(status_code=403, detail="无权限重解析该文档")

        abs_path = os.path.join(settings.UPLOAD_DIR, doc.storage_path or "")
        if not doc.storage_path or not os.path.isfile(abs_path):
            doc.parse_status = "failed"
            doc.parse_error = "源文件不存在"
            await doc.save()
            return await doc.to_dict()

        with open(abs_path, "rb") as f:
            data = f.read()
        text_content = self._parse_text_content(doc.file_name or doc.title, data)
        await KbChunk.filter(document_id=doc.id).delete()

        if text_content:
            await KbChunk.create(
                space_id=doc.space_id,
                document_id=doc.id,
                chunk_index=0,
                content=text_content,
                token_count=max(1, len(text_content) // 2),
                metadata_json={"source": "reparse", "file_name": doc.file_name},
            )
            doc.parse_status = "success"
            doc.parse_error = None
        else:
            doc.parse_status = "pending"
            doc.parse_error = "当前文件类型待异步解析"
        await doc.save()
        return await doc.to_dict()

    async def delete_document(self, *, document_id: int, owner_id: int, is_admin: bool) -> dict:
        doc = await KbDocument.filter(id=document_id, is_deleted=False).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        space = await KbSpace.filter(id=doc.space_id).first()
        if not space:
            raise HTTPException(status_code=404, detail="所属空间不存在")
        if not is_admin and not (doc.created_by == owner_id or space.owner_id == owner_id):
            raise HTTPException(status_code=403, detail="无权限删除该文档")

        doc.is_deleted = True
        doc.parse_status = "deleted"
        await doc.save()
        return await doc.to_dict()

    async def create_session(self, *, user_id: int, payload: dict, is_admin: bool):
        space = await KbSpace.filter(id=payload["space_id"]).first()
        if not space:
            raise HTTPException(status_code=404, detail="知识空间不存在")
        if not is_admin and not (space.is_public or space.owner_id == user_id):
            raise HTTPException(status_code=403, detail="无权限访问该知识空间")
        obj = await KbSession.create(user_id=user_id, **payload)
        return await obj.to_dict()

    async def list_sessions(self, *, user_id: int, page: int, page_size: int):
        query = KbSession.filter(user_id=user_id).order_by("-id")
        total = await query.count()
        rows = await query.offset((page - 1) * page_size).limit(page_size)
        return total, rows

    async def list_messages(self, *, session_id: int, user_id: int, is_admin: bool):
        session = await KbSession.filter(id=session_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="会话不存在")
        if not is_admin and session.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权限查看该会话")

        rows = await KbMessage.filter(session_id=session_id).order_by("id")
        return [await item.to_dict() for item in rows]

    async def ask(self, *, user_id: int, payload: dict, is_admin: bool) -> dict:
        space = await KbSpace.filter(id=payload["space_id"]).first()
        if not space:
            raise HTTPException(status_code=404, detail="知识空间不存在")
        if not is_admin and not (space.is_public or space.owner_id == user_id):
            raise HTTPException(status_code=403, detail="无权限访问该知识空间")

        session_id = payload.get("session_id")
        if session_id:
            session = await KbSession.filter(id=session_id).first()
            if not session:
                raise HTTPException(status_code=404, detail="会话不存在")
            if not is_admin and session.user_id != user_id:
                raise HTTPException(status_code=403, detail="无权限访问该会话")
        else:
            session = await KbSession.create(space_id=space.id, user_id=user_id, title=payload["question"][:30], status="active")

        user_msg = await KbMessage.create(session_id=session.id, role="user", content=payload["question"])

        result = await agent_orchestrator.ask(space_id=space.id, question=payload["question"])
        assistant_msg = await KbMessage.create(
            session_id=session.id,
            role="assistant",
            content=result["answer"],
            model_name=result["model"],
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            latency_ms=result["latency_ms"],
        )
        await KbLlmCallLog.create(
            trace_id=None,
            session_id=session.id,
            message_id=assistant_msg.id,
            node_name="answer",
            provider=result.get("provider"),
            model_code=result.get("model"),
            prompt_tokens=result["prompt_tokens"],
            completion_tokens=result["completion_tokens"],
            latency_ms=result["latency_ms"],
            request_json=result.get("request_payload"),
            response_json=result.get("response_payload"),
            error_code=result.get("error_code"),
            cost_estimate=0.0,
        )

        citations = []
        for item in result["citations"]:
            citation = await KbCitation.create(
                message_id=assistant_msg.id,
                document_id=item["document_id"],
                chunk_id=item["chunk_id"],
                score=item["score"],
                snippet=item["snippet"],
            )
            citations.append(await citation.to_dict())

        return {
            "session_id": session.id,
            "question_message_id": user_msg.id,
            "answer_message_id": assistant_msg.id,
            "answer": result["answer"],
            "model": result["model"],
            "prompt_tokens": result["prompt_tokens"],
            "completion_tokens": result["completion_tokens"],
            "latency_ms": result["latency_ms"],
            "citations": citations,
        }

    async def create_feedback(self, *, user_id: int, payload: dict) -> dict:
        msg = await KbMessage.filter(id=payload["message_id"], role="assistant").first()
        if not msg:
            raise HTTPException(status_code=404, detail="回答消息不存在")
        obj = await KbFeedback.create(user_id=user_id, **payload)
        return await obj.to_dict()

    async def list_feedback(self, *, page: int, page_size: int, status: str | None):
        q = Q()
        if status:
            q &= Q(status=status)
        query = KbFeedback.filter(q).order_by("-id")
        total = await query.count()
        rows = await query.offset((page - 1) * page_size).limit(page_size)
        return total, rows

    async def list_llm_logs(
        self,
        *,
        page: int,
        page_size: int,
        provider: str | None,
        model_code: str | None,
        error_code: str | None,
        session_id: int | None,
    ):
        q = Q()
        if provider:
            q &= Q(provider__contains=provider)
        if model_code:
            q &= Q(model_code__contains=model_code)
        if error_code:
            q &= Q(error_code__contains=error_code)
        if session_id:
            q &= Q(session_id=session_id)

        query = KbLlmCallLog.filter(q).order_by("-id")
        total = await query.count()
        rows = await query.offset((page - 1) * page_size).limit(page_size)
        return total, rows

    async def test_llm_connectivity(self) -> dict:
        result = await llm_gateway.chat(question="连通性测试", contexts=["系统连通性检测"], model=settings.KB_DEFAULT_MODEL)
        ok = not bool(result.get("error_code"))
        return {
            "ok": ok,
            "provider": result.get("provider"),
            "model": result.get("model"),
            "latency_ms": result.get("latency_ms"),
            "prompt_tokens": (result.get("usage") or {}).get("prompt_tokens") if isinstance(result.get("usage"), dict) else None,
            "completion_tokens": (result.get("usage") or {}).get("completion_tokens")
            if isinstance(result.get("usage"), dict)
            else None,
            "error_code": result.get("error_code"),
            "content_preview": (result.get("content") or "")[:200],
        }


kb_controller = KbController()
