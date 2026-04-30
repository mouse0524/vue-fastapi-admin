import unittest

from app.controllers.ticket import TicketController


class TicketControllerUtilsTestCase(unittest.TestCase):
    def test_normalize_extensions(self):
        items = [".PNG", "jpg", "", " png ", None, ".jpg", "GIF"]
        normalized = TicketController._normalize_extensions(items)
        self.assertEqual(normalized, ["png", "jpg", "gif"])

    def test_detect_file_type_png(self):
        data = b"\x89PNG\r\n\x1a\n" + b"payload"
        self.assertEqual(TicketController._detect_file_type(data), "png")

    def test_detect_file_type_unknown(self):
        data = b"plain-text-content"
        self.assertIsNone(TicketController._detect_file_type(data))


if __name__ == "__main__":
    unittest.main()
