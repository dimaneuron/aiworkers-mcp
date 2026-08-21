"""Allowlist for api.knopka.click /tg/ (userbot CRM)."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiworkers_mcp.knopka_ai import path_allowed
from aiworkers_mcp.knopka_tg import normalize_tg_path, tg_path_allowed


class KnopkaTgAllowlistTests(unittest.TestCase):
    def test_health_and_accounts(self):
        self.assertTrue(tg_path_allowed("GET", "/health"))
        self.assertTrue(tg_path_allowed("GET", "/tg/health"))
        self.assertTrue(tg_path_allowed("GET", "/accounts"))
        self.assertTrue(tg_path_allowed("GET", "/tg/accounts"))
        self.assertTrue(tg_path_allowed("GET", "/accounts/+79991234567"))
        self.assertTrue(tg_path_allowed("POST", "/accounts/+79991234567/tasks/create-channel"))
        self.assertTrue(tg_path_allowed("POST", "/accounts/acc1/tasks/create-bot"))
        self.assertTrue(tg_path_allowed("POST", "/accounts/acc1/start"))
        self.assertTrue(tg_path_allowed("PUT", "/groups-channels/12"))
        self.assertTrue(tg_path_allowed("POST", "/accounts/login/start"))

    def test_normalize_strips_tg_prefix(self):
        self.assertEqual(normalize_tg_path("/tg/accounts"), "/accounts")
        self.assertEqual(normalize_tg_path("https://api.knopka.click/tg/health"), "/health")
        self.assertEqual(normalize_tg_path("/accounts"), "/accounts")

    def test_host_and_secrets_denied(self):
        self.assertFalse(tg_path_allowed("GET", "/env"))
        self.assertFalse(tg_path_allowed("POST", "/env"))
        self.assertFalse(tg_path_allowed("GET", "/pm2"))
        self.assertFalse(tg_path_allowed("GET", "/pm2/logs"))
        self.assertFalse(tg_path_allowed("GET", "/login"))
        self.assertFalse(tg_path_allowed("POST", "/login"))
        self.assertFalse(tg_path_allowed("POST", "/update"))
        self.assertFalse(tg_path_allowed("GET", "/api/tokens"))
        self.assertFalse(tg_path_allowed("POST", "/api/tokens"))
        self.assertFalse(tg_path_allowed("POST", "/accounts/import-session"))
        self.assertFalse(tg_path_allowed("POST", "/accounts/start-all"))
        self.assertFalse(tg_path_allowed("POST", "/accounts/stop-all"))
        self.assertFalse(tg_path_allowed("GET", "/"))
        self.assertFalse(tg_path_allowed("GET", "/docs"))

    def test_wrong_method_denied(self):
        self.assertFalse(tg_path_allowed("POST", "/health"))
        self.assertFalse(tg_path_allowed("DELETE", "/accounts"))
        self.assertFalse(tg_path_allowed("GET", "/accounts/acc1/tasks/create-channel"))
        self.assertFalse(tg_path_allowed("POST", "/accounts/acc1/tasks/delete-everything"))
        self.assertFalse(tg_path_allowed("PATCH", "/groups-channels/12"))

    def test_dotdot_and_bad_account(self):
        self.assertFalse(tg_path_allowed("GET", "/tg/../env"))
        self.assertFalse(tg_path_allowed("POST", "/accounts/../env"))
        self.assertFalse(tg_path_allowed("GET", "/accounts/foo/bar"))
        self.assertFalse(tg_path_allowed("GET", "/accounts/foo/../health"))

    def test_ai_request_still_denies_tg(self):
        self.assertFalse(path_allowed("/tg/health"))
        self.assertFalse(path_allowed("/tg/accounts"))
        self.assertFalse(path_allowed("/health"))


if __name__ == "__main__":
    unittest.main()
