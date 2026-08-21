"""Worker card, memory, chats, ready replies — HTTP to /api/mcp/*."""

from __future__ import annotations

import json
from typing import Any

from aiworkers_mcp.http import request_ai as _request_ai, require_group_id as _require_group_id


def request_ai(method: str, path: str, **kwargs: Any):
    kwargs.setdefault("module", "workers")
    return _request_ai(method, path, **kwargs)


def require_group_id(group_id: str = ""):
    return _require_group_id(group_id, module="workers")


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _call(method: str, path: str, **kwargs: Any) -> str:
    try:
        return _dump(request_ai(method, path, **kwargs))
    except RuntimeError as exc:
        try:
            payload = json.loads(str(exc))
        except json.JSONDecodeError:
            raise
        if isinstance(payload, dict) and payload.get("status_code") in (400, 403, 409, 429):
            return _dump(payload)
        raise


def _need_group(group_id: str = "") -> str:
    try:
        return require_group_id(group_id)
    except ValueError:
        raise ValueError("нужен group_id") from None


def register(mcp) -> None:
    @mcp.tool()
    def workers_list() -> str:
        """List workers this key can access. Each row has group tt/usd/stars. Root account is the shared USD wallet once. For one group use workers_balance."""
        return _call("GET", "/api/mcp/workers")

    @mcp.tool()
    def workers_get(group_id: str = "") -> str:
        """Read the worker card (no bot tokens). For money prefer workers_balance."""
        gid = require_group_id(group_id)
        return _call("GET", f"/api/mcp/workers/{gid}")

    @mcp.tool()
    def workers_update(group_id: str = "", patch_json: str = "{}") -> str:
        """Update worker fields: status, lang, paid_until, translate_langs. Never write tt here — use workers_salary_quote or workers_tt_buy_quote."""
        try:
            patch = json.loads(patch_json or "{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid patch_json: {e}") from e
        if not isinstance(patch, dict):
            raise ValueError("patch_json must be an object")
        if "tt" in patch:
            raise ValueError(
                "do not write tt via workers_update; use workers_salary_quote or workers_tt_buy_quote"
            )
        gid = require_group_id(group_id)
        return _call("POST", f"/api/mcp/workers/{gid}", json=patch)

    @mcp.tool()
    def workers_balance(group_id: str = "") -> str:
        """Two layers: account.usd (shared wallet) and group.tt (TokenTime). Empty group_id uses credentials / AIWORKERS_GROUP_ID, else «нужен group_id». Does not charge."""
        gid = _need_group(group_id)
        return _call("GET", f"/api/mcp/workers/{gid}/balance")

    @mcp.tool()
    def workers_topup_link(group_id: str = "", amount_usd: float | None = None) -> str:
        """URL to top up the ACCOUNT wallet in @aiworkersbot (users.balance). Does not credit group tt. No tt_credit. If amount_usd omitted: ask_amount=true and start=addBalance. If set: start=addBalance_10 (integer USD); bot shows Change amount. Dot in start payload is invalid."""
        gid = _need_group(group_id)
        params = {}
        if amount_usd is not None:
            params["amount_usd"] = amount_usd
        return _call("GET", f"/api/mcp/workers/{gid}/topup_link", params=params)

    @mcp.tool()
    def workers_salary_quote(add_usd: int, group_id: str = "") -> str:
        """Preview raising YOUR contribution by whole USD. Debits account, adds add_usd*3600 tt, raises solary. Does not charge until workers_salary_confirm(quote_id, confirm=true). Other admins can raise their own share."""
        gid = _need_group(group_id)
        return _call("POST", f"/api/mcp/workers/{gid}/salary/quote", json={"add_usd": add_usd})

    @mcp.tool()
    def workers_salary_confirm(quote_id: str, confirm: bool = False, group_id: str = "") -> str:
        """Charge a salary quote. confirm must be true. Quote lives ~5 min; reuse is 409. Cannot decrease contribution (write @dimaneuron)."""
        gid = _need_group(group_id)
        return _call(
            "POST",
            f"/api/mcp/workers/{gid}/salary/confirm",
            json={"quote_id": quote_id, "confirm": confirm},
        )

    @mcp.tool()
    def workers_tt_buy_quote(
        group_id: str = "",
        amount_usd: float | None = None,
        tt: float | None = None,
    ) -> str:
        """Preview one-time tt buy at 10x subscription ($10 → 3600 tt). Does not change solary. Pass amount_usd or tt. Does not charge until workers_tt_buy_confirm."""
        gid = _need_group(group_id)
        body: dict[str, Any] = {}
        if amount_usd is not None:
            body["amount_usd"] = amount_usd
        if tt is not None:
            body["tt"] = tt
        return _call("POST", f"/api/mcp/workers/{gid}/tt/quote", json=body)

    @mcp.tool()
    def workers_tt_buy_confirm(quote_id: str, confirm: bool = False, group_id: str = "") -> str:
        """Charge a one-time tt quote. confirm must be true. Quote lives ~5 min; reuse is 409. solary unchanged."""
        gid = _need_group(group_id)
        return _call(
            "POST",
            f"/api/mcp/workers/{gid}/tt/confirm",
            json={"quote_id": quote_id, "confirm": confirm},
        )

    @mcp.tool()
    def workers_partner() -> str:
        """Platform partner terms, catalog/builder/community URLs, ref_link. rates is a constants dict — do not invent percents if empty. Not the worker-bot /ref product."""
        return _call("GET", "/api/mcp/workers/partner")

    @mcp.tool()
    def workers_memory_get(group_id: str = "", topic: str = "") -> str:
        """Read memory topics and entries. Optional topic=topic_<id>."""
        gid = require_group_id(group_id)
        params: dict[str, Any] = {}
        if topic:
            params["topic"] = topic
        return _dump(request_ai("GET", f"/api/mcp/workers/{gid}/memory", params=params))

    @mcp.tool()
    def workers_memory_add(content: str, group_id: str = "", topic: str = "") -> str:
        """Add a memory entry to a topic (topic_*)."""
        gid = require_group_id(group_id)
        if not topic:
            raise ValueError("topic is required")
        return _dump(
            request_ai(
                "POST",
                f"/api/mcp/workers/{gid}/memory",
                json={"action": "add", "memory_topic": topic, "content": content},
            )
        )

    @mcp.tool()
    def workers_memory_edit(
        message_id: str, content: str, group_id: str = "", topic: str = ""
    ) -> str:
        """Edit a memory entry by message_id."""
        gid = require_group_id(group_id)
        if not topic:
            raise ValueError("topic is required")
        return _dump(
            request_ai(
                "POST",
                f"/api/mcp/workers/{gid}/memory",
                json={
                    "action": "edit",
                    "memory_topic": topic,
                    "message_id": message_id,
                    "content": content,
                },
            )
        )

    @mcp.tool()
    def workers_memory_delete(message_id: str, group_id: str = "", topic: str = "") -> str:
        """Delete a memory entry by message_id."""
        gid = require_group_id(group_id)
        if not topic:
            raise ValueError("topic is required")
        return _dump(
            request_ai(
                "POST",
                f"/api/mcp/workers/{gid}/memory",
                json={
                    "action": "delete",
                    "memory_topic": topic,
                    "message_id": message_id,
                },
            )
        )

    @mcp.tool()
    def workers_memory_create_topic(name: str = "", group_id: str = "") -> str:
        """Create a new memory forum topic."""
        gid = require_group_id(group_id)
        return _dump(
            request_ai(
                "POST",
                f"/api/mcp/workers/{gid}/memory",
                json={"action": "create_topic", "name": name},
            )
        )

    @mcp.tool()
    def workers_chats_list(group_id: str = "", limit: int = 100) -> str:
        """List user chats (no message logs)."""
        gid = require_group_id(group_id)
        return _dump(
            request_ai("GET", f"/api/mcp/workers/{gid}/chats", params={"limit": limit})
        )

    @mcp.tool()
    def workers_chats_get(user_id: str, group_id: str = "") -> str:
        """Get one user chat card (no message logs)."""
        gid = require_group_id(group_id)
        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id is required")
        return _dump(
            request_ai("GET", f"/api/mcp/workers/{gid}/chats", params={"user_id": uid})
        )

    @mcp.tool()
    def workers_chat_send(
        user_id: str,
        text: str = "",
        rr_id: str = "",
        channel: str = "auto",
        group_id: str = "",
    ) -> str:
        """Send one message to a known chat from workers_chats_list. channel=auto|bot|embed|topic (auto: bot DM, or embed outbox for widget users). Mirrors into the user's forum topic. Need text and/or rr_id. Does not send to arbitrary Telegram ids. Rate-limited."""
        gid = require_group_id(group_id)
        uid = (user_id or "").strip()
        if not uid:
            raise ValueError("user_id is required")
        body: dict[str, Any] = {"user_id": uid, "channel": channel or "auto"}
        if text:
            body["text"] = text
        if rr_id:
            body["rr_id"] = rr_id
        return _call("POST", f"/api/mcp/workers/{gid}/chats/send", json=body)

    @mcp.tool()
    def workers_broadcast_quote(rr_id: str, group_id: str = "") -> str:
        """Preview a one-shot DM blast of a ready reply to everyone who already wrote this worker bot. Does not send until workers_broadcast_confirm(quote_id, confirm=true). Not widget, not folders, not arbitrary ids."""
        gid = require_group_id(group_id)
        rid = (rr_id or "").strip()
        if not rid:
            raise ValueError("rr_id is required")
        return _call("POST", f"/api/mcp/workers/{gid}/broadcast/quote", json={"rr_id": rid})

    @mcp.tool()
    def workers_broadcast_confirm(quote_id: str, confirm: bool = False, group_id: str = "") -> str:
        """Start the quoted bot-user blast. confirm must be true. Quote lives ~5 min; reuse 409. Status goes to the mailing topic."""
        gid = require_group_id(group_id)
        qid = (quote_id or "").strip()
        if not qid:
            raise ValueError("quote_id is required")
        return _call(
            "POST",
            f"/api/mcp/workers/{gid}/broadcast/confirm",
            json={"quote_id": qid, "confirm": confirm},
        )

    @mcp.tool()
    def workers_readyreply_list(group_id: str = "", rr_id: str = "") -> str:
        """List ready replies, or one item if rr_id is set."""
        gid = require_group_id(group_id)
        params: dict[str, Any] = {}
        if rr_id:
            params["rr_id"] = rr_id
        return _dump(request_ai("GET", f"/api/mcp/workers/{gid}/readyreply", params=params))

    @mcp.tool()
    def workers_readyreply_upsert(item_json: str, group_id: str = "", rr_id: str = "") -> str:
        """Create or update a ready reply. Posts the donor into the native ready-reply Telegram topic (P{message_id} + customization button). item_json: text/triggers/caption/buttons/topic_name."""
        try:
            item = json.loads(item_json or "{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid item_json: {e}") from e
        if not isinstance(item, dict):
            raise ValueError("item_json must be an object")
        gid = require_group_id(group_id)
        payload = {"action": "upsert", **item}
        if rr_id:
            payload["rr_id"] = rr_id
        return _dump(request_ai("POST", f"/api/mcp/workers/{gid}/readyreply", json=payload))

    @mcp.tool()
    def workers_readyreply_delete(rr_id: str, group_id: str = "") -> str:
        """Delete a ready reply by id."""
        gid = require_group_id(group_id)
        rid = (rr_id or "").strip()
        if not rid:
            raise ValueError("rr_id is required")
        return _dump(
            request_ai(
                "POST",
                f"/api/mcp/workers/{gid}/readyreply",
                json={"action": "delete", "rr_id": rid},
            )
        )

    @mcp.tool()
    def workers_readyreply_create_topic(name: str = "", group_id: str = "") -> str:
        """Create a Telegram topic for ready replies."""
        gid = require_group_id(group_id)
        return _dump(
            request_ai(
                "POST",
                f"/api/mcp/workers/{gid}/readyreply",
                json={"action": "create_topic", "name": name},
            )
        )
