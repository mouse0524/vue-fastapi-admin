from fastapi import APIRouter

from app.schemas.base import Success
from app.services.skill_know.config_service import skill_know_config_service

router = APIRouter()


@router.get("", summary="Skill-Know健康检查")
async def health_check():
    return Success(data={"status": "healthy", "configured": await skill_know_config_service.is_configured()})


@router.get("/detail", summary="Skill-Know详细健康检查")
async def health_detail():
    return Success(data={
        "status": "healthy",
        "components": {
            "database": "ok",
            "chroma": "configured",
            "openai": "configured" if await skill_know_config_service.is_configured() else "missing_api_key",
        },
    })
