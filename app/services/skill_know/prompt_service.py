from __future__ import annotations

from fastapi import HTTPException

from app.models.admin import SkillKnowPrompt
from app.models.enums import SkillKnowPromptCategory
from app.services.skill_know.utils import prompt_to_dict


DEFAULT_PROMPTS = [
    {
        "key": "system.chat",
        "category": SkillKnowPromptCategory.CHAT,
        "name": "智能对话系统提示词",
        "description": "控制知识库对话助手的整体行为",
        "content": "你是 Skill-Know 知识库助手。请优先基于已激活的 Skill、产品问题匹配结果和检索上下文回答。回答产品支持问题时，先判断问题类型和置信度，再按快速解决、深入排查、升级处理三个层级展示方案；无法确定时先提出澄清问题，不要编造不存在的产品能力、配置项或接口。",
        "variables": ["context", "skills", "question"],
    },
    {
        "key": "system.support_chat",
        "category": SkillKnowPromptCategory.CHAT,
        "name": "产品支持对话提示词",
        "description": "产品问题支持场景专用系统提示词",
        "content": "你是产品问题支持助手。必须基于匹配到的 Skill 和上下文回答。输出结构：1. 问题判断；2. 最可能原因；3. 快速解决；4. 深入排查；5. 需要补充的信息；6. 升级处理条件。若匹配置信度低于中等，先追问产品模块、错误信息、操作步骤和环境版本。禁止臆测未提供的产品功能。",
        "variables": ["support_match", "context", "question"],
    },
    {
        "key": "skill.generator",
        "category": SkillKnowPromptCategory.SKILL,
        "name": "Skill 生成提示词",
        "description": "文档转 Skill 时使用",
        "content": "请将文档提炼为可检索、可复用的 Skill，保留关键步骤、约束、示例、适用范围和风险提示。若内容属于产品支持场景，请抽取产品类型、模块、问题分类、症状、可能原因、解决步骤和升级条件。",
        "variables": ["document"],
    },
    {
        "key": "skill.support_generator",
        "category": SkillKnowPromptCategory.SKILL,
        "name": "产品支持 Skill 生成提示词",
        "description": "文档转产品支持 Skill 时使用",
        "content": "请把产品支持文档转换为 JSON。字段包括 name、description、issue_category(faq/troubleshooting/feature_consulting/configuration/integration/known_issue/upgrade_guide)、product_type、product_module、symptoms、root_causes、trigger_keywords、trigger_intents、solution_levels(三级：快速解决/深入排查/升级处理)、affected_versions、severity、quality_score。只返回 JSON。",
        "variables": ["document", "product_profiles"],
    },
    {
        "key": "skill.quality_evaluator",
        "category": SkillKnowPromptCategory.SKILL,
        "name": "Skill 质量评估提示词",
        "description": "评估产品支持 Skill 的专业性和实用性",
        "content": "请评估 Skill 是否具备产品模块、问题分类、触发关键词、症状、原因、分级解决方案、适用范围和风险提示。返回 quality_score(0-1)、missing_fields、improvement_suggestions。只返回 JSON。",
        "variables": ["skill"],
    },
    {
        "key": "search.intent",
        "category": SkillKnowPromptCategory.SEARCH,
        "name": "搜索意图分析提示词",
        "description": "分析用户查询意图",
        "content": "请抽取用户查询的关键词、目标对象、产品模块、问题分类、症状、错误信息和意图。",
        "variables": ["query"],
    },
    {
        "key": "support.classifier",
        "category": SkillKnowPromptCategory.CLASSIFICATION,
        "name": "产品问题分类提示词",
        "description": "分析产品支持问题的类型与置信度",
        "content": "请识别用户问题的 product_type、product_module、issue_category、severity、symptoms、error_codes、confidence，并给出需要补充的信息。只返回 JSON。",
        "variables": ["query", "product_profiles", "issue_categories"],
    },
]


class SkillKnowPromptService:
    async def initialize_defaults(self) -> None:
        for item in DEFAULT_PROMPTS:
            exists = await SkillKnowPrompt.filter(key=item["key"]).first()
            if not exists:
                await SkillKnowPrompt.create(**item)

    async def list(self, category: str | None = None, include_inactive: bool = False) -> list[dict]:
        await self.initialize_defaults()
        query = SkillKnowPrompt.all()
        if category:
            query = query.filter(category=category)
        if not include_inactive:
            query = query.filter(is_active=True)
        rows = await query.order_by("category", "key")
        return [await prompt_to_dict(item) for item in rows]

    async def get(self, key: str) -> dict:
        await self.initialize_defaults()
        item = await SkillKnowPrompt.filter(key=key).first()
        if not item:
            raise HTTPException(status_code=404, detail="提示词不存在")
        return await prompt_to_dict(item)

    async def update(self, key: str, data) -> dict:
        item = await SkillKnowPrompt.filter(key=key).first()
        if not item:
            raise HTTPException(status_code=404, detail="提示词不存在")
        if data.content is not None:
            item.content = data.content
        if data.is_active is not None:
            item.is_active = data.is_active
        await item.save()
        return await prompt_to_dict(item)

    async def reset(self, key: str) -> dict:
        default = next((item for item in DEFAULT_PROMPTS if item["key"] == key), None)
        if not default:
            raise HTTPException(status_code=400, detail="该提示词没有默认值")
        item = await SkillKnowPrompt.filter(key=key).first()
        if not item:
            item = await SkillKnowPrompt.create(**default)
        else:
            item.content = default["content"]
            item.variables = default["variables"]
            item.is_active = True
            await item.save()
        return await prompt_to_dict(item)


skill_know_prompt_service = SkillKnowPromptService()
