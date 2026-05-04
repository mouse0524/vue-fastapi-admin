from __future__ import annotations

from app.models.admin import SkillKnowSkill
from app.services.skill_know.graph_service import skill_know_graph_service


class SkillKnowKnowledgeDeduplicator:
    async def merge_if_similar(self, skill: SkillKnowSkill, threshold: float = 0.88) -> dict:
        candidates = await SkillKnowSkill.filter(is_active=True).exclude(id=skill.id).limit(100)
        best = None
        best_score = 0.0
        source = (skill.abstract or skill.description or skill.content[:300]).strip().lower()
        source_tokens = set(source.split())
        if not source_tokens:
            return {"merged": False}
        for item in candidates:
            target = (item.abstract or item.description or item.content[:300]).strip().lower()
            target_tokens = set(target.split())
            if not target_tokens:
                continue
            inter = len(source_tokens & target_tokens)
            union = len(source_tokens | target_tokens)
            score = inter / union if union else 0.0
            if score > best_score:
                best_score, best = score, item
        if not best or best_score < threshold:
            return {"merged": False, "score": round(best_score, 4)}
        if skill.uri and best.uri:
            await skill_know_graph_service.record(
                source_uri=best.uri,
                target_uri=skill.uri,
                relation_type="merged_from",
                reason=f"auto-merge similarity={best_score:.4f}",
                weight=best_score,
            )
        skill.is_active = False
        await skill.save()
        return {"merged": True, "score": round(best_score, 4), "target_skill_id": best.id}


skill_know_knowledge_deduplicator = SkillKnowKnowledgeDeduplicator()
