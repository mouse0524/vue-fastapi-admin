from __future__ import annotations

from app.models.admin import SkillKnowDocumentChunk, SkillKnowSkill
from app.services.skill_know.graph_service import skill_know_graph_service
from app.services.skill_know.chroma_store import skill_know_chroma_store
from app.services.skill_know.skill_service import skill_know_skill_service
from app.services.skill_know.utils import preview_text, skill_to_dict


class SkillKnowRetriever:
    async def retrieve(self, query: str, *, limit: int = 8) -> list[dict]:
        return await self.retrieve_skills(query, limit=limit)

    async def retrieve_skills(self, query: str, *, limit: int = 8) -> list[dict]:
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

    async def retrieve_document_chunks(self, query: str, *, limit: int = 8) -> list[dict]:
        results = await skill_know_chroma_store.search_document_chunks(query, limit=limit)
        items = []
        for result in results:
            metadata = result.get("metadata") or {}
            chunk = None
            vector_id = result.get("vector_id")
            if vector_id:
                chunk = await SkillKnowDocumentChunk.filter(uri=vector_id).first()
            if not chunk and metadata.get("document_id") is not None and metadata.get("chunk_index") is not None:
                chunk = await SkillKnowDocumentChunk.filter(
                    document_id=int(metadata["document_id"]),
                    chunk_index=int(metadata["chunk_index"]),
                ).first()
            content = chunk.content if chunk else result.get("text") or ""
            data = {
                "source_type": "document",
                "document_id": metadata.get("document_id"),
                "chunk_id": chunk.id if chunk else None,
                "chunk_uri": chunk.uri if chunk else vector_id,
                "title": metadata.get("title") or "文档片段",
                "filename": metadata.get("filename"),
                "heading": metadata.get("heading"),
                "content": content,
                "abstract": preview_text(content, 180),
                "score": round(float(result.get("score") or 0), 4),
                "matched_by": result.get("matched_by") or "document_vector",
                "metadata": metadata,
            }
            items.append(data)
        items.sort(key=lambda x: (-x.get("score", 0), x.get("chunk_id") or 0))
        return items[:limit]

    async def retrieve_context(self, query: str, *, limit: int = 10) -> list[dict]:
        doc_limit = max(4, limit)
        skill_limit = max(3, limit // 2)
        documents = await self.retrieve_document_chunks(query, limit=doc_limit)
        skills = await self.retrieve_skills(query, limit=skill_limit)
        context = [
            *documents,
            *[{**skill, "source_type": "skill", "skill_id": skill.get("id")} for skill in skills],
        ]
        seen: set[str] = set()
        deduped = []
        for item in context:
            key = str(item.get("chunk_uri") or item.get("skill_id") or item.get("id"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        deduped.sort(key=lambda x: (-float(x.get("score") or 0), x.get("priority", 100), -(x.get("id") or x.get("chunk_id") or 0)))
        return deduped[:limit]


skill_know_retriever = SkillKnowRetriever()
