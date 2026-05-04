from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator

import httpx

from app.log import logger
from app.models.admin import SkillKnowConversation, SkillKnowMessage, SkillKnowPrompt
from app.models.enums import SkillKnowMessageRole
from app.services.skill_know.knowledge_extractor import skill_know_knowledge_extractor
from app.services.skill_know.openai_client import skill_know_openai_client
from app.services.skill_know.prompt_service import skill_know_prompt_service
from app.services.skill_know.retriever import skill_know_retriever
from app.services.skill_know.session_compressor import skill_know_session_compressor
from app.services.skill_know.support_matcher import skill_know_support_matcher
from app.services.skill_know.utils import new_uuid


def event(event_type: str, payload: dict | None = None) -> dict:
    return {"type": event_type, "payload": payload or {}, "ts": int(time.time() * 1000)}


def _status_hint(status_code: int | str) -> str:
    try:
        code = int(status_code)
    except Exception:
        return "请检查网络与模型服务状态。"
    if code == 401:
        return "认证失败：请检查 API Key 是否正确且仍有效。"
    if code == 403:
        return "权限不足：请检查 Key 权限、模型访问范围或账号策略。"
    if code == 404:
        return "资源不存在：请检查 Base URL 与模型名是否正确。"
    if code == 429:
        return "请求过多：请稍后重试，或检查配额/速率限制。"
    if 500 <= code < 600:
        return "模型服务端异常：请稍后重试。"
    return "请检查请求参数、模型配置与网络连通性。"


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

        support_match = await skill_know_support_matcher.match(message, limit=5)
        support_event = event("support.match", {
            "classification": support_match["classification"],
            "confidence": support_match["confidence"],
            "clarifying_questions": support_match["clarifying_questions"],
            "items": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "score": item["score"],
                    "matched_reasons": item.get("matched_reasons") or [],
                    "solution_levels": item.get("solution_levels") or [],
                }
                for item in support_match["matches"][:3]
            ],
        })
        timeline.append(support_event)
        yield support_event

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
        support_context = json.dumps(support_event["payload"], ensure_ascii=False)
        messages = [
            {"role": "system", "content": await self._system_prompt()},
            {"role": "system", "content": f"产品问题匹配结果：\n{support_context}"},
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
        except httpx.ConnectError as exc:
            logger.warning("[skill_know.chat.stream] network connect error conv_id={} error={}", conv.id, str(exc))
            if not answer:
                answer = "网络连接失败，请检查网络设置"
                yield event("assistant.delta", {"content": answer})
            err = event("error", {"message": "网络连接失败，请检查网络设置"})
            timeline.append(err)
            yield err
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else "unknown"
            hint = _status_hint(status_code)
            logger.warning(
                "[skill_know.chat.stream] provider http status error conv_id={} status={} error={}",
                conv.id,
                status_code,
                str(exc),
            )
            if not answer:
                answer = f"API错误: {status_code}。{hint}"
                yield event("assistant.delta", {"content": answer})
            err = event("error", {"message": f"API错误: {status_code}", "hint": hint, "status_code": status_code})
            timeline.append(err)
            yield err
        except httpx.ReadTimeout as exc:
            logger.warning("[skill_know.chat.stream] provider read timeout conv_id={} error={}", conv.id, str(exc))
            if not answer:
                answer = "响应超时，请稍后重试"
                yield event("assistant.delta", {"content": answer})
            err = event("error", {"message": "响应超时，请稍后重试"})
            timeline.append(err)
            yield err
        except Exception as exc:
            logger.exception("[skill_know.chat.stream] unexpected error conv_id={} error={}", conv.id, str(exc))
            if not answer:
                answer = "服务暂时不可用，请稍后重试"
                yield event("assistant.delta", {"content": answer})
            err = event("error", {"message": "服务暂时不可用，请稍后重试"})
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
