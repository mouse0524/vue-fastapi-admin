from app.models.admin import SkillKnowSkill
from app.models.enums import SkillKnowSkillCategory, SkillKnowSkillType
from app.schemas.skill_know import SkillKnowSkillIn
from app.services.skill_know.prompt_service import skill_know_prompt_service
from app.services.skill_know.skill_service import skill_know_skill_service


SYSTEM_SKILLS = [
    {
        "name": "SQL 只读搜索",
        "description": "通过安全 SELECT 查询检索 Skill-Know 数据表。",
        "category": SkillKnowSkillCategory.SEARCH,
        "content": "仅允许对 sk_skill、sk_document、sk_folder、sk_prompt 执行 SELECT 查询，禁止修改数据。",
        "trigger_keywords": ["SQL", "查询", "表", "数据"],
        "always_apply": False,
        "priority": 10,
    },
    {
        "name": "知识库检索",
        "description": "使用 L0/L1 分层内容和 ChromaDB 语义检索找到相关 Skill。",
        "category": SkillKnowSkillCategory.RETRIEVAL,
        "content": "优先使用 L0 摘要召回候选 Skill，再结合 L1 概览和优先级进行排序。",
        "trigger_keywords": ["搜索", "检索", "知识库", "Skill"],
        "always_apply": True,
        "priority": 1,
    },
]


async def init_skill_know_defaults() -> None:
    await skill_know_prompt_service.initialize_defaults()
    for item in SYSTEM_SKILLS:
        exists = await SkillKnowSkill.filter(name=item["name"], type=SkillKnowSkillType.SYSTEM).first()
        if exists:
            continue
        payload = SkillKnowSkillIn(**item)
        await skill_know_skill_service.create(payload, skill_type=SkillKnowSkillType.SYSTEM)
