import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.core.middlewares import HttpAuditLogMiddleware
from app.services.skill_know.search_service import skill_know_search_service


class SecurityControlsTestCase(unittest.TestCase):
    def test_audit_log_masks_sensitive_fields(self):
        middleware = HttpAuditLogMiddleware(app=None, methods=["POST"], exclude_paths=[])
        payload = {
            "username": "demo",
            "password": "secret",
            "nested": {"smtp_password": "mail-secret", "safe": "value"},
            "items": [{"token": "jwt", "name": "x"}],
        }

        masked = middleware._mask_sensitive(payload)

        self.assertEqual(masked["password"], "******")
        self.assertEqual(masked["nested"]["smtp_password"], "******")
        self.assertEqual(masked["nested"]["safe"], "value")
        self.assertEqual(masked["items"][0]["token"], "******")

    def test_skill_know_sql_search_disabled_by_default(self):
        async def run():
            with patch("app.services.skill_know.search_service.settings.SKILL_KNOW_SQL_SEARCH_ENABLED", False):
                await skill_know_search_service.sql("SELECT id FROM sk_skill LIMIT 1")

        import asyncio

        with self.assertRaises(HTTPException) as ctx:
            asyncio.run(run())
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
