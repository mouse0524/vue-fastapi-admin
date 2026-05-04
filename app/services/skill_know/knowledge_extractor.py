from __future__ import annotations

import re

from app.models.admin import SkillKnowDocument
from app.models.enums import SkillKnowDocumentStatus
from app.services.skill_know.content_analyzer import skill_know_content_analyzer
from app.services.skill_know.utils import make_uri, new_uuid, preview_text, sha256_text


class SkillKnowKnowledgeExtractor:
    async def extract_from_dialogue(self, user_text: str, assistant_text: str, conversation_id: int) -> list[dict]:
        text = f"Q: {user_text}\nA: {assistant_text}".strip()
        if len(assistant_text.strip()) < 40:
            return []
        title = preview_text(user_text, 60) or f"conversation-{conversation_id}"
        analysis = await skill_know_content_analyzer.analyze(title, text, use_llm=False)
        doc = await SkillKnowDocument.create(
            uuid=new_uuid(),
            uri=make_uri("knowledge", f"conv-{conversation_id}-{sha256_text(text)[:10]}"),
            title=f"会话知识: {title}",
            description="从对话中自动抽取",
            filename=f"conversation_{conversation_id}.md",
            file_path="inline://conversation",
            file_size=len(text.encode("utf-8")),
            file_type="md",
            abstract=analysis.get("abstract"),
            overview=analysis.get("overview"),
            content=text,
            content_hash=sha256_text(text),
            status=SkillKnowDocumentStatus.COMPLETED,
            category=analysis.get("category") or "conversation",
            tags=list({*analysis.get("tags", []), "conversation", "auto-extract"}),
            extra_metadata={"source": "chat", "conversation_id": conversation_id},
        )
        return [await doc.to_dict()]


skill_know_knowledge_extractor = SkillKnowKnowledgeExtractor()
