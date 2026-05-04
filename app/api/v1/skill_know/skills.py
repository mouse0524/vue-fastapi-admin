from fastapi import APIRouter, Query

from app.models.enums import SkillKnowSkillCategory, SkillKnowSkillType
from app.schemas.base import Success, SuccessExtra
from app.schemas.skill_know import SkillKnowMoveIn, SkillKnowSearchIn, SkillKnowSkillIn, SkillKnowSkillUpdate
from app.services.skill_know.skill_initializer import init_skill_know_defaults
from app.services.skill_know.skill_service import skill_know_skill_service

router = APIRouter()


@router.post("/initialize", summary="初始化系统Skill")
async def initialize_skills():
    await init_skill_know_defaults()
    return Success(msg="初始化成功")


@router.get("/list", summary="技能列表")
async def list_skills(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    type: SkillKnowSkillType | None = Query(None),
    category: SkillKnowSkillCategory | None = Query(None),
    folder_id: int | None = Query(None),
    is_active: bool | None = Query(True),
):
    total, rows = await skill_know_skill_service.list(
        page=page,
        page_size=page_size,
        skill_type=type,
        category=category,
        folder_id=folder_id,
        is_active=is_active,
    )
    return SuccessExtra(data=rows, total=total, page=page, page_size=page_size)


@router.post("/create", summary="创建技能")
async def create_skill(payload: SkillKnowSkillIn):
    return Success(data=await skill_know_skill_service.create(payload))


@router.get("/get", summary="技能详情")
async def get_skill(skill_id: int = Query(...)):
    return Success(data=await skill_know_skill_service.get(skill_id))


@router.post("/update", summary="更新技能")
async def update_skill(payload: SkillKnowSkillUpdate):
    return Success(data=await skill_know_skill_service.update(payload))


@router.delete("/delete", summary="删除技能")
async def delete_skill(skill_id: int = Query(...)):
    await skill_know_skill_service.delete(skill_id)
    return Success(msg="删除成功")


@router.post("/move", summary="移动技能")
async def move_skill(payload: SkillKnowMoveIn):
    return Success(data=await skill_know_skill_service.move(payload.target_id, payload.folder_id))


@router.post("/search", summary="搜索技能")
async def search_skills(payload: SkillKnowSearchIn):
    rows = await skill_know_skill_service.text_search(payload.query, limit=payload.limit, category=payload.category, skill_type=payload.type)
    return Success(data={"items": rows, "total": len(rows)})
