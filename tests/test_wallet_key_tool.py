"""ai_keys_wallet_key tool + issue-disabled hints."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiworkers_mcp.modules import ai as ai_mod

SECRET = "sk-wallet-root-secret-1234567890"
OK = {
    "success": True,
    "key": SECRET,
    "prefix": "sk-wallet-ro",
    "key_alias": "wallet-root",
    "eth_address": "0xabc",
    "created_at": 1,
    "warning": "w",
}


class _Mcp:
    def __init__(self):
        self.tools = {}

    def tool(self):
        def deco(fn):
            self.tools[fn.__name__] = fn
            return fn

        return deco


def _err(status, **kw):
    return RuntimeError(json.dumps({"success": False, "status_code": status, **kw}))


class WalletKeyToolTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(prefix="aw-cred-", suffix=".json", delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.path = Path(tmp.name)
        self._env = patch.dict(os.environ, {"AIWORKERS_CREDENTIALS": tmp.name})
        self._env.start()
        self._parent = patch.object(ai_mod, "_need_parent", return_value=None)
        self._parent.start()
        mcp = _Mcp()
        ai_mod.register(mcp)
        self.tools = mcp.tools

    def tearDown(self):
        self._parent.stop()
        self._env.stop()
        if self.path.exists():
            self.path.unlink()

    def creds(self):
        return json.loads(self.path.read_text())

    def test_no_reveal_saves_without_key_in_output(self):
        with patch.object(ai_mod, "request_ai", return_value=dict(OK)) as m:
            out = self.tools["ai_keys_wallet_key"]()
        self.assertNotIn(SECRET, out)
        data = json.loads(out)
        self.assertNotIn("key", data)
        self.assertEqual(data["prefix"], "sk-wallet-ro")
        self.assertEqual(data["key_alias"], "wallet-root")
        self.assertTrue(data["saved"])
        self.assertEqual(self.creds()["knopka_ai_wallet"]["key"], SECRET)
        self.assertEqual(oct(self.path.stat().st_mode & 0o777), "0o600")
        self.assertEqual(m.call_args.args[:2], ("POST", "/api/mcp/ai-keys/wallet/key"))

    def test_reveal_returns_key(self):
        with patch.object(ai_mod, "request_ai", return_value=dict(OK)):
            data = json.loads(self.tools["ai_keys_wallet_key"](reveal=True, reason="other machine"))
        self.assertEqual(data["key"], SECRET)

    def test_use_as_default(self):
        self.path.write_text(json.dumps({"knopka_ai": {"key": "sk-old", "prefix": "sk-old"}}))
        with patch.object(ai_mod, "request_ai", return_value=dict(OK)):
            self.tools["ai_keys_wallet_key"](use_as_default=True)
        c = self.creds()
        self.assertEqual(c["knopka_ai"]["key"], SECRET)
        self.assertEqual(c["knopka_ai_prev"]["key"], "sk-old")

    def test_nothing_to_do_makes_no_call(self):
        with patch.object(ai_mod, "request_ai") as m:
            data = json.loads(self.tools["ai_keys_wallet_key"](save=False, reveal=False))
        self.assertFalse(data["success"])
        m.assert_not_called()

    def test_disabled_passthrough_with_hint(self):
        e = _err(403, code="wallet_reveal_disabled", message="off")
        with patch.object(ai_mod, "request_ai", side_effect=e):
            data = json.loads(self.tools["ai_keys_wallet_key"]())
        self.assertEqual(data["code"], "wallet_reveal_disabled")
        self.assertIn("Mini App", data["hint"])
        self.assertFalse(self.path.exists())

    def test_rate_limit_keeps_retry_after(self):
        e = _err(429, code="reveal_rate_limited", retry_after=123)
        with patch.object(ai_mod, "request_ai", side_effect=e):
            data = json.loads(self.tools["ai_keys_wallet_key"]())
        self.assertEqual(data["retry_after"], 123)
        self.assertIn("retry_after", data["hint"])

    def test_not_provisioned_hint(self):
        e = _err(409, code="wallet_key_not_provisioned")
        with patch.object(ai_mod, "request_ai", side_effect=e):
            data = json.loads(self.tools["ai_keys_wallet_key"]())
        self.assertIn("Ключ для ИИ", data["hint"])

    def test_issue_denied_hint(self):
        e = _err(403, code="mcp_key_issue_disabled")
        with patch.object(ai_mod, "request_ai", side_effect=e):
            data = json.loads(self.tools["ai_keys_issue"]())
        self.assertEqual(data["code"], "mcp_key_issue_disabled")
        self.assertIn("не обходить", data["hint"])


if __name__ == "__main__":
    unittest.main()
