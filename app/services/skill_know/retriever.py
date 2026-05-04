from __future__ import annotations

from app.models.admin import SkillKnowSkill
from app.services.skill_know.graph_service import skill_know_graph_service
from app.services.skill_know.chroma_store import skill_know_chroma_store
from app.services.skill_know.skill_service import skill_know_skill_service
from app.services.skill_know.utils import skill_to_dict


class SkillKnowRetriever:
    async def retrieve(self, query: str, *, limit: int = 8) -> list[dict]:
        results = await skill_know_chroma_store.search(query, level=0, limit=limit * 2)
        by_id: dict[int, dict] = {}
        for item in results:
            skill_id = item.get("metadata", {}).get("skill_id")
            if not skill_id:
                continue
            current = by_id.get(int(skill_id))
            if not current or item["score"] > current["score"]:
                by_id[int(skill_id)] = item
        if not by_id:
            fallback = await skill_know_skill_service.text_search(query, limit=limit)
            return [{**item, "score": 0.5, "matched_by": "text"} for item in fallback]
        skills = await SkillKnowSkill.filter(id__in=list(by_id.keys()), is_active=True)
        enriched = []
        relations_map = await skill_know_graph_service.first_hop([skill.uri for skill in skills if skill.uri])
        for skill in skills:
            data = await skill_to_dict(skill)
            match = by_id.get(skill.id) or {}
            data["score"] = round(float(match.get("score") or 0), 4)
            data["matched_by"] = match.get("matched_by") or "L0"
            data["relations"] = relations_map.get(skill.uri or "", [])
            enriched.append(data)
        enriched.sort(key=lambda x: (-x.get("score", 0), x.get("priority", 100), -x.get("id", 0)))
        return enriched[:limit]


skill_know_retriever = SkillKnowRetriever()
