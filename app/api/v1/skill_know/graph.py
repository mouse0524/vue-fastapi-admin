from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

from app.schemas.base import Success
from app.services.skill_know.graph_service import skill_know_graph_service

router = APIRouter()


class RelationIn(BaseModel):
    source_uri: str = Field(..., min_length=1)
    target_uri: str = Field(..., min_length=1)
    relation_type: str = "related_to"
    reason: str = ""
    weight: float = 1.0
    metadata: dict = Field(default_factory=dict)


@router.get("", summary="知识图谱")
async def get_graph(center_uri: str | None = Query(None), depth: int = Query(2, ge=1, le=3), limit: int = Query(200, ge=1, le=1000)):
    return Success(data=await skill_know_graph_service.graph(center_uri=center_uri, depth=depth, limit=limit))


@router.get("/relations", summary="知识关系列表")
async def list_relations(uri: str | None = Query(None), relation_type: str | None = Query(None), limit: int = Query(200, ge=1, le=1000)):
    return Success(data={"items": await skill_know_graph_service.relations(uri=uri, relation_type=relation_type, limit=limit)})


@router.post("/relations/create", summary="创建知识关系")
async def create_relation(payload: RelationIn):
    return Success(data=await skill_know_graph_service.record(
        source_uri=payload.source_uri,
        target_uri=payload.target_uri,
        relation_type=payload.relation_type,
        reason=payload.reason,
        weight=payload.weight,
        metadata=payload.metadata,
    ))


@router.delete("/relations/delete", summary="删除知识关系")
async def delete_relation(relation_id: int = Query(...)):
    await skill_know_graph_service.delete(relation_id)
    return Success(msg="删除成功")
