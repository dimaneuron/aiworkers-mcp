"""credentials.json knopka_ai save/clear."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiworkers_mcp.login import clear_knopka_ai_key, save_knopka_ai_key


class KnopkaAiCredentialsTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(prefix="aw-cred-", suffix=".json", delete=False)
        self._tmp.close()
        os.unlink(self._tmp.name)
        self._env = patch.dict(os.environ, {"AIWORKERS_CREDENTIALS": self._tmp.name})
        self._env.start()

    def tearDown(self):
        self._env.stop()
        path = Path(self._tmp.name)
        if path.exists():
            path.unlink()

    def test_save_does_not_clobber_parent(self):
        path = Path(self._tmp.name)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"parent": "awp_keep", "keys": {"workers": {"token": "awm_x"}}}) + "\n")
        save_knopka_ai_key("sk-test-secret", alias="gpt", prefix="sk-test-secr")
        data = json.loads(path.read_text())
        self.assertEqual(data["parent"], "awp_keep")
        self.assertEqual(data["keys"]["workers"]["token"], "awm_x")
        self.assertEqual(data["knopka_ai"]["key"], "sk-test-secret")
        self.assertEqual(data["knopka_ai"]["key_alias"], "gpt")

    def test_clear_matching_prefix(self):
        save_knopka_ai_key("sk-test-secret", prefix="sk-test-secr")
        clear_knopka_ai_key(prefix="sk-test-secr")
        data = json.loads(Path(self._tmp.name).read_text())
        self.assertNotIn("knopka_ai", data)

    def test_clear_skips_other_prefix(self):
        save_knopka_ai_key("sk-test-secret", prefix="sk-test-secr")
        clear_knopka_ai_key(prefix="sk-other")
        data = json.loads(Path(self._tmp.name).read_text())
        self.assertEqual(data["knopka_ai"]["key"], "sk-test-secret")


if __name__ == "__main__":
    unittest.main()
