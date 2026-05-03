import json
import math
import os
import re
from datetime import datetime
from typing import Any

import httpx
from docx import Document
from pypdf import PdfReader

from app.ai_kb_skill import FAQ_ANSWER_PROMPT, PRODUCT_DETAIL_PROMPT, SOLUTION_RECOMMEND_PROMPT, SYSTEM_PROMPT
from app.controllers.system_setting import system_setting_controller
from app.log import logger
from app.settings import settings


class AIKnowledgeController:
    def __init__(self) -> None:
        self.base_dir = os.path.join(settings.UPLOAD_DIR, "ai_kb")
        self.docs_dir = os.path.join(self.base_dir, "docs")
        self.feedback_path = os.path.join(self.base_dir, "feedback.jsonl")
        self.evolution_log_path = os.path.join(self.base_dir, "evolution.log")
        self.index_path = os.path.join(self.base_dir, "index.json")
        self.meta_path = os.path.join(self.base_dir, "index_meta.json")
        self.rebuild_log_path = os.path.join(self.base_dir, "rebuild.log")
        os.makedirs(self.docs_dir, exist_ok=True)

    def _load_skill_prompts(self) -> dict[str, str]:
        return {
            "system": SYSTEM_PROMPT,
            "product_detail": PRODUCT_DETAIL_PROMPT,
            "solution": SOLUTION_RECOMMEND_PROMPT,
            "faq": FAQ_ANSWER_PROMPT,
        }

    @staticmethod
    def _classify_intent(question: str) -> str:
        q = (question or "").lower()
        if any(k in q for k in ["方案", "场景", "行业", "推荐", "架构"]):
            return "solution"
        if any(k in q for k in ["怎么", "如何", "步骤", "报错", "常见", "faq"]):
            return "faq"
        return "product_detail"

    async def _runtime_conf(self) -> dict[str, Any]:
        conf = await system_setting_controller.get_full_dict()
        return {
            "enabled": bool(conf.get("ai_kb_enabled", True)),
            "top_k": int(conf.get("ai_kb_top_k") or settings.AI_KB_TOP_K),
            "chunk_size": int(conf.get("ai_kb_chunk_size") or settings.AI_KB_CHUNK_SIZE),
            "chunk_overlap": int(conf.get("ai_kb_chunk_overlap") or settings.AI_KB_CHUNK_OVERLAP),
            "feedback_window": int(conf.get("ai_kb_feedback_window") or 20),
            "auto_reindex_threshold": int(conf.get("ai_kb_auto_reindex_threshold") or 5),
            "openai_base_url": str(conf.get("ai_kb_openai_base_url") or settings.LLM_BASE_URL),
            "openai_api_key": str(conf.get("ai_kb_openai_api_key") or settings.LLM_API_KEY),
            "openai_model": str(conf.get("ai_kb_openai_model") or settings.LLM_MODEL),
            "embedding_model": str(conf.get("ai_kb_embedding_model") or os.getenv("AI_KB_EMBEDDING_MODEL", "text-embedding-3-small")),
            "llm_timeout_seconds": int(conf.get("ai_kb_llm_timeout_seconds") or settings.LLM_TIMEOUT_SECONDS),
        }

    @staticmethod
    def _tokenize(text: str) -> set[str]:
        items = re.findall(r"[A-Za-z0-9\u4e00-\u9fff_]+", (text or "").lower())
        return {i for i in items if len(i) > 1}

    def _load_index(self) -> list[dict[str, Any]]:
        if not os.path.exists(self.index_path):
            return []
        try:
            with open(self.index_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            logger.warning("[ai_kb.index] load_failed error={}", str(exc))
            return []

    def _save_index(self, rows: list[dict[str, Any]]) -> None:
        os.makedirs(self.base_dir, exist_ok=True)
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, ensure_ascii=False)

    def _load_meta(self) -> dict[str, Any]:
        if not os.path.exists(self.meta_path):
            return {"files": {}}
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return {"files": {}}
            if not isinstance(data.get("files"), dict):
                data["files"] = {}
            return data
        except Exception:
            return {"files": {}}

    def _save_meta(self, meta: dict[str, Any]) -> None:
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)

    @staticmethod
    def _cosine_similarity(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = 0.0
        na = 0.0
        nb = 0.0
        for x, y in zip(a, b):
            dot += x * y
            na += x * x
            nb += y * y
        if na <= 0.0 or nb <= 0.0:
            return 0.0
        return dot / (math.sqrt(na) * math.sqrt(nb))

    async def _embed_text(self, text: str) -> list[float]:
        runtime = await self._runtime_conf()
        base_url = str(runtime.get("openai_base_url") or "").rstrip("/")
        api_key = str(runtime.get("openai_api_key") or "").strip()
        if not base_url or not api_key:
            return []
        model = str(runtime.get("embedding_model") or "text-embedding-3-small")
        payload = {"model": model, "input": text}
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = f"{base_url}/embeddings"
        try:
            async with httpx.AsyncClient(timeout=float(runtime.get("llm_timeout_seconds") or settings.LLM_TIMEOUT_SECONDS)) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                logger.warning("[ai_kb.embed] request_failed status={}", resp.status_code)
                return []
            data = resp.json()
            items = data.get("data") or []
            if not items:
                return []
            vec = items[0].get("embedding") or []
            return [float(x) for x in vec]
        except Exception as exc:
            logger.warning("[ai_kb.embed] request_error error={}", str(exc))
            return []

    @staticmethod
    def _read_text_file(abs_path: str) -> str:
        with open(abs_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _read_pdf_file(abs_path: str) -> str:
        reader = PdfReader(abs_path)
        parts: list[str] = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        return "\n".join(parts)

    @staticmethod
    def _read_docx_file(abs_path: str) -> str:
        doc = Document(abs_path)
        return "\n".join([p.text for p in doc.paragraphs if p.text])

    def _extract_text(self, abs_path: str, ext: str) -> str:
        ext = ext.lower()
        if ext in {".txt", ".md"}:
            return self._read_text_file(abs_path)
        if ext == ".pdf":
            return self._read_pdf_file(abs_path)
        if ext == ".docx":
            return self._read_docx_file(abs_path)
        if ext == ".doc":
            logger.warning("[ai_kb.index] doc_not_supported file={}", abs_path)
            return ""
        return ""

    @staticmethod
    def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
        content = (text or "").strip()
        if not content:
            return []
        chunks: list[str] = []
        i = 0
        n = len(content)
        while i < n:
            j = min(n, i + chunk_size)
            chunks.append(content[i:j])
            if j >= n:
                break
            i = max(i + 1, j - overlap)
        return chunks

    async def rebuild_index(self, *, incremental: bool = False) -> dict[str, Any]:
        started = datetime.now()
        rows: list[dict[str, Any]] = []
        conf = await self._runtime_conf()
        chunk_size = int(conf["chunk_size"])
        overlap = int(conf["chunk_overlap"])
        changed_files = 0
        processed_files = 0
        removed_files = 0

        old_meta = self._load_meta() if incremental else {"files": {}}
        old_files: dict[str, Any] = old_meta.get("files", {})
        old_rows = self._load_index() if incremental else []
        keep_rows: list[dict[str, Any]] = []
        if incremental:
            keep_rows = list(old_rows)

        current_files: dict[str, Any] = {}
        for name in os.listdir(self.docs_dir):
            abs_path = os.path.join(self.docs_dir, name)
            if not os.path.isfile(abs_path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in {".txt", ".md", ".pdf", ".docx", ".doc"}:
                continue
            st = os.stat(abs_path)
            signature = {"mtime": int(st.st_mtime), "size": int(st.st_size)}
            current_files[name] = signature
            if incremental and old_files.get(name) == signature:
                continue
            try:
                changed_files += 1
                processed_files += 1
                content = self._extract_text(abs_path, ext)
                if not content.strip():
                    continue
                if incremental:
                    keep_rows = [r for r in keep_rows if r.get("file") != name]
                for idx, chunk in enumerate(self._split_text(content, chunk_size, overlap)):
                    vector = await self._embed_text(chunk[:3000])
                    target = keep_rows if incremental else rows
                    target.append(
                        {
                            "id": f"{name}#{idx}",
                            "file": name,
                            "chunk": chunk,
                            "tokens": list(self._tokenize(chunk)),
                            "vector": vector,
                        }
                    )
            except Exception as exc:
                logger.warning("[ai_kb.index] parse_failed file={} error={}", name, str(exc))
        if incremental:
            missing = [f for f in old_files.keys() if f not in current_files]
            if missing:
                removed_files = len(missing)
                keep_rows = [r for r in keep_rows if r.get("file") not in set(missing)]
            rows = keep_rows

        self._save_index(rows)
        self._save_meta({"files": current_files, "updated_at": datetime.now().strftime(settings.DATETIME_FORMAT)})
        took_ms = int((datetime.now().timestamp() - started.timestamp()) * 1000)
        mode = "incremental" if incremental else "full"
        with open(self.rebuild_log_path, "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.now().strftime(settings.DATETIME_FORMAT)} mode={mode} chunks={len(rows)} changed={changed_files} removed={removed_files} took_ms={took_ms}\n"
            )
        return {
            "chunks": len(rows),
            "mode": mode,
            "changed_files": changed_files,
            "removed_files": removed_files,
            "processed_files": processed_files,
            "took_ms": took_ms,
        }

    async def _retrieve(self, question: str, top_k: int) -> list[dict[str, Any]]:
        q_tokens = self._tokenize(question)
        rows = self._load_index()
        query_vec = await self._embed_text(question)
        scored: list[tuple[float, dict[str, Any]]] = []
        for item in rows:
            tokens = set(item.get("tokens") or [])
            vec = item.get("vector") or []
            score_vec = self._cosine_similarity(query_vec, vec) if query_vec and vec else 0.0
            score_tok = (len(q_tokens & tokens) / max(len(q_tokens), 1)) if q_tokens and tokens else 0.0
            score = score_vec if score_vec > 0 else score_tok
            if score <= 0:
                continue
            scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        result = []
        for score, item in scored[:top_k]:
            result.append({"file": item.get("file"), "chunk": item.get("chunk"), "score": round(score, 4)})
        return result

    async def _call_openai_compatible(self, *, question: str, context: str) -> str:
        runtime = await self._runtime_conf()
        base_url = str(runtime.get("openai_base_url") or "").rstrip("/")
        api_key = str(runtime.get("openai_api_key") or "").strip()
        if not base_url or not api_key:
            return "AI知识库已接入，但未配置LLM_BASE_URL或LLM_API_KEY。"

        prompts = self._load_skill_prompts()
        system_prompt = prompts.get("system") or (
            "你是企业产品功能专家。请严格基于提供的知识片段回答。"
            "若证据不足，明确说明并给出需要补充的信息。"
        )
        intent = self._classify_intent(question)
        tpl = prompts.get(intent) or ""
        if tpl:
            user_prompt = tpl.format(
                query=question,
                context=context,
                industry="未指定",
                scenario=question,
            )
        else:
            user_prompt = f"问题:\n{question}\n\n知识片段:\n{context}"

        max_chars = int(settings.AI_KB_SKILL_MAX_CHARS)
        if len(system_prompt) > max_chars:
            system_prompt = system_prompt[:max_chars]
        if len(user_prompt) > max_chars:
            user_prompt = user_prompt[:max_chars]
        payload = {
            "model": str(runtime.get("openai_model") or settings.LLM_MODEL),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = f"{base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=float(runtime.get("llm_timeout_seconds") or settings.LLM_TIMEOUT_SECONDS)) as client:
                resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                logger.warning("[ai_kb.llm] request_failed status={} body={}", resp.status_code, resp.text[:300])
                return "AI模型调用失败，请稍后重试。"
            data = resp.json()
            choices = data.get("choices") or []
            if not choices:
                return "AI模型未返回可用内容。"
            return str((choices[0].get("message") or {}).get("content") or "").strip() or "AI模型未返回可用内容。"
        except Exception as exc:
            logger.warning("[ai_kb.llm] request_error error={}", str(exc))
            return "AI模型调用异常，请稍后重试。"

    async def _stream_openai_compatible(self, *, question: str, context: str):
        runtime = await self._runtime_conf()
        base_url = str(runtime.get("openai_base_url") or "").rstrip("/")
        api_key = str(runtime.get("openai_api_key") or "").strip()
        if not base_url or not api_key:
            yield "AI知识库已接入，但未配置LLM_BASE_URL或LLM_API_KEY。"
            return

        prompts = self._load_skill_prompts()
        system_prompt = prompts.get("system") or (
            "你是企业产品功能专家。请严格基于提供的知识片段回答。"
            "若证据不足，明确说明并给出需要补充的信息。"
        )
        intent = self._classify_intent(question)
        tpl = prompts.get(intent) or ""
        if tpl:
            user_prompt = tpl.format(query=question, context=context, industry="未指定", scenario=question)
        else:
            user_prompt = f"问题:\n{question}\n\n知识片段:\n{context}"

        max_chars = int(settings.AI_KB_SKILL_MAX_CHARS)
        if len(system_prompt) > max_chars:
            system_prompt = system_prompt[:max_chars]
        if len(user_prompt) > max_chars:
            user_prompt = user_prompt[:max_chars]

        payload = {
            "model": str(runtime.get("openai_model") or settings.LLM_MODEL),
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "stream": True,
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        url = f"{base_url}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=float(runtime.get("llm_timeout_seconds") or settings.LLM_TIMEOUT_SECONDS)) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code >= 400:
                        logger.warning("[ai_kb.llm.stream] request_failed status={}", resp.status_code)
                        yield "AI模型流式调用失败，请稍后重试。"
                        return
                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                            delta = ((obj.get("choices") or [{}])[0].get("delta") or {}).get("content")
                            if delta:
                                yield str(delta)
                        except Exception:
                            continue
        except Exception as exc:
            logger.warning("[ai_kb.llm.stream] request_error error={}", str(exc))
            yield "AI模型流式调用异常，请稍后重试。"

    async def chat(self, *, question: str, top_k: int) -> dict[str, Any]:
        conf = await self._runtime_conf()
        if not conf["enabled"]:
            return {"question": question, "answer": "AI知识库功能已关闭。", "references": []}
        default_top_k = int(conf["top_k"])
        limit = max(1, min(int(top_k or default_top_k), 20))
        refs = await self._retrieve(question, limit)
        context = "\n\n".join([f"[{i+1}] {r['file']}\n{r['chunk']}" for i, r in enumerate(refs)])
        answer = await self._call_openai_compatible(question=question, context=context or "无")
        return {
            "question": question,
            "answer": answer,
            "references": [{"source": r["file"], "title": r["file"], "score": r["score"]} for r in refs],
        }

    async def stream_chat(self, *, question: str, top_k: int):
        conf = await self._runtime_conf()
        if not conf["enabled"]:
            yield {"type": "meta", "references": []}
            yield {"type": "delta", "content": "AI知识库功能已关闭。"}
            yield {"type": "done"}
            return
        default_top_k = int(conf["top_k"])
        limit = max(1, min(int(top_k or default_top_k), 20))
        refs = await self._retrieve(question, limit)
        context = "\n\n".join([f"[{i+1}] {r['file']}\n{r['chunk']}" for i, r in enumerate(refs)])
        yield {"type": "meta", "references": [{"source": r["file"], "title": r["file"], "score": r["score"]} for r in refs]}
        async for token in self._stream_openai_compatible(question=question, context=context or "无"):
            yield {"type": "delta", "content": token}
        yield {"type": "done"}

    async def save_feedback(self, *, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        conf = await self._runtime_conf()
        os.makedirs(self.base_dir, exist_ok=True)
        row = {
            "user_id": user_id,
            "created_at": datetime.now().strftime(settings.DATETIME_FORMAT),
            **payload,
        }
        with open(self.feedback_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

        auto_reindexed = False
        low_score_count = 0
        try:
            if os.path.exists(self.feedback_path):
                with open(self.feedback_path, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-int(conf["feedback_window"]):]
                for line in lines:
                    item = json.loads(line)
                    if int(item.get("score") or 0) <= 2:
                        low_score_count += 1
            if low_score_count >= int(conf["auto_reindex_threshold"]):
                result = await self.rebuild_index(incremental=True)
                auto_reindexed = True
                with open(self.evolution_log_path, "a", encoding="utf-8") as f:
                    f.write(
                        f"{datetime.now().strftime(settings.DATETIME_FORMAT)} auto_reindex low_score_count={low_score_count} chunks={result.get('chunks')} mode={result.get('mode')}\n"
                    )
        except Exception as exc:
            logger.warning("[ai_kb.feedback] evolve_failed error={}", str(exc))

        return {"auto_reindexed": auto_reindexed, "low_score_count": low_score_count}

    async def list_docs(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        if not os.path.exists(self.docs_dir):
            return rows
        for name in os.listdir(self.docs_dir):
            abs_path = os.path.join(self.docs_dir, name)
            if not os.path.isfile(abs_path):
                continue
            stat = os.stat(abs_path)
            rows.append(
                {
                    "name": name,
                    "size": int(stat.st_size),
                    "updated_at": datetime.fromtimestamp(stat.st_mtime).strftime(settings.DATETIME_FORMAT),
                }
            )
        rows.sort(key=lambda x: x["updated_at"], reverse=True)
        return rows

    async def remove_doc(self, stored_name: str) -> bool:
        name = (stored_name or "").strip()
        if not name:
            return False
        abs_path = os.path.normcase(os.path.realpath(os.path.join(self.docs_dir, name)))
        docs_root = os.path.normcase(os.path.realpath(self.docs_dir))
        try:
            in_root = os.path.commonpath([abs_path, docs_root]) == docs_root
        except ValueError:
            in_root = False
        if not in_root or not os.path.isfile(abs_path):
            return False
        try:
            os.remove(abs_path)
            return True
        except OSError as exc:
            logger.warning("[ai_kb.docs] remove_failed file={} error={}", stored_name, str(exc))
            return False

    async def reindex_one_doc(self, stored_name: str) -> dict[str, Any]:
        name = (stored_name or "").strip()
        if not name:
            return {"ok": False, "msg": "文档名为空"}
        abs_path = os.path.normcase(os.path.realpath(os.path.join(self.docs_dir, name)))
        docs_root = os.path.normcase(os.path.realpath(self.docs_dir))
        try:
            in_root = os.path.commonpath([abs_path, docs_root]) == docs_root
        except ValueError:
            in_root = False
        if not in_root or not os.path.isfile(abs_path):
            return {"ok": False, "msg": "文档不存在"}

        ext = os.path.splitext(name)[1].lower()
        if ext not in {".txt", ".md", ".pdf", ".docx", ".doc"}:
            return {"ok": False, "msg": "文档类型不支持重建"}

        conf = await self._runtime_conf()
        chunk_size = int(conf["chunk_size"])
        overlap = int(conf["chunk_overlap"])

        rows = self._load_index()
        rows = [r for r in rows if r.get("file") != name]
        content = self._extract_text(abs_path, ext)
        if not content.strip():
            self._save_index(rows)
            return {"ok": True, "chunks": len(rows), "doc_chunks": 0}

        doc_chunks = 0
        for idx, chunk in enumerate(self._split_text(content, chunk_size, overlap)):
            vector = await self._embed_text(chunk[:3000])
            rows.append(
                {
                    "id": f"{name}#{idx}",
                    "file": name,
                    "chunk": chunk,
                    "tokens": list(self._tokenize(chunk)),
                    "vector": vector,
                }
            )
            doc_chunks += 1
        self._save_index(rows)

        meta = self._load_meta()
        st = os.stat(abs_path)
        meta.setdefault("files", {})[name] = {"mtime": int(st.st_mtime), "size": int(st.st_size)}
        meta["updated_at"] = datetime.now().strftime(settings.DATETIME_FORMAT)
        self._save_meta(meta)
        with open(self.rebuild_log_path, "a", encoding="utf-8") as f:
            f.write(
                f"{datetime.now().strftime(settings.DATETIME_FORMAT)} mode=single file={name} doc_chunks={doc_chunks} chunks={len(rows)}\n"
            )
        return {"ok": True, "chunks": len(rows), "doc_chunks": doc_chunks}

    async def list_rebuild_history(self, limit: int = 50) -> list[str]:
        if not os.path.exists(self.rebuild_log_path):
            return []
        with open(self.rebuild_log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [x.strip() for x in f.readlines() if x.strip()]
        return list(reversed(lines[-max(1, min(limit, 200)):]))

    async def get_status(self) -> dict[str, Any]:
        docs = await self.list_docs()
        chunks = len(self._load_index())
        prompts = self._load_skill_prompts()
        low_score_count = 0
        recent_feedback = 0
        if os.path.exists(self.feedback_path):
            with open(self.feedback_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            recent_feedback = len(lines[-50:])
            for line in lines[-20:]:
                try:
                    item = json.loads(line)
                    if int(item.get("score") or 0) <= 2:
                        low_score_count += 1
                except Exception:
                    continue

        last_evolution = ""
        if os.path.exists(self.evolution_log_path):
            with open(self.evolution_log_path, "r", encoding="utf-8", errors="ignore") as f:
                logs = [x.strip() for x in f.readlines() if x.strip()]
            if logs:
                last_evolution = logs[-1]

        last_rebuild = ""
        if os.path.exists(self.rebuild_log_path):
            with open(self.rebuild_log_path, "r", encoding="utf-8", errors="ignore") as f:
                logs = [x.strip() for x in f.readlines() if x.strip()]
            if logs:
                last_rebuild = logs[-1]

        return {
            "doc_count": len(docs),
            "chunk_count": chunks,
            "recent_feedback": recent_feedback,
            "recent_low_score": low_score_count,
            "last_evolution": last_evolution,
            "last_rebuild": last_rebuild,
            "skill_prompt_loaded": bool(prompts.get("system")),
            "skill_prompt_dir": "app.ai_kb_skill",
        }


ai_kb_controller = AIKnowledgeController()
