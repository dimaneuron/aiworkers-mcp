"""aiworkers-mcp login: device pairing default, paste fallback."""

import contextlib
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiworkers_mcp import login


class FakeResp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status
        self.text = json.dumps(data)

    def json(self):
        return self._data


class FakeClient:
    def __init__(self, resp):
        self._resp = resp

    def __call__(self, *a, **kw):
        return self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get(self, url, **kw):
        return self._resp


class LoginPairingTests(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.cred = Path(self._dir.name) / "credentials.json"
        self._env = patch.dict(os.environ, {"AIWORKERS_CREDENTIALS": str(self.cred)})
        self._env.start()
        self._sleep = patch.object(login.time, "sleep", lambda s: None)
        self._sleep.start()
        self.out = io.StringIO()
        self.err = io.StringIO()

    def tearDown(self):
        self._sleep.stop()
        self._env.stop()
        self._dir.cleanup()

    def run_login(self, args=None, *, pasted="", whoami=None):
        whoami = whoami or FakeResp({"success": True, "kind": "parent", "prefix": "awp_abc"})
        with patch.object(login.getpass, "getpass", return_value=pasted) as gp, \
                patch.object(login.httpx, "Client", FakeClient(whoami)), \
                contextlib.redirect_stdout(self.out), contextlib.redirect_stderr(self.err):
            try:
                login.cmd_login(args)
            except SystemExit as e:
                return gp, e.code
        return gp, None

    def creds(self):
        return json.loads(self.cred.read_text())

    def test_pending_then_confirmed_saves_parent(self):
        polls = iter([
            {"status": "pending"},
            {"status": "pending"},
            {"status": "confirmed", "parent_token": "awp_SECRETVALUE", "prefix": "awp_SECRETVA", "eth_address": "0xabc"},
        ])
        with patch.object(login, "device_start", return_value=("DEV", "ABCD-1234", 600)), \
                patch.object(login, "device_poll", lambda dc: next(polls)):
            gp, code = self.run_login()
        self.assertIsNone(code)
        gp.assert_not_called()
        self.assertEqual(self.creds()["parent"], "awp_SECRETVALUE")
        self.assertEqual(stat.S_IMODE(self.cred.stat().st_mode), 0o600)
        text = self.out.getvalue()
        self.assertIn("ABCD-1234", text)
        self.assertIn("mcplogin_ABCD-1234", text)
        self.assertIn("awp_SECRETVA", text)
        self.assertNotIn("awp_SECRETVALUE", text + self.err.getvalue())
        self.assertNotIn("DEV", text.replace("DEV_", ""))
        self.assertFalse((self.cred.parent / "pending_login.json").exists())

    def test_expired_falls_back_to_paste(self):
        with patch.object(login, "device_start", return_value=("DEV", "ABCD", 600)), \
                patch.object(login, "device_poll", lambda dc: {"status": "expired"}):
            gp, code = self.run_login(pasted="awp_pasted")
        self.assertIsNone(code)
        gp.assert_called_once()
        self.assertEqual(self.creds()["parent"], "awp_pasted")
        self.assertIn("expired", self.err.getvalue())

    def test_start_failure_falls_back(self):
        def boom():
            raise RuntimeError("503")
        with patch.object(login, "device_start", boom):
            gp, code = self.run_login(pasted="awp_pasted")
        self.assertIsNone(code)
        gp.assert_called_once()
        self.assertIn("503", self.err.getvalue())
        self.assertEqual(self.creds()["parent"], "awp_pasted")

    def test_paste_flag_skips_pairing(self):
        def boom():
            raise AssertionError("pairing must be skipped")
        with patch.object(login, "device_start", boom):
            gp, code = self.run_login(["--paste"], pasted="awp_pasted")
        self.assertIsNone(code)
        self.assertEqual(self.creds()["parent"], "awp_pasted")

    def test_keyboard_interrupt_falls_back(self):
        def interrupt(dc):
            raise KeyboardInterrupt
        with patch.object(login, "device_start", return_value=("DEV", "ABCD", 600)), \
                patch.object(login, "device_poll", interrupt):
            gp, code = self.run_login(pasted="awp_pasted")
        self.assertIsNone(code)
        gp.assert_called_once()
        self.assertIn("interrupted", self.out.getvalue())
        self.assertEqual(self.creds()["parent"], "awp_pasted")

    def test_invalid_pasted_token_leaves_credentials_unchanged(self):
        self.cred.write_text(json.dumps({"parent": "awp_old"}))
        bad = FakeResp({"success": False, "message": "invalid token"}, 401)
        gp, code = self.run_login(["--paste"], pasted="awp_bad", whoami=bad)
        self.assertEqual(code, 1)
        self.assertEqual(self.creds(), {"parent": "awp_old"})

    def test_paste_child_token_saved_under_module(self):
        child = FakeResp({"success": True, "kind": "child", "module": "tasks", "group_id": "g1", "prefix": "awm_x"})
        gp, code = self.run_login(["--paste"], pasted="awm_tok", whoami=child)
        self.assertIsNone(code)
        self.assertEqual(self.creds()["keys"]["tasks"], {"token": "awm_tok", "group_id": "g1"})
        self.assertNotIn("parent", self.creds())

    def test_unknown_arg_is_error(self):
        gp, code = self.run_login(["--bogus"])
        self.assertEqual(code, 2)
        self.assertIn("usage", self.err.getvalue())


if __name__ == "__main__":
    unittest.main()
