from fastapi import APIRouter, Query

from app.schemas.base import Success
from app.schemas.skill_know import SkillKnowSqlIn
from app.services.skill_know.search_service import skill_know_search_service

router = APIRouter()


@router.get("", summary="统一搜索")
async def unified_search(q: str = Query(...), type: str | None = Query(None), limit: int = Query(20, ge=1, le=100)):
    return Success(data=await skill_know_search_service.unified(q, search_type=type, limit=limit))


@router.post("/sql", summary="SQL只读搜索")
async def sql_search(payload: SkillKnowSqlIn):
    return Success(data=await skill_know_search_service.sql(payload.query))


@router.get("/tables", summary="可查询表")
async def list_tables():
    return Success(data={"tables": skill_know_search_service.tables()})
