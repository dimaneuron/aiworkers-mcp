"""Client-side module alias lookup."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aiworkers_mcp.module_names import (
    canonicalize_module,
    credential_module_names,
    expand_enabled_modules,
)


class ClientModuleNamesTests(unittest.TestCase):
    def test_credential_lookup_does_not_borrow_sibling(self):
        self.assertEqual(credential_module_names("tasks")[0], "tasks")
        self.assertNotIn("crm", credential_module_names("tasks"))
        self.assertNotIn("surveys", credential_module_names("crm"))
        self.assertEqual(credential_module_names("crm")[0], "crm")
        self.assertIn("booking", credential_module_names("tasks"))
        self.assertIn("booking", credential_module_names("crm"))
        self.assertNotIn("tasks", credential_module_names("booking"))
        self.assertNotIn("crm", credential_module_names("booking"))

    def test_book_calendar_expand_to_task_tools(self):
        self.assertEqual(canonicalize_module("book"), "booking")
        self.assertEqual(canonicalize_module("calendar"), "booking")
        self.assertEqual(expand_enabled_modules({"book"}), {"tasks", "crm"})
        self.assertEqual(expand_enabled_modules({"calendar"}), {"tasks", "crm"})
        self.assertIn("surveys", expand_enabled_modules({"surveys", "booking"}))


if __name__ == "__main__":
    unittest.main()
