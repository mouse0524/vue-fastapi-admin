from __future__ import annotations

import re
from typing import Any

from app.models.admin import SkillKnowSkill
from app.models.enums import SkillKnowSkillCategory
from app.services.skill_know.retriever import skill_know_retriever
from app.services.skill_know.skill_service import skill_know_skill_service
from app.services.skill_know.support_taxonomy import ISSUE_CATEGORIES, skill_know_support_taxonomy
from app.services.skill_know.utils import preview_text, skill_to_dict


SUPPORT_CATEGORIES = {item.value for item in [
    SkillKnowSkillCategory.FAQ,
    SkillKnowSkillCategory.TROUBLESHOOTING,
    SkillKnowSkillCategory.FEATURE_CONSULTING,
    SkillKnowSkillCategory.CONFIGURATION,
    SkillKnowSkillCategory.INTEGRATION,
    SkillKnowSkillCategory.KNOWN_ISSUE,
    SkillKnowSkillCategory.UPGRADE_GUIDE,
]}


class SkillKnowSupportMatcher:
    def normalize_query(self, query: str) -> str:
        return re.sub(r"\s+", " ", query.strip().lower())

    async def classify(self, query: str, *, product_type: str | None = None, product_module: str | None = None, issue_category: str | None = None) -> dict:
        normalized = self.normalize_query(query)
        products = await skill_know_support_taxonomy.product_profiles()
        detected_product = product_type
        detected_module = product_module
        product_confidence = 0.0

        if not detected_product:
            for product in products:
                candidates = [product.get("key", ""), product.get("name", ""), *(product.get("modules") or [])]
                hits = [item for item in candidates if item and str(item).lower() in normalized]
                if hits:
                    detected_product = product.get("key")
                    detected_module = detected_module or hits[0]
                    product_confidence = min(1.0, 0.45 + 0.15 * len(hits))
                    break
        else:
            product_confidence = 1.0

        category_scores: dict[str, float] = {}
        for key, meta in ISSUE_CATEGORIES.items():
            keywords = meta.get("keywords") or []
            hits = sum(1 for word in keywords if str(word).lower() in normalized)
            if hits:
                category_scores[key] = min(1.0, 0.35 + hits * 0.2)
        detected_category = issue_category or (max(category_scores, key=category_scores.get) if category_scores else SkillKnowSkillCategory.FAQ.value)
        category_confidence = 1.0 if issue_category else category_scores.get(detected_category, 0.35)
        confidence = round(max(0.2, min(1.0, category_confidence * 0.7 + product_confidence * 0.3)), 4)
        return {
            "query": query,
            "normalized_query": normalized,
            "product_type": detected_product,
            "product_module": detected_module,
            "issue_category": detected_category,
            "confidence": confidence,
        }

    def _support(self, skill: dict) -> dict[str, Any]:
        config = skill.get("config") or {}
        support = config.get("support") if isinstance(config, dict) else None
        return support if isinstance(support, dict) else {}

    def _tokens(self, values: list[str] | tuple[str, ...] | str | None) -> list[str]:
        if not values:
            return []
        if isinstance(values, str):
            values = [values]
        return [str(item).strip().lower() for item in values if str(item).strip()]

    def _hit_score(self, query: str, values: list[str] | tuple[str, ...] | str | None) -> tuple[float, list[str]]:
        tokens = self._tokens(values)
        hits = [item for item in tokens if item and item in query]
        if not tokens:
            return 0.0, []
        return min(1.0, len(hits) / min(len(tokens), 5)), hits

    def evaluate_skill(self, skill: dict) -> dict:
        support = self._support(skill)
        checks = {
            "has_product": bool(support.get("product_type") or support.get("product_module")),
            "has_issue_category": bool(support.get("issue_category") or skill.get("category") in SUPPORT_CATEGORIES),
            "has_triggers": bool(skill.get("trigger_keywords") or skill.get("trigger_intents") or support.get("symptoms")),
            "has_solution_levels": bool(support.get("solution_levels")),
            "has_root_causes": bool(support.get("root_causes")),
            "has_actionable_content": len(str(skill.get("content") or "")) >= 30,
        }
        score = round(sum(1 for value in checks.values() if value) / len(checks), 4)
        missing = [key for key, value in checks.items() if not value]
        return {"score": score, "checks": checks, "missing": missing}

    def _solution_levels(self, skill: dict) -> list[dict]:
        support = self._support(skill)
        configured = support.get("solution_levels")
        if isinstance(configured, list) and configured:
            return configured
        content = preview_text(skill.get("content"), 900)
        return [
            {"level": 1, "title": "快速解决", "steps": [skill.get("abstract") or skill.get("description") or "先确认问题现象与适用模块。"]},
            {"level": 2, "title": "深入排查", "steps": [skill.get("overview") or content or "检查配置、日志、网络和权限状态。"]},
            {"level": 3, "title": "升级处理", "steps": ["如仍未解决，请补充错误截图、操作步骤、环境版本和相关日志后升级技术处理。"]},
        ]

    def _priority_score(self, priority: int | None) -> float:
        value = priority if isinstance(priority, int) else 100
        return max(0.0, min(1.0, (200 - value) / 200))

    async def match(self, query: str, *, product_type: str | None = None, product_module: str | None = None, issue_category: str | None = None, limit: int = 5) -> dict:
        classification = await self.classify(query, product_type=product_type, product_module=product_module, issue_category=issue_category)
        normalized = classification["normalized_query"]
        weights = await skill_know_support_taxonomy.match_weights()

        candidates: dict[int, dict] = {}
        for item in await skill_know_retriever.retrieve(query, limit=max(limit * 3, 8)):
            candidates[item["id"]] = item
        for item in await skill_know_skill_service.text_search(query, limit=max(limit * 3, 8)):
            candidates.setdefault(item["id"], {**item, "score": 0.45, "matched_by": "text"})

        matches = []
        for skill in candidates.values():
            support = self._support(skill)
            keyword_score, keyword_hits = self._hit_score(
                normalized,
                [*(skill.get("trigger_keywords") or []), *(support.get("symptoms") or []), *(support.get("root_causes") or [])],
            )
            intent_score, intent_hits = self._hit_score(normalized, skill.get("trigger_intents") or ISSUE_CATEGORIES.get(str(skill.get("category")), {}).get("keywords") or [])
            product_values = [support.get("product_type"), support.get("product_module"), skill.get("name"), skill.get("description")]
            requested_product = [classification.get("product_type"), classification.get("product_module")]
            product_score = 0.0
            product_hits = []
            for value in requested_product:
                if value:
                    product_score, product_hits = self._hit_score(" ".join(self._tokens(product_values)), value)
                    if product_score:
                        break
            if support.get("issue_category") == classification.get("issue_category") or skill.get("category") == classification.get("issue_category"):
                intent_score = max(intent_score, 1.0)
                intent_hits.append(str(classification.get("issue_category")))
            quality = self.evaluate_skill(skill)
            support_quality = support.get("quality_score")
            quality_score = max(quality["score"], float(support_quality or 0.0))
            semantic_score = float(skill.get("score") or 0.0)
            final_score = (
                semantic_score * weights["semantic"]
                + keyword_score * weights["keyword"]
                + intent_score * weights["intent"]
                + product_score * weights["product"]
                + quality_score * weights["quality"]
                + self._priority_score(skill.get("priority")) * weights["priority"]
            )
            reasons = []
            if semantic_score:
                reasons.append(f"语义召回 {semantic_score:.2f}")
            if keyword_hits:
                reasons.append("关键词命中：" + "、".join(keyword_hits[:5]))
            if intent_hits:
                reasons.append("意图/分类命中：" + "、".join(dict.fromkeys(intent_hits[:5])))
            if product_hits:
                reasons.append("产品模块匹配：" + "、".join(product_hits[:3]))
            matches.append({
                **skill,
                "score": round(final_score, 4),
                "score_breakdown": {
                    "semantic": round(semantic_score, 4),
                    "keyword": round(keyword_score, 4),
                    "intent": round(intent_score, 4),
                    "product": round(product_score, 4),
                    "quality": round(quality_score, 4),
                    "priority": round(self._priority_score(skill.get("priority")), 4),
                },
                "matched_reasons": reasons,
                "solution_levels": self._solution_levels(skill),
                "quality": quality,
            })

        matches.sort(key=lambda item: (-item["score"], item.get("priority", 100), -item.get("id", 0)))
        matches = matches[:limit]
        top_score = matches[0]["score"] if matches else 0.0
        clarifying_questions = []
        if top_score < 0.55:
            clarifying_questions = ["请补充具体产品模块。", "请提供完整错误信息或截图文字。", "请说明触发问题的操作步骤和环境版本。"]
        return {
            "query": query,
            "classification": {key: value for key, value in classification.items() if key != "normalized_query"},
            "matches": matches,
            "total": len(matches),
            "confidence": round(max(top_score, classification["confidence"] * 0.5), 4),
            "clarifying_questions": clarifying_questions,
        }

    async def evaluate_skill_by_id(self, skill_id: int) -> dict:
        skill = await SkillKnowSkill.get(id=skill_id)
        data = await skill_to_dict(skill)
        return {"skill_id": skill_id, "quality": self.evaluate_skill(data)}


skill_know_support_matcher = SkillKnowSupportMatcher()
