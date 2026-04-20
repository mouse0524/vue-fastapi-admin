import time

import httpx

from app.controllers.system_setting import system_setting_controller
from app.log import logger
from app.settings import settings


class LlmGateway:
    async def _runtime_config(self) -> dict:
        conf = {
            "provider": self._provider(),
            "base_url": settings.LLM_BASE_URL,
            "api_key": settings.LLM_API_KEY,
            "model": self._model(),
            "timeout_seconds": settings.LLM_TIMEOUT_SECONDS,
        }
        try:
            setting = await system_setting_controller.get_or_create()
            data = await setting.to_dict()
            conf["provider"] = (data.get("llm_provider") or conf["provider"] or "mock").strip().lower()
            conf["base_url"] = data.get("llm_base_url") or conf["base_url"]
            conf["api_key"] = data.get("llm_api_key") or conf["api_key"]
            conf["model"] = data.get("llm_model") or conf["model"]
            timeout = data.get("llm_timeout_seconds")
            if isinstance(timeout, int) and timeout > 0:
                conf["timeout_seconds"] = timeout
        except Exception as exc:
            logger.warning("[llm.gateway] load runtime config failed error={}", str(exc))
        return conf

    @staticmethod
    def _provider() -> str:
        return (settings.LLM_PROVIDER or "mock").strip().lower()

    @staticmethod
    def _model(default: str = "mock-rag-v1") -> str:
        return (settings.KB_DEFAULT_MODEL or default).strip() or default

    async def _chat_openai_compat(self, *, question: str, contexts: list[str], model: str, conf: dict) -> dict:
        if not conf.get("base_url") or not conf.get("api_key"):
            logger.warning("[llm.gateway] openai_compat missing base_url or api_key, fallback to mock")
            return await self._chat_mock(question=question, contexts=contexts, model=model)

        prompt_context = "\n".join([f"- {item}" for item in contexts[:5] if item])
        system_prompt = "你是企业知识库助手。请严格基于提供的知识片段作答，若证据不足明确说明。"
        user_prompt = f"问题：{question}\n\n知识片段：\n{prompt_context if prompt_context else '(无)'}"
        start = time.perf_counter()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 800,
        }
        headers = {
            "Authorization": f"Bearer {conf.get('api_key')}",
            "Content-Type": "application/json",
        }
        url = f"{str(conf.get('base_url')).rstrip('/')}/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=float(conf.get("timeout_seconds") or settings.LLM_TIMEOUT_SECONDS)) as client:
                resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = (
                ((data.get("choices") or [{}])[0].get("message") or {}).get("content")
                or "模型未返回有效内容"
            )
            usage = data.get("usage") or {}
            latency_ms = int((time.perf_counter() - start) * 1000)
            return {
                "content": content,
                "model": model,
                "provider": "openai_compat",
                "usage": {
                    "prompt_tokens": int(usage.get("prompt_tokens") or 0),
                    "completion_tokens": int(usage.get("completion_tokens") or 0),
                },
                "latency_ms": latency_ms,
                "request_payload": {
                    "messages": len(payload["messages"]),
                    "temperature": payload["temperature"],
                    "max_tokens": payload["max_tokens"],
                },
                "response_payload": {
                    "id": data.get("id"),
                    "model": data.get("model"),
                },
                "error_code": None,
            }
        except httpx.TimeoutException:
            return {
                "content": "模型请求超时，请稍后重试。",
                "model": model,
                "provider": "openai_compat",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "request_payload": {"messages": len(payload["messages"])},
                "response_payload": None,
                "error_code": "timeout",
            }
        except Exception as exc:
            logger.warning("[llm.gateway] openai_compat error={}", str(exc))
            return {
                "content": "模型服务暂不可用，已返回降级回答。",
                "model": model,
                "provider": "openai_compat",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                "latency_ms": int((time.perf_counter() - start) * 1000),
                "request_payload": {"messages": len(payload["messages"])},
                "response_payload": None,
                "error_code": "provider_error",
            }

    async def _chat_mock(self, *, question: str, contexts: list[str], model: str) -> dict:
        start = time.perf_counter()
        context_text = "\n".join([f"- {item}" for item in contexts[:3] if item])
        if context_text:
            answer = f"基于知识库检索结果，问题“{question}”的相关信息如下：\n{context_text}"
        else:
            answer = f"当前知识库中未检索到与“{question}”高度相关的内容，请补充更具体的问题。"

        latency_ms = int((time.perf_counter() - start) * 1000)
        return {
            "content": answer,
            "model": model,
            "provider": "mock",
            "usage": {
                "prompt_tokens": max(1, len(question) // 2 + sum(len(c) for c in contexts) // 4),
                "completion_tokens": max(1, len(answer) // 2),
            },
            "latency_ms": latency_ms,
            "request_payload": {"contexts": len(contexts)},
            "response_payload": {"mode": "mock"},
            "error_code": None,
        }

    async def chat(
        self,
        *,
        question: str,
        contexts: list[str],
        model: str = "mock-rag-v1",
    ) -> dict:
        conf = await self._runtime_config()
        model_name = model or conf.get("model") or self._model()
        provider = conf.get("provider") or self._provider()
        if provider in {"openai", "openai_compat"}:
            return await self._chat_openai_compat(question=question, contexts=contexts, model=model_name, conf=conf)
        return await self._chat_mock(question=question, contexts=contexts, model=model_name)


llm_gateway = LlmGateway()
