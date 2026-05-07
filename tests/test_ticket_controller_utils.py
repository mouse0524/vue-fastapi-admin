import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException

from app.controllers.ticket import TicketController
from app.utils.file_signature import detect_file_type


class TicketControllerUtilsTestCase(unittest.TestCase):
    def test_normalize_extensions(self):
        items = [".PNG", "jpg", "", " png ", None, ".jpg", "GIF"]
        normalized = TicketController._normalize_extensions(items)
        self.assertEqual(normalized, ["png", "jpg", "gif"])

    def test_detect_file_type_png(self):
        data = b"\x89PNG\r\n\x1a\n" + b"payload"
        self.assertEqual(detect_file_type(data), "png")

    def test_detect_file_type_unknown(self):
        data = b"plain-text-content"
        self.assertIsNone(detect_file_type(data))

    async def _bind_with_count(self, count):
        controller = TicketController()

        class FakeQuery:
            async def update(self, **kwargs):
                return count

        with patch("app.controllers.ticket.TicketAttachment.filter", return_value=FakeQuery()):
            return await controller._bind_attachments(ticket_id=1, attachment_ids=[10, 11], owner_ids=[2])

    def test_bind_attachments_rejects_partial_ownership(self):
        with self.assertRaises(HTTPException) as ctx:
            import asyncio

            asyncio.run(self._bind_with_count(1))
        self.assertEqual(ctx.exception.status_code, 403)

    def test_bind_attachments_accepts_full_ownership(self):
        import asyncio

        self.assertEqual(asyncio.run(self._bind_with_count(2)), 2)


if __name__ == "__main__":
    unittest.main()
