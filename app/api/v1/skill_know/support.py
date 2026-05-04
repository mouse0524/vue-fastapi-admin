from fastapi import APIRouter

from app.schemas.base import Success
from app.schemas.skill_know import SkillKnowSupportEvaluateSkillIn, SkillKnowSupportMatchIn
from app.services.skill_know.support_matcher import skill_know_support_matcher
from app.services.skill_know.support_taxonomy import skill_know_support_taxonomy

router = APIRouter()


@router.get("/taxonomy", summary="产品支持分类体系")
async def support_taxonomy():
    return Success(data=await skill_know_support_taxonomy.taxonomy())


@router.post("/match", summary="产品问题匹配")
async def support_match(payload: SkillKnowSupportMatchIn):
    return Success(data=await skill_know_support_matcher.match(
        payload.query,
        product_type=payload.product_type,
        product_module=payload.product_module,
        issue_category=payload.issue_category,
        limit=payload.limit,
    ))


@router.post("/evaluate-skill", summary="产品支持 Skill 质量评估")
async def evaluate_skill(payload: SkillKnowSupportEvaluateSkillIn):
    return Success(data=await skill_know_support_matcher.evaluate_skill_by_id(payload.skill_id))
