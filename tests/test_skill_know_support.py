import unittest
from unittest.mock import AsyncMock, patch

from app.services.skill_know.prompt_service import DEFAULT_PROMPTS
from app.services.skill_know.support_matcher import skill_know_support_matcher


class SkillKnowSupportTestCase(unittest.IsolatedAsyncioTestCase):
    async def test_classify_troubleshooting_query(self):
        result = await skill_know_support_matcher.classify("提交工单验证码一直错误，无法提交", product_type="ticket")

        self.assertEqual(result["product_type"], "ticket")
        self.assertEqual(result["issue_category"], "troubleshooting")
        self.assertGreaterEqual(result["confidence"], 0.5)

    async def test_evaluate_skill_requires_support_fields(self):
        skill = {
            "category": "troubleshooting",
            "content": "验证码错误时，请检查验证码是否过期、邮箱配置是否正常，并重新获取验证码后提交。",
            "trigger_keywords": ["验证码", "错误"],
            "trigger_intents": ["troubleshooting"],
            "config": {
                "support": {
                    "product_type": "ticket",
                    "issue_category": "troubleshooting",
                    "symptoms": ["验证码错误"],
                    "root_causes": ["验证码过期"],
                    "solution_levels": [{"level": 1, "title": "快速解决", "steps": ["重新获取验证码"]}],
                }
            },
        }

        quality = skill_know_support_matcher.evaluate_skill(skill)

        self.assertEqual(quality["score"], 1.0)
        self.assertEqual(quality["missing"], [])

    async def test_match_ranks_keyword_and_support_hits(self):
        candidate = {
            "id": 1,
            "name": "工单验证码错误处理",
            "description": "处理提交工单时验证码错误的问题",
            "category": "troubleshooting",
            "content": "重新获取验证码，检查邮件配置。",
            "trigger_keywords": ["验证码", "提交工单"],
            "trigger_intents": ["troubleshooting"],
            "priority": 10,
            "score": 0.6,
            "config": {
                "support": {
                    "product_type": "ticket",
                    "product_module": "提交工单",
                    "issue_category": "troubleshooting",
                    "symptoms": ["验证码错误"],
                    "root_causes": ["验证码过期"],
                    "solution_levels": [{"level": 1, "title": "快速解决", "steps": ["重新获取验证码"]}],
                    "quality_score": 1.0,
                }
            },
        }

        with (
            patch("app.services.skill_know.support_matcher.skill_know_retriever.retrieve", AsyncMock(return_value=[candidate])),
            patch("app.services.skill_know.support_matcher.skill_know_skill_service.text_search", AsyncMock(return_value=[])),
        ):
            result = await skill_know_support_matcher.match("提交工单验证码错误", product_type="ticket")

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["matches"][0]["id"], 1)
        self.assertGreater(result["matches"][0]["score"], 0.6)
        self.assertTrue(result["matches"][0]["solution_levels"])

    def test_default_prompts_include_support_templates(self):
        keys = {item["key"] for item in DEFAULT_PROMPTS}

        self.assertIn("system.support_chat", keys)
        self.assertIn("skill.support_generator", keys)
        self.assertIn("support.classifier", keys)


if __name__ == "__main__":
    unittest.main()
