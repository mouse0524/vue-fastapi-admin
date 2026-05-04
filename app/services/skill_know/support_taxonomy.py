from __future__ import annotations

from copy import deepcopy

from tortoise.exceptions import ConfigurationError

from app.models.enums import SkillKnowSkillCategory
from app.services.skill_know.config_service import skill_know_config_service


DEFAULT_PRODUCT_PROFILES = [
    {"key": "ticket", "name": "工单中心", "modules": ["提交工单", "我的工单", "工单审核", "技术处理", "问题根因"]},
    {"key": "webdav", "name": "WebDAV 外发", "modules": ["外发网盘", "分享链接", "分享记录", "缓存"]},
    {"key": "mail", "name": "邮件通知", "modules": ["SMTP", "验证码邮件", "审核通知", "模板"]},
    {"key": "rbac", "name": "权限与菜单", "modules": ["用户", "角色", "菜单", "API权限"]},
    {"key": "registration", "name": "注册审核", "modules": ["渠道商注册", "用户注册", "审核"]},
    {"key": "skill_know", "name": "Skill-Know", "modules": ["技能", "文档", "搜索", "提示词", "智能对话"]},
]


ISSUE_CATEGORIES = {
    SkillKnowSkillCategory.FAQ.value: {
        "name": "常见问题",
        "keywords": ["是什么", "能不能", "是否支持", "说明", "介绍", "区别"],
        "intents": ["explain", "faq"],
    },
    SkillKnowSkillCategory.TROUBLESHOOTING.value: {
        "name": "故障排查",
        "keywords": ["报错", "失败", "无法", "不能", "异常", "打不开", "超时", "错误", "无效"],
        "intents": ["diagnose", "fix", "troubleshoot"],
    },
    SkillKnowSkillCategory.FEATURE_CONSULTING.value: {
        "name": "功能咨询",
        "keywords": ["怎么用", "如何", "支持", "配置", "操作", "流程"],
        "intents": ["how_to", "consult"],
    },
    SkillKnowSkillCategory.CONFIGURATION.value: {
        "name": "配置问题",
        "keywords": ["配置", "参数", "设置", "环境变量", "连接", "key", "url"],
        "intents": ["configure"],
    },
    SkillKnowSkillCategory.INTEGRATION.value: {
        "name": "集成问题",
        "keywords": ["接口", "API", "集成", "第三方", "WebDAV", "SMTP", "模型"],
        "intents": ["integrate"],
    },
    SkillKnowSkillCategory.KNOWN_ISSUE.value: {
        "name": "已知问题",
        "keywords": ["已知问题", "bug", "缺陷", "版本", "临时方案", "规避"],
        "intents": ["known_issue"],
    },
    SkillKnowSkillCategory.UPGRADE_GUIDE.value: {
        "name": "升级迁移",
        "keywords": ["升级", "迁移", "版本", "兼容", "回滚", "变更"],
        "intents": ["upgrade"],
    },
}


DEFAULT_MATCH_WEIGHTS = {
    "semantic": 0.45,
    "keyword": 0.20,
    "intent": 0.15,
    "product": 0.10,
    "quality": 0.05,
    "priority": 0.05,
}


class SkillKnowSupportTaxonomy:
    async def product_profiles(self) -> list[dict]:
        try:
            configured = await skill_know_config_service.get("support.product_profiles")
        except ConfigurationError:
            configured = None
        return configured if isinstance(configured, list) and configured else deepcopy(DEFAULT_PRODUCT_PROFILES)

    async def match_weights(self) -> dict[str, float]:
        try:
            configured = await skill_know_config_service.get("support.match_weights")
        except ConfigurationError:
            configured = None
        if not isinstance(configured, dict):
            return DEFAULT_MATCH_WEIGHTS.copy()
        weights = DEFAULT_MATCH_WEIGHTS.copy()
        for key, value in configured.items():
            try:
                weights[key] = max(0.0, float(value))
            except (TypeError, ValueError):
                continue
        total = sum(weights.values()) or 1.0
        return {key: value / total for key, value in weights.items()}

    async def taxonomy(self) -> dict:
        return {"products": await self.product_profiles(), "issue_categories": ISSUE_CATEGORIES, "match_weights": await self.match_weights()}


skill_know_support_taxonomy = SkillKnowSupportTaxonomy()
