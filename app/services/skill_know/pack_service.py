from __future__ import annotations

from app.models.admin import SkillKnowContextRelation, SkillKnowSkill, SkillKnowVectorIndex
from app.models.enums import SkillKnowSkillType
from app.schemas.skill_know import SkillKnowSkillIn
from app.services.skill_know.graph_service import skill_know_graph_service
from app.services.skill_know.skill_service import skill_know_skill_service


class SkillKnowPackService:
    async def export_skills(self, *, category: str | None = None, folder_id: int | None = None) -> dict:
        query = SkillKnowSkill.filter(is_active=True)
        if category:
            query = query.filter(category=category)
        if folder_id is not None:
            query = query.filter(folder_id=folder_id)
        skills = await query.order_by("priority", "id")
        uris = [item.uri for item in skills if item.uri]
        vectors = await SkillKnowVectorIndex.filter(uri__in=uris).order_by("uri", "level") if uris else []
        relations = await SkillKnowContextRelation.filter(source_uri__in=uris) if uris else []
        return {
            "version": "1.0",
            "type": "skill_know_pack",
            "skills": [await item.to_dict() for item in skills],
            "vectors": [await item.to_dict() for item in vectors],
            "relations": [await item.to_dict() for item in relations],
            "stats": {"skill_count": len(skills), "vector_count": len(vectors), "relation_count": len(relations)},
        }

    async def import_skills(self, pack_data: dict, *, skip_duplicates: bool = True) -> dict:
        imported = 0
        skipped = 0
        uri_mapping: dict[str, str] = {}
        for item in pack_data.get("skills") or []:
            old_uri = item.get("uri")
            exists = await SkillKnowSkill.filter(name=item.get("name")).first()
            if exists and skip_duplicates:
                skipped += 1
                if old_uri and exists.uri:
                    uri_mapping[old_uri] = exists.uri
                continue
            payload = SkillKnowSkillIn(
                name=item.get("name") or "未命名Skill",
                description=item.get("description") or "导入Skill",
                category=item.get("category") or "prompt",
                abstract=item.get("abstract"),
                overview=item.get("overview"),
                content=item.get("content") or "",
                trigger_keywords=item.get("trigger_keywords") or [],
                trigger_intents=item.get("trigger_intents") or [],
                always_apply=bool(item.get("always_apply")),
                priority=item.get("priority") or 100,
                config=item.get("config") or {},
            )
            created = await skill_know_skill_service.create(payload, skill_type=SkillKnowSkillType.USER)
            imported += 1
            if old_uri and created.get("uri"):
                uri_mapping[old_uri] = created["uri"]
        relation_count = 0
        for item in pack_data.get("relations") or []:
            source = uri_mapping.get(item.get("source_uri"), item.get("source_uri"))
            target = uri_mapping.get(item.get("target_uri"), item.get("target_uri"))
            if not source or not target:
                continue
            await skill_know_graph_service.record(
                source_uri=source,
                target_uri=target,
                relation_type=item.get("relation_type") or "related_to",
                reason=item.get("reason") or "imported",
                weight=float(item.get("weight") or 1),
                metadata=item.get("extra_metadata") or {},
            )
            relation_count += 1
        return {"success": True, "imported": imported, "skipped": skipped, "relations_imported": relation_count}


skill_know_pack_service = SkillKnowPackService()
