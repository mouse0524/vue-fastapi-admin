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
        "content": "你是 Skill-Know 知识库助手。请优先基于已激活的 Skill 和检索上下文回答，无法确定时明确说明。",
        "variables": ["context", "skills", "question"],
    },
    {
        "key": "skill.generator",
        "category": SkillKnowPromptCategory.SKILL,
        "name": "Skill 生成提示词",
        "description": "文档转 Skill 时使用",
        "content": "请将文档提炼为可检索、可复用的 Skill，保留关键步骤、约束和示例。",
        "variables": ["document"],
    },
    {
        "key": "search.intent",
        "category": SkillKnowPromptCategory.SEARCH,
        "name": "搜索意图分析提示词",
        "description": "分析用户查询意图",
        "content": "请抽取用户查询的关键词、目标对象和意图。",
        "variables": ["query"],
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
