from __future__ import annotations

import os
import uuid
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from tortoise.expressions import Q

from app.models.admin import SkillKnowDocument, SkillKnowSkill
from app.models.enums import SkillKnowDocumentStatus, SkillKnowSkillCategory, SkillKnowSkillType
from app.schemas.skill_know import SkillKnowSkillIn
from app.services.skill_know.content_analyzer import skill_know_content_analyzer
from app.services.skill_know.document_parser import skill_know_document_parser
from app.services.skill_know.graph_service import skill_know_graph_service
from app.services.skill_know.skill_service import skill_know_skill_service
from app.services.skill_know.utils import document_to_dict, make_uri, new_uuid, sha256_text
from app.settings import settings


class SkillKnowDocumentService:
    def _upload_dir(self) -> str:
        path = os.path.join(settings.UPLOAD_DIR, "skill_know", datetime.now().strftime("%Y%m%d"))
        os.makedirs(path, exist_ok=True)
        return path

    async def upload(self, file: UploadFile, *, title: str | None = None, folder_id: int | None = None) -> dict:
        filename = (file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        ext = Path(filename).suffix.lower().lstrip(".") or "txt"
        if ext not in {"txt", "md", "markdown", "pdf", "docx", "doc"}:
            raise HTTPException(status_code=400, detail="仅支持 txt、md、pdf、docx 文档")
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        abs_path = os.path.join(self._upload_dir(), stored_name)
        content_bytes = await file.read()
        if len(content_bytes) > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(status_code=400, detail="文件大小超限")
        with open(abs_path, "wb") as f:
            f.write(content_bytes)
        doc_title = title or filename
        document = await SkillKnowDocument.create(
            uuid=new_uuid(),
            uri=make_uri("documents", uuid.uuid4().hex),
            title=doc_title,
            filename=filename,
            file_path=abs_path,
            file_size=len(content_bytes),
            file_type=ext,
            folder_id=folder_id,
            status=SkillKnowDocumentStatus.PROCESSING,
        )
        try:
            content = await skill_know_document_parser.parse(abs_path, ext)
            analysis = await skill_know_content_analyzer.analyze(doc_title, content)
            document.content = content
            document.content_hash = sha256_text(content)
            document.abstract = analysis["abstract"]
            document.overview = analysis["overview"]
            document.category = analysis["category"]
            document.tags = analysis["tags"]
            document.status = SkillKnowDocumentStatus.COMPLETED
            await document.save()
        except Exception as exc:
            document.status = SkillKnowDocumentStatus.FAILED
            document.error_message = str(exc)
            await document.save()
        return await document_to_dict(document)

    async def list(self, *, page: int, page_size: int, folder_id=None, category=None, status=None, is_converted=None) -> tuple[int, list[dict]]:
        q = Q()
        if folder_id is not None:
            q &= Q(folder_id=folder_id)
        if category:
            q &= Q(category=category)
        if status:
            q &= Q(status=status)
        if is_converted is not None:
            q &= Q(is_converted=is_converted)
        query = SkillKnowDocument.filter(q)
        total = await query.count()
        rows = await query.order_by("-id").offset((page - 1) * page_size).limit(page_size)
        return total, [await document_to_dict(item) for item in rows]

    async def get(self, document_id: int) -> dict:
        document = await SkillKnowDocument.filter(id=document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        return await document_to_dict(document)

    async def update(self, data) -> dict:
        document = await SkillKnowDocument.filter(id=data.document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        for field in ["title", "description", "category", "tags", "folder_id"]:
            if field in data.model_fields_set:
                setattr(document, field, getattr(data, field))
        await document.save()
        return await document_to_dict(document)

    async def delete(self, document_id: int) -> None:
        document = await SkillKnowDocument.filter(id=document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        await document.delete()

    async def move(self, target_id: int, folder_id: int | None) -> dict:
        document = await SkillKnowDocument.filter(id=target_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        document.folder_id = folder_id
        await document.save()
        return await document_to_dict(document)

    async def convert_to_skill(self, document_id: int, *, use_llm: bool = True, auto_activate: bool = True, folder_id: int | None = None) -> dict:
        document = await SkillKnowDocument.filter(id=document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")
        if not document.content:
            raise HTTPException(status_code=400, detail="文档内容为空，无法转换")
        analysis = await skill_know_content_analyzer.analyze(document.title, document.content, use_llm=use_llm)
        payload = SkillKnowSkillIn(
            name=document.title,
            description=document.description or analysis["abstract"],
            category=SkillKnowSkillCategory.RETRIEVAL,
            abstract=analysis["abstract"],
            overview=analysis["overview"],
            content=document.content,
            trigger_keywords=analysis.get("keywords") or analysis.get("tags") or [],
            folder_id=folder_id if folder_id is not None else document.folder_id,
        )
        skill_data = await skill_know_skill_service.create(payload, skill_type=SkillKnowSkillType.DOCUMENT, source_document_id=document.id)
        skill = await SkillKnowSkill.get(id=skill_data["id"])
        skill.is_active = auto_activate
        await skill.save()
        document.skill_id = skill.id
        document.is_converted = True
        document.converted_at = datetime.now()
        await document.save()
        if skill.uri and document.uri:
            await skill_know_graph_service.record(
                source_uri=skill.uri,
                target_uri=document.uri,
                relation_type="derived_from",
                reason=f"Skill '{skill.name}' converted from document '{document.filename}'",
                weight=1.0,
                metadata={"document_id": document.id, "skill_id": skill.id},
            )
        return {"success": True, "skill": await skill_know_skill_service.get(skill.id), "document": await document_to_dict(document)}

    async def search(self, query: str, *, limit: int = 20) -> list[dict]:
        rows = await SkillKnowDocument.filter(Q(title__contains=query) | Q(description__contains=query) | Q(content__contains=query)).limit(limit)
        return [await document_to_dict(item) for item in rows]


skill_know_document_service = SkillKnowDocumentService()
