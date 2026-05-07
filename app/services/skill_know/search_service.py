from __future__ import annotations

from fastapi import HTTPException
from tortoise import Tortoise

from app.services.skill_know.document_service import skill_know_document_service
from app.services.skill_know.retriever import skill_know_retriever


class SkillKnowSearchService:
    ALLOWED_TABLES = {"sk_skill", "sk_document", "sk_folder", "sk_prompt"}

    async def unified(self, query: str, *, search_type: str | None = None, limit: int = 20) -> dict:
        result = {"query": query, "skills": [], "documents": [], "chunks": [], "items": [], "total": 0}
        if search_type in {None, "all", "skill"}:
            result["skills"] = await skill_know_retriever.retrieve_skills(query, limit=limit)
        if search_type in {None, "all", "document"}:
            result["documents"] = await skill_know_document_service.search(query, limit=limit)
            result["chunks"] = await skill_know_retriever.retrieve_document_chunks(query, limit=limit)
        if search_type in {None, "all"}:
            result["items"] = await skill_know_retriever.retrieve_context(query, limit=limit)
        else:
            result["items"] = [*result["chunks"], *result["skills"]]
        result["total"] = len(result["items"]) or (len(result["skills"]) + len(result["documents"]) + len(result["chunks"]))
        return result

    async def sql(self, query: str) -> dict:
        clean = query.strip().rstrip(";")
        upper = clean.upper()
        if not upper.startswith("SELECT "):
            raise HTTPException(status_code=400, detail="仅支持 SELECT 查询")
        if ";" in clean:
            raise HTTPException(status_code=400, detail="不允许多语句查询")
        banned = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", "TRUNCATE", "REPLACE"]
        if any(f" {word} " in f" {upper} " for word in banned):
            raise HTTPException(status_code=400, detail="SQL 包含不允许的操作")
        if not any(table.upper() in upper for table in self.ALLOWED_TABLES):
            raise HTTPException(status_code=400, detail="仅允许查询 Skill-Know 相关表")
        conn = Tortoise.get_connection("models")
        rows = await conn.execute_query_dict(clean)
        return {"query": clean, "results": rows, "count": len(rows)}

    def tables(self) -> list[dict]:
        return [
            {"name": "sk_skill", "description": "技能表", "columns": ["id", "name", "description", "type", "category", "abstract", "overview", "content"]},
            {"name": "sk_document", "description": "文档表", "columns": ["id", "title", "filename", "status", "category", "tags", "content"]},
            {"name": "sk_folder", "description": "文件夹表", "columns": ["id", "name", "parent_id", "sort_order", "is_system"]},
            {"name": "sk_prompt", "description": "提示词表", "columns": ["key", "category", "name", "content", "is_active"]},
        ]


skill_know_search_service = SkillKnowSearchService()
