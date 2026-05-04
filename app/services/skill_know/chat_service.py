from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator

from app.models.admin import SkillKnowConversation, SkillKnowMessage, SkillKnowPrompt
from app.models.enums import SkillKnowMessageRole
from app.services.skill_know.knowledge_extractor import skill_know_knowledge_extractor
from app.services.skill_know.openai_client import skill_know_openai_client
from app.services.skill_know.prompt_service import skill_know_prompt_service
from app.services.skill_know.retriever import skill_know_retriever
from app.services.skill_know.session_compressor import skill_know_session_compressor
from app.services.skill_know.utils import new_uuid


def event(event_type: str, payload: dict | None = None) -> dict:
    return {"type": event_type, "payload": payload or {}, "ts": int(time.time() * 1000)}


class SkillKnowChatService:
    async def _conversation(self, conversation_id: int | None, message: str) -> SkillKnowConversation:
        if conversation_id:
            item = await SkillKnowConversation.filter(id=conversation_id).first()
            if item:
                return item
        return await SkillKnowConversation.create(uuid=new_uuid(), title=message[:60])

    async def _system_prompt(self) -> str:
        await skill_know_prompt_service.initialize_defaults()
        prompt = await SkillKnowPrompt.filter(key="system.chat", is_active=True).first()
        return prompt.content if prompt else "你是 Skill-Know 知识库助手。"

    async def chat(self, message: str, conversation_id: int | None = None) -> dict:
        content = ""
        async for item in self.stream(message, conversation_id=conversation_id):
            if item["type"] == "assistant.delta":
                content += item["payload"].get("content", "")
            if item["type"] == "final":
                return item["payload"]
        return {"content": content}

    async def stream(self, message: str, conversation_id: int | None = None) -> AsyncGenerator[dict, None]:
        start = time.perf_counter()
        timeline: list[dict] = []
        conv = await self._conversation(conversation_id, message)
        user_event = event("user.message", {"content": message, "conversation_id": conv.id})
        timeline.append(user_event)
        yield user_event

        await SkillKnowMessage.create(uuid=new_uuid(), conversation_id=conv.id, role=SkillKnowMessageRole.USER, content=message)

        phase = event("phase.changed", {"phase": "retrieving", "label": "检索相关 Skill"})
        timeline.append(phase)
        yield phase

        skills = await skill_know_retriever.retrieve(message, limit=6)
        search_event = event("search.results", {"query": message, "items": skills, "total": len(skills)})
        timeline.append(search_event)
        yield search_event

        for skill in skills[:3]:
            activated = event("skill.activated", {"id": skill["id"], "name": skill["name"], "score": skill.get("score")})
            timeline.append(activated)
            yield activated

        tools_event = event("tools.registered", {"tools": ["search_skills", "get_skill_content", "extract_keywords"]})
        timeline.append(tools_event)
        yield tools_event

        context = "\n\n".join(
            f"### {skill['name']}\n摘要：{skill.get('abstract') or skill.get('description')}\n内容：{skill.get('overview') or skill.get('content', '')[:1200]}"
            for skill in skills[:5]
        )
        messages = [
            {"role": "system", "content": await self._system_prompt()},
            {"role": "system", "content": f"已检索到的知识上下文：\n{context}" if context else "当前没有检索到相关 Skill。"},
            {"role": "user", "content": message},
        ]

        llm_start = event("llm.call.started", {"model": "configured", "stream": True})
        timeline.append(llm_start)
        yield llm_start

        answer = ""
        try:
            async for chunk in skill_know_openai_client.stream_chat(messages):
                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content") or ""
                if not delta:
                    continue
                answer += delta
                item = event("assistant.delta", {"content": delta})
                yield item
            done = event("llm.call.completed", {"length": len(answer)})
            timeline.append(done)
            yield done
        except Exception as exc:
            if not answer:
                answer = "模型暂不可用。请先在快速设置中检查 OpenAI 配置，或稍后重试。"
                yield event("assistant.delta", {"content": answer})
            err = event("error", {"message": str(exc)})
            timeline.append(err)
            yield err

        latency_ms = int((time.perf_counter() - start) * 1000)
        msg = await SkillKnowMessage.create(
            uuid=new_uuid(),
            conversation_id=conv.id,
            role=SkillKnowMessageRole.ASSISTANT,
            content=answer,
            timeline=timeline,
            latency_ms=latency_ms,
        )
        final = event("final", {"conversation_id": conv.id, "message_id": msg.id, "content": answer, "latency_ms": latency_ms})
        try:
            await skill_know_knowledge_extractor.extract_from_dialogue(message, answer, conv.id)
            await skill_know_session_compressor.compress(conv.id)
        except Exception:
            pass
        yield final

    async def list_conversations(self, page: int, page_size: int) -> tuple[int, list[dict]]:
        query = SkillKnowConversation.all()
        total = await query.count()
        rows = await query.order_by("-id").offset((page - 1) * page_size).limit(page_size)
        return total, [await item.to_dict() for item in rows]

    async def get_conversation(self, conversation_id: int) -> dict:
        conv = await SkillKnowConversation.get(id=conversation_id)
        data = await conv.to_dict()
        messages = await SkillKnowMessage.filter(conversation_id=conversation_id).order_by("id")
        data["messages"] = [await item.to_dict() for item in messages]
        return data

    async def delete_conversation(self, conversation_id: int) -> None:
        await SkillKnowMessage.filter(conversation_id=conversation_id).delete()
        await SkillKnowConversation.filter(id=conversation_id).delete()

    async def messages(self, conversation_id: int) -> list[dict]:
        rows = await SkillKnowMessage.filter(conversation_id=conversation_id).order_by("id")
        return [await item.to_dict() for item in rows]

    async def stats(self, conversation_id: int) -> dict:
        messages = await SkillKnowMessage.filter(conversation_id=conversation_id)
        skills_used = []
        for msg in messages:
            for item in msg.timeline or []:
                if item.get("type") == "skill.activated":
                    payload = item.get("payload") or {}
                    if payload.get("name") and payload.get("name") not in skills_used:
                        skills_used.append(payload.get("name"))
        return {"conversation_id": conversation_id, "stats": {"total_turns": len(messages), "compression_count": 0, "skills_used": skills_used}, "has_summary": False}


def sse_encode(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"


skill_know_chat_service = SkillKnowChatService()
