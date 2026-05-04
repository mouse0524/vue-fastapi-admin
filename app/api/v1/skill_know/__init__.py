from fastapi import APIRouter

from .chat import router as chat_router
from .documents import router as documents_router
from .folders import router as folders_router
from .graph import router as graph_router
from .health import router as health_router
from .pack import router as pack_router
from .prompts import router as prompts_router
from .quick_setup import router as quick_setup_router
from .search import router as search_router
from .skills import router as skills_router
from .upload import router as upload_router

skill_know_router = APIRouter()
skill_know_router.include_router(folders_router, prefix="/folders", tags=["Skill-Know 文件夹"])
skill_know_router.include_router(skills_router, prefix="/skills", tags=["Skill-Know 技能"])
skill_know_router.include_router(documents_router, prefix="/documents", tags=["Skill-Know 文档"])
skill_know_router.include_router(search_router, prefix="/search", tags=["Skill-Know 搜索"])
skill_know_router.include_router(graph_router, prefix="/graph", tags=["Skill-Know 知识图谱"])
skill_know_router.include_router(chat_router, prefix="/chat", tags=["Skill-Know 对话"])
skill_know_router.include_router(prompts_router, prefix="/prompts", tags=["Skill-Know 提示词"])
skill_know_router.include_router(quick_setup_router, prefix="/quick-setup", tags=["Skill-Know 快速设置"])
skill_know_router.include_router(upload_router, prefix="/upload", tags=["Skill-Know 批量上传"])
skill_know_router.include_router(pack_router, prefix="/pack", tags=["Skill-Know 知识包"])
skill_know_router.include_router(health_router, prefix="/health", tags=["Skill-Know 健康检查"])

__all__ = ["skill_know_router"]
