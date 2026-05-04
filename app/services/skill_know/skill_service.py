from __future__ import annotations

from fastapi import HTTPException
from tortoise.expressions import Q

from app.models.admin import SkillKnowSkill
from app.models.enums import SkillKnowSkillType
from app.services.skill_know.chroma_store import skill_know_chroma_store
from app.services.skill_know.content_analyzer import skill_know_content_analyzer
from app.services.skill_know.graph_service import skill_know_graph_service
from app.services.skill_know.knowledge_deduplicator import skill_know_knowledge_deduplicator
from app.services.skill_know.utils import make_uri, new_uuid, skill_to_dict


class SkillKnowSkillService:
    def _merge_support_config(self, data) -> dict:
        config = dict(data.config or {})
        support = getattr(data, "support", None)
        if support is not None:
            config["support"] = support.model_dump(exclude_none=True)
        return config

    async def create(self, data, *, skill_type: SkillKnowSkillType = SkillKnowSkillType.USER, source_document_id: int | None = None) -> dict:
        analysis = await skill_know_content_analyzer.analyze(data.name, data.content, use_llm=False)
        abstract = data.abstract or analysis["abstract"]
        overview = data.overview or analysis["overview"]
        config = self._merge_support_config(data)
        skill = await SkillKnowSkill.create(
            uuid=new_uuid(),
            uri=make_uri("skills", data.name),
            name=data.name,
            description=data.description,
            type=skill_type,
            category=data.category,
            abstract=abstract,
            overview=overview,
            content=data.content,
            trigger_keywords=data.trigger_keywords,
            trigger_intents=data.trigger_intents,
            always_apply=data.always_apply,
            folder_id=data.folder_id,
            priority=data.priority,
            config=config,
            source_document_id=source_document_id,
        )
        await self.index(skill)
        await skill_know_knowledge_deduplicator.merge_if_similar(skill)
        return await skill_to_dict(skill)

    async def index(self, skill: SkillKnowSkill) -> None:
        if not skill.uri:
            return
        metadata = {
            "skill_id": skill.id,
            "uri": skill.uri,
            "name": skill.name,
            "category": str(skill.category),
            "type": str(skill.type),
            "folder_id": skill.folder_id,
        }
        await skill_know_chroma_store.upsert(uri=skill.uri, level=0, text=skill.abstract or skill.description, metadata=metadata)
        await skill_know_chroma_store.upsert(uri=skill.uri, level=1, text=skill.overview or skill.content[:2000], metadata=metadata)

    async def list(self, *, page: int, page_size: int, skill_type=None, category=None, folder_id=None, is_active=True) -> tuple[int, list[dict]]:
        q = Q()
        if skill_type:
            q &= Q(type=skill_type)
        if category:
            q &= Q(category=category)
        if folder_id is not None:
            q &= Q(folder_id=folder_id)
        if is_active is not None:
            q &= Q(is_active=is_active)
        query = SkillKnowSkill.filter(q)
        total = await query.count()
        rows = await query.order_by("priority", "-id").offset((page - 1) * page_size).limit(page_size)
        return total, [await skill_to_dict(item) for item in rows]

    async def get(self, skill_id: int) -> dict:
        skill = await SkillKnowSkill.filter(id=skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="技能不存在")
        return await skill_to_dict(skill)

    async def update(self, data) -> dict:
        skill = await SkillKnowSkill.filter(id=data.skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="技能不存在")
        if skill.type == SkillKnowSkillType.SYSTEM:
            raise HTTPException(status_code=400, detail="系统技能不可编辑")
        for field in [
            "name", "description", "category", "abstract", "overview", "content", "trigger_keywords",
            "trigger_intents", "always_apply", "folder_id", "priority", "is_active", "config",
        ]:
            if field in data.model_fields_set:
                setattr(skill, field, getattr(data, field))
        if "support" in data.model_fields_set and data.support is not None:
            config = dict(skill.config or {})
            config["support"] = data.support.model_dump(exclude_none=True)
            skill.config = config
        await skill.save()
        await self.index(skill)
        return await skill_to_dict(skill)

    async def delete(self, skill_id: int) -> None:
        skill = await SkillKnowSkill.filter(id=skill_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="技能不存在")
        if skill.type == SkillKnowSkillType.SYSTEM:
            raise HTTPException(status_code=400, detail="系统技能不可删除")
        if skill.uri:
            await skill_know_chroma_store.delete(skill.uri)
            await skill_know_graph_service.cleanup_uri(skill.uri)
        await skill.delete()

    async def move(self, target_id: int, folder_id: int | None) -> dict:
        skill = await SkillKnowSkill.filter(id=target_id).first()
        if not skill:
            raise HTTPException(status_code=404, detail="技能不存在")
        if skill.type == SkillKnowSkillType.SYSTEM:
            raise HTTPException(status_code=400, detail="系统技能不可迁移")
        skill.folder_id = folder_id
        await skill.save()
        return await skill_to_dict(skill)

    async def text_search(self, query: str, *, limit: int = 20, category=None, skill_type=None) -> list[dict]:
        q = Q(is_active=True) & (Q(name__contains=query) | Q(description__contains=query) | Q(content__contains=query) | Q(abstract__contains=query) | Q(overview__contains=query))
        if category:
            q &= Q(category=category)
        if skill_type:
            q &= Q(type=skill_type)
        rows = await SkillKnowSkill.filter(q).order_by("priority", "-id").limit(limit)
        return [await skill_to_dict(item) for item in rows]


skill_know_skill_service = SkillKnowSkillService()
