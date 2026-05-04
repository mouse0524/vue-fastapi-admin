from __future__ import annotations

from app.models.admin import SkillKnowConversation, SkillKnowMessage
from app.models.enums import SkillKnowMessageRole
from app.services.skill_know.openai_client import skill_know_openai_client
from app.services.skill_know.utils import new_uuid


class SkillKnowSessionCompressor:
    async def compress(self, conversation_id: int, *, keep_recent: int = 20) -> dict:
        messages = await SkillKnowMessage.filter(conversation_id=conversation_id, is_archived=False).order_by("id")
        if len(messages) <= keep_recent:
            return {"compressed": False, "reason": "messages_not_enough"}
        to_archive = messages[:-keep_recent]
        content = "\n".join([f"{m.role}: {m.content[:800]}" for m in to_archive])
        summary = await self._summarize(content)
        for msg in to_archive:
            msg.is_archived = True
            await msg.save()
        conv = await SkillKnowConversation.get(id=conversation_id)
        meta = conv.extra_metadata or {}
        stats = meta.get("stats") or {}
        stats["compression_count"] = int(stats.get("compression_count") or 0) + 1
        meta["stats"] = stats
        meta["summary"] = summary
        conv.extra_metadata = meta
        await conv.save()
        await SkillKnowMessage.create(
            conversation_id=conversation_id,
            uuid=new_uuid(),
            role=SkillKnowMessageRole.SYSTEM,
            content=f"[会话摘要]\n{summary}",
            is_archived=False,
            timeline=[],
            extra_metadata={"type": "summary"},
        )
        return {"compressed": True, "archived": len(to_archive), "summary": summary}

    async def _summarize(self, text: str) -> str:
        try:
            resp = await skill_know_openai_client.chat([
                {"role": "system", "content": "请把对话总结成不超过300字的要点。"},
                {"role": "user", "content": text[:12000]},
            ])
            return resp.get("choices", [{}])[0].get("message", {}).get("content", "") or text[:300]
        except Exception:
            return text[:300]


skill_know_session_compressor = SkillKnowSessionCompressor()
