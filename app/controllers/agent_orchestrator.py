from app.controllers.llm_gateway import llm_gateway
from app.models.kb import KbChunk


class AgentOrchestrator:
    async def ask(self, *, space_id: int, question: str) -> dict:
        chunks = await KbChunk.filter(space_id=space_id).order_by("-id").limit(5)
        contexts = [item.content for item in chunks]
        cited = []
        for item in chunks[:3]:
            cited.append(
                {
                    "document_id": item.document_id,
                    "chunk_id": item.id,
                    "score": 1.0,
                    "snippet": (item.content or "")[:200],
                }
            )

        llm_result = await llm_gateway.chat(question=question, contexts=contexts)
        return {
            "answer": llm_result["content"],
            "model": llm_result["model"],
            "provider": llm_result.get("provider") or "mock",
            "prompt_tokens": llm_result["usage"]["prompt_tokens"],
            "completion_tokens": llm_result["usage"]["completion_tokens"],
            "latency_ms": llm_result["latency_ms"],
            "request_payload": llm_result.get("request_payload"),
            "response_payload": llm_result.get("response_payload"),
            "error_code": llm_result.get("error_code"),
            "citations": cited,
        }


agent_orchestrator = AgentOrchestrator()
