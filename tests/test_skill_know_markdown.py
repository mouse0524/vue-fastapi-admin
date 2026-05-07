import unittest

from app.services.skill_know.document_parser import SUPPORTED_MARKDOWN_UPLOAD_EXTENSIONS
from app.services.skill_know.markdown_chunker import skill_know_markdown_chunker


class SkillKnowMarkdownTestCase(unittest.TestCase):
    def test_supported_extensions_exclude_legacy_office_formats(self):
        for ext in ["pdf", "pptx", "docx", "xlsx", "html", "htm", "csv", "json", "xml", "txt", "md", "markdown"]:
            self.assertIn(ext, SUPPORTED_MARKDOWN_UPLOAD_EXTENSIONS)

        for ext in ["doc", "ppt", "xls"]:
            self.assertNotIn(ext, SUPPORTED_MARKDOWN_UPLOAD_EXTENSIONS)

    def test_chunker_preserves_heading_context(self):
        markdown = "# 产品手册\n\n## 登录认证\n\n" + "验证码错误时请重新获取验证码。\n\n" * 80

        chunks = skill_know_markdown_chunker.chunk(markdown, target_chars=300, max_chars=500, overlap_chars=50)

        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].index, 0)
        self.assertTrue(any(chunk.heading and "产品手册" in chunk.heading for chunk in chunks))
        self.assertTrue(any(chunk.heading and "登录认证" in chunk.heading for chunk in chunks))
        self.assertTrue(all(chunk.content for chunk in chunks))
        self.assertTrue(all(chunk.token_count > 0 for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
