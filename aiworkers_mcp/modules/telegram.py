"""Telegram bot status and commands. No message sending."""

from __future__ import annotations

import json
from aiworkers_mcp.http import request_ai as _request_ai, require_group_id as _require_group_id


def request_ai(method, path, **kwargs):
    kwargs.setdefault("module", "telegram")
    return _request_ai(method, path, **kwargs)


def require_group_id(group_id: str = ""):
    return _require_group_id(group_id, module="telegram")


def _dump(data) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def register(mcp) -> None:
    @mcp.tool()
    def telegram_status(group_id: str = "") -> str:
        """Bot connection status (username/id, no token). Does not send messages."""
        gid = require_group_id(group_id)
        return _dump(request_ai("GET", f"/api/mcp/telegram/{gid}/status"))

    @mcp.tool()
    def telegram_commands_get(group_id: str = "") -> str:
        """Read bot command menu (segments + translations). Does not send messages."""
        gid = require_group_id(group_id)
        return _dump(request_ai("GET", f"/api/mcp/telegram/{gid}/commands"))

    @mcp.tool()
    def telegram_commands_save(commands_json: str, group_id: str = "") -> str:
        """Save bot commands. JSON: builtin/custom/segments/translations. Syncs Bot API menu, no chats."""
        try:
            payload = json.loads(commands_json or "{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid commands_json: {e}") from e
        if not isinstance(payload, dict):
            raise ValueError("commands_json must be an object")
        gid = require_group_id(group_id)
        return _dump(request_ai("POST", f"/api/mcp/telegram/{gid}/commands", json=payload))

    @mcp.tool()
    def telegram_restart(group_id: str = "") -> str:
        """Restart this group's Telegram worker process (pm2 aibot-<username>). Same as /telegram_bot «Перезапустить скрипт». Rate-limited (60s per bot); on 429 wait retry_after, do not loop. Use when the user asks to restart the bot — not workers_update. Does not send messages."""
        gid = require_group_id(group_id)
        try:
            return _dump(request_ai("POST", f"/api/mcp/telegram/{gid}/restart"))
        except RuntimeError as exc:
            try:
                payload = json.loads(str(exc))
            except json.JSONDecodeError:
                raise
            if not isinstance(payload, dict):
                raise
            wait = payload.get("retry_after")
            if payload.get("status_code") == 429 or wait:
                return _dump({
                    "success": False,
                    "rate_limited": True,
                    "retry_after": wait,
                    "message": payload.get("message") or f"wait {wait}s before restarting again",
                })
            raise
