"""Allowlist for api.knopka.click paths."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiworkers_mcp.knopka_ai import normalize_ai_path, path_allowed


class KnopkaAiAllowlistTests(unittest.TestCase):
    def test_openai_chat(self):
        self.assertTrue(path_allowed("/v1/chat/completions"))
        self.assertTrue(path_allowed("v1/chat/completions"))
        self.assertTrue(path_allowed("/v1/chat/completions?foo=1"))

    def test_custom_cursor_and_videos(self):
        self.assertTrue(path_allowed("/cursor/chat/completions"))
        self.assertTrue(path_allowed("/v1/videos"))
        self.assertTrue(path_allowed("/v1/videos/abc/content"))
        self.assertTrue(path_allowed("/rag/query"))
        self.assertTrue(path_allowed("/v1/messages"))
        self.assertTrue(path_allowed("/key/info"))

    def test_admin_denied(self):
        self.assertFalse(path_allowed("/key/issue"))
        self.assertFalse(path_allowed("/key/generate"))
        self.assertFalse(path_allowed("/key/delete"))
        self.assertFalse(path_allowed("/user/delete"))
        self.assertFalse(path_allowed("/global/spend/reset"))
        self.assertFalse(path_allowed("/credentials"))
        self.assertFalse(path_allowed("/model/new"))
        self.assertFalse(path_allowed("/team/list"))
        self.assertFalse(path_allowed("/config/pass_through_endpoint"))

    def test_unknown_denied(self):
        self.assertFalse(path_allowed("/health"))
        self.assertFalse(path_allowed("/"))
        self.assertFalse(path_allowed(""))

    def test_dotdot_rejected(self):
        self.assertFalse(path_allowed("/v1/../key/generate"))
        with self.assertRaises(ValueError):
            normalize_ai_path("/v1/../key/generate")

    def test_normalize_strips_query(self):
        self.assertEqual(normalize_ai_path("/v1/models?foo=1"), "/v1/models")
        self.assertEqual(normalize_ai_path("https://api.knopka.click/v1/models"), "/v1/models")


if __name__ == "__main__":
    unittest.main()
