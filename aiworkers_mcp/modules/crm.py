"""Booking CRM (book.knopka.click) via /api/mcp/crm. Not admin CRM dialogs."""

from __future__ import annotations

import json
from typing import Any

from aiworkers_mcp.http import request_ai as _request_ai, require_group_id as _require_group_id


def request_ai(method: str, path: str, **kwargs: Any):
    kwargs.setdefault("module", "crm")
    return _request_ai(method, path, **kwargs)


def require_group_id(group_id: str = ""):
    return _require_group_id(group_id, module="crm")


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def register(mcp) -> None:
    @mcp.tool()
    def crm_context(group_id: str = "", username: str = "") -> str:
        """Resolve Booking CRM context: employees, cal_link, Telegram group and topic keys."""
        params: dict[str, Any] = {}
        gid = (group_id or "").strip()
        uname = (username or "").strip()
        if gid:
            params["group_id"] = require_group_id(gid)
        if uname:
            params["username"] = uname.lstrip("@")
        if not params:
            params["group_id"] = require_group_id("")
        return _dump(request_ai("GET", "/api/mcp/crm/context", params=params))

    @mcp.tool()
    def crm_process(payload_json: str, group_id: str = "") -> str:
        """Create/update/cancel a booking. payload_json: {action, event}. Tool group_id is enough. Create with start/end books cal.diy (blocks the public slot) and posts the group card — do not also tasks_create a hold."""
        try:
            body = json.loads(payload_json or "{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid payload_json: {e}") from e
        if not isinstance(body, dict):
            raise ValueError("payload_json must be an object")
        gid = (group_id or "").strip()
        if gid:
            gid = require_group_id(gid)
            body.setdefault("group_id", gid)
            body.setdefault("defaultGroupId", gid)
            event = body.get("event") if isinstance(body.get("event"), dict) else {}
            if event:
                event.setdefault("defaultGroupId", gid)
                body["event"] = event
        elif "group_id" not in body and "defaultGroupId" not in body:
            body["group_id"] = require_group_id("")
            body.setdefault("defaultGroupId", body["group_id"])
        return _dump(request_ai("POST", "/api/mcp/crm", json=body))
