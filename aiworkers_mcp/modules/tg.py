"""Telegram userbot accounts via api.knopka.click /tg/. Not telegram_* (pm2 worker bot)."""

from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote

from aiworkers_mcp.knopka_tg import account_segment, request_knopka_tg


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _call_tg(
    method: str,
    path: str,
    json_body: Any = None,
    params: dict[str, Any] | None = None,
) -> str:
    try:
        return _dump(request_knopka_tg(method, path, json_body=json_body, params=params))
    except RuntimeError as exc:
        try:
            payload = json.loads(str(exc))
        except json.JSONDecodeError:
            raise
        if isinstance(payload, dict) and payload.get("status_code") in (
            400, 401, 403, 404, 409, 429, 500, 502, 503,
        ):
            return _dump(payload)
        raise
    except ValueError as exc:
        return _dump({"success": False, "message": str(exc), "status_code": 400})


def _account_path(account: str, suffix: str = "") -> str:
    name = quote(account_segment(account), safe="+@.-_")
    return f"/accounts/{name}{suffix}"


def _optional_json(raw: str) -> Any:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON: {exc}") from exc


def register(mcp) -> None:
    @mcp.tool()
    def tg_health() -> str:
        """GET /tg/health on api.knopka.click. Userbot CRM ping + account names. Needs the LLM key (ai_keys_issue), not telegram_*."""
        return _call_tg("GET", "/health")

    @mcp.tool()
    def tg_accounts_list(sync: bool = False) -> str:
        """List userbot Telegram accounts (status, me). sync=true also refreshes groups. LLM key. Not telegram_status."""
        return _call_tg("GET", "/accounts", params={"sync": "1" if sync else "0"})

    @mcp.tool()
    def tg_account_get(account: str) -> str:
        """GET one userbot account by CRM name (often the phone). LLM key."""
        return _call_tg("GET", _account_path(account))

    @mcp.tool()
    def tg_account_start(account: str) -> str:
        """Start the userbot process for one CRM account. LLM key. Not telegram_restart (that is aibot-<username>)."""
        return _call_tg("POST", _account_path(account, "/start"))

    @mcp.tool()
    def tg_account_stop(account: str) -> str:
        """Stop the userbot process for one CRM account. LLM key."""
        return _call_tg("POST", _account_path(account, "/stop"))

    @mcp.tool()
    def tg_channel_create(
        account: str,
        title: str,
        description: str = "",
        username: str = "",
    ) -> str:
        """Create a Telegram channel/supergroup from a userbot account. title required. username without @ if public. LLM key. This hits Telegram for real."""
        body: dict[str, Any] = {"title": title, "description": description or ""}
        if (username or "").strip():
            body["username"] = username.strip().lstrip("@")
        return _call_tg("POST", _account_path(account, "/tasks/create-channel"), json_body=body)

    @mcp.tool()
    def tg_bot_create(account: str, bot_name: str, bot_username: str) -> str:
        """Create a bot via BotFather from a userbot account. bot_username must end with 'bot'. LLM key. Returns bot token from CRM — tell the human, do not commit it."""
        return _call_tg(
            "POST",
            _account_path(account, "/tasks/create-bot"),
            json_body={"name": bot_name, "username": bot_username},
        )

    @mcp.tool()
    def tg_send_message(
        account: str,
        chat: str,
        text: str,
        parse_mode: str = "",
        reply_to: str = "",
        disable_web_page_preview: bool = False,
    ) -> str:
        """Send a message from a userbot account to chat (id, @username, or invite link). LLM key. Not workers_chat_send."""
        body: dict[str, Any] = {"chat": chat, "text": text}
        if (parse_mode or "").strip():
            body["parse_mode"] = parse_mode.strip()
        if (reply_to or "").strip():
            body["reply_to_message_id"] = reply_to.strip()
        if disable_web_page_preview:
            body["disable_web_page_preview"] = True
        return _call_tg("POST", _account_path(account, "/tasks/send-message"), json_body=body)

    @mcp.tool()
    def tg_join_group(account: str, chat: str) -> str:
        """Join a group/channel from a userbot account. chat = id, @username, or invite link. LLM key."""
        return _call_tg(
            "POST",
            _account_path(account, "/tasks/join-group"),
            json_body={"chat": chat},
        )

    @mcp.tool()
    def tg_leave_group(account: str, chat: str) -> str:
        """Leave a group/channel from a userbot account. LLM key."""
        return _call_tg(
            "POST",
            _account_path(account, "/tasks/leave-group"),
            json_body={"chat": chat},
        )

    @mcp.tool()
    def tg_groups_list(
        account: str = "",
        limit: int = 100,
        offset: int = 0,
        name: str = "",
        link: str = "",
    ) -> str:
        """List cached groups/channels for userbot accounts. Optional filters. LLM key."""
        params: dict[str, Any] = {
            "limit": max(1, min(int(limit), 2000)),
            "offset": max(0, int(offset)),
        }
        if (account or "").strip():
            params["account"] = account.strip()
        if (name or "").strip():
            params["name"] = name.strip()
        if (link or "").strip():
            params["link"] = link.strip()
        return _call_tg("GET", "/groups-channels", params=params)

    @mcp.tool()
    def tg_tasks_list() -> str:
        """List recent userbot CRM tasks (create channel/bot, send, join). LLM key. Not tasks_* (group todos)."""
        return _call_tg("GET", "/tasks")

    @mcp.tool()
    def tg_phone_check(phone: str, account: str = "", force: bool = False) -> str:
        """Check whether a phone has Telegram, using a userbot account. LLM key."""
        body: dict[str, Any] = {"phone": phone, "force": bool(force)}
        if (account or "").strip():
            body["account"] = account.strip()
        return _call_tg("POST", "/accounts/phone/check", json_body=body)

    @mcp.tool()
    def tg_login_start(phone: str) -> str:
        """Start adding a userbot account: send the Telegram login code to this phone. LLM key. Then tg_login_confirm."""
        return _call_tg("POST", "/accounts/login/start", json_body={"phone": phone})

    @mcp.tool()
    def tg_login_confirm(phone: str, code: str) -> str:
        """Confirm userbot login with the SMS/Telegram code from tg_login_start. LLM key."""
        return _call_tg(
            "POST",
            "/accounts/login/confirm",
            json_body={"phone": phone, "code": code},
        )

    @mcp.tool()
    def tg_login_password(phone: str, password: str) -> str:
        """Submit Telegram 2FA cloud password after tg_login_confirm. LLM key. Do not log the password."""
        return _call_tg(
            "POST",
            "/accounts/login/password",
            json_body={"phone": phone, "password": password},
        )

    @mcp.tool()
    def tg_request(method: str, path: str, body_json: str = "") -> str:
        """Call an allowlisted /tg/ CRM path with the LLM key. Path is CRM-relative (/accounts, /tg/accounts, …). Denied: /env, /pm2, /login, /api/tokens, import-session, start-all/stop-all. Prefer named tg_* tools. Not ai_request."""
        payload = _optional_json(body_json)
        return _call_tg(method, path, json_body=payload)
