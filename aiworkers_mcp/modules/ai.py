"""LLM keys and allowlisted requests to api.knopka.click."""

from __future__ import annotations

import json
from typing import Any

from aiworkers_mcp.http import request_ai
from aiworkers_mcp.knopka_ai import request_knopka_ai, resolve_knopka_ai_key
from aiworkers_mcp.login import (
    clear_knopka_ai_key,
    login_help,
    save_knopka_ai_key,
    save_knopka_ai_wallet_key,
)


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _call_ai(method: str, path: str, **kwargs: Any) -> str:
    try:
        return _dump(request_ai(method, path, **kwargs))
    except RuntimeError as exc:
        try:
            payload = json.loads(str(exc))
        except json.JSONDecodeError:
            raise
        if isinstance(payload, dict) and payload.get("status_code") in (400, 401, 403, 409, 429, 502, 503):
            return _dump(payload)
        raise


def _call_knopka(method: str, path: str, json_body: Any = None) -> str:
    try:
        return _dump(request_knopka_ai(method, path, json_body=json_body))
    except RuntimeError as exc:
        try:
            payload = json.loads(str(exc))
        except json.JSONDecodeError:
            raise
        if isinstance(payload, dict) and payload.get("status_code") in (400, 401, 403, 409, 429, 502, 503):
            return _dump(payload)
        raise


_ISSUE_DISABLED_HINT = (
    "выпуск новых ключей через MCP выключен человеком в Mini App; "
    "не обходить, попросить включить"
)

_WALLET_KEY_HINTS = {
    "wallet_reveal_disabled": (
        "попроси человека включить в Mini App: Ключи → Безопасность MCP (нужны 12 слов)"
    ),
    "wallet_mismatch": "кошелёк токена не совпадает с привязанным; не обходить, сообщи человеку",
    "reveal_rate_limited": "не повторяй до retry_after",
    "wallet_not_bound": "кошелёк не привязан; попроси человека привязать его в Mini App",
    "wallet_key_not_provisioned": "открой Mini App → Ключ для ИИ",
}


def _error_payload(exc: RuntimeError) -> dict | None:
    try:
        payload = json.loads(str(exc))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _need_parent() -> dict | None:
    from aiworkers_mcp.http import resolve_token

    if resolve_token():
        return None
    payload = login_help()
    payload["success"] = False
    payload["message"] = (
        "parent awp_ required to manage LLM keys. Open url, copy the token, then aiworkers-mcp login"
    )
    return payload


def register(mcp) -> None:
    @mcp.tool()
    def ai_keys_issue(save: bool = True, role: str = "", period: str = "", plan: str = "") -> str:
        """Buy and issue a user LLM key for api.knopka.click. Parent awp_ only. Key is shown once. save=true writes it to credentials.json knopka_ai so ai_chat / ai_request / tg_* work. Not an MCP awp_/awm_ token. role (default manager; roles from https://api.knopka.click/key/roles: sales, content, marketer, manager) and period (week|month|year|100d, default month) pick the employee; plan (plan id, REQUIRED for roles sold by subscription plans such as chatgpt/claude/gemini/perplexity/grok/mistral/copilot/deepseek; ids and prices are in the roles catalog) picks the tariff; the price (plan price for the period, or default_salary_budget x days/30 for plain roles; free plans cost nothing) is charged from the agent balance — 402 insufficient_agent_balance if it is too low."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        try:
            body: dict[str, Any] = {}
            if role.strip():
                body["role"] = role.strip()
            if period.strip():
                body["period"] = period.strip()
            if plan.strip():
                body["plan"] = plan.strip()
            data = request_ai("POST", "/api/mcp/ai-keys/issue", json=body)
        except RuntimeError as e:
            payload = _error_payload(e)
            if payload is None:
                return str(e)
            if payload.get("code") == "mcp_key_issue_disabled":
                payload["hint"] = _ISSUE_DISABLED_HINT
            return _dump(payload)
        if not isinstance(data, dict):
            data = {"raw": data}
        secret = str(data.get("key") or "").strip()
        if save and secret:
            path = save_knopka_ai_key(
                secret,
                alias=str(data.get("key_alias") or ""),
                prefix=str(data.get("prefix") or ""),
            )
            data["saved"] = str(path)
        data["restart_hint"] = (
            "LLM key is in credentials.json knopka_ai. Next ai_chat / ai_request / tg_* use it. "
            "Tell the human prefix + alias; do not dump the full secret unless they need it elsewhere. "
            "Do not commit the key."
        )
        return _dump(data)

    @mcp.tool()
    def ai_keys_wallet_key(
        reveal: bool = False,
        save: bool = True,
        use_as_default: bool = False,
        reason: str = "",
    ) -> str:
        """Main (root/contract) api.knopka.click key of the bound wallet. Parent awp_ only. DISABLED by default: the human must enable it in the Mini App (Ключи → Безопасность MCP, needs the 12 words). Every call is audited and the human gets a Telegram alert. Rate-limited to 5/h. This key spends the WHOLE wallet budget and revoking awp_ does NOT revoke it. reveal=false (default) never returns the secret to the model: it is only saved locally (save=true) to credentials.json knopka_ai_wallet. use_as_default=true also copies it to knopka_ai (old value moves to knopka_ai_prev). reveal=true returns the secret: only if the human asked to use it on another machine; never print it in chat or commit it. Tell the human prefix + alias only. reason is logged in the audit (max 200 chars)."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        if not save and not reveal:
            return _dump({
                "success": False,
                "message": "nothing to do: save=false and reveal=false would fetch the key and discard it. Use save=true and/or reveal=true.",
            })
        body: dict[str, Any] = {"reason": reason.strip()[:200]} if reason and reason.strip() else {}
        try:
            data = request_ai("POST", "/api/mcp/ai-keys/wallet/key", json=body)
        except RuntimeError as e:
            payload = _error_payload(e)
            if payload is None:
                return str(e)
            hint = _WALLET_KEY_HINTS.get(str(payload.get("code") or ""))
            if not hint and "parent token required" in str(payload.get("message") or "").lower():
                hint = "нужен родительский awp_ токен (aiworkers_login_link)"
            if hint:
                payload["hint"] = hint
            return _dump(payload)
        if not isinstance(data, dict):
            data = {"raw": data}
        secret = str(data.get("key") or "").strip()
        if save and secret:
            path = save_knopka_ai_wallet_key(
                secret,
                alias=str(data.get("key_alias") or ""),
                prefix=str(data.get("prefix") or ""),
                eth_address=str(data.get("eth_address") or ""),
                as_default=use_as_default,
            )
            data["saved"] = str(path)
            data["saved_as_default"] = bool(use_as_default)
        else:
            data["saved"] = None
        if not reveal:
            data.pop("key", None)
        data["instruction"] = (
            "Do NOT print or commit the key. Tell the human only prefix + key_alias. "
            "Key is in credentials.json knopka_ai_wallet."
            if not reveal
            else "Key returned because reveal=true. Do NOT print it in chat or commit it; "
            "pass it only where the human asked. Tell the human only prefix + key_alias."
        )
        return _dump(data)

    @mcp.tool()
    def ai_keys_list() -> str:
        """List this user's api.knopka.click keys (prefix + alias, no full secret). Parent awp_ only."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        return _call_ai("GET", "/api/mcp/ai-keys")

    @mcp.tool()
    def ai_keys_revoke(key: str = "", prefix: str = "", issued_at: str = "") -> str:
        """Revoke a user LLM key. Parent awp_ only. Pass the full key, or prefix + issued_at from ai_keys_list."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        body: dict[str, Any] = {}
        secret = (key or "").strip()
        if not secret and not prefix.strip() and not str(issued_at).strip():
            secret = resolve_knopka_ai_key()
        if secret:
            body["key"] = secret
        if prefix.strip():
            body["prefix"] = prefix.strip()
        if str(issued_at).strip():
            try:
                body["issued_at"] = int(str(issued_at).strip())
            except ValueError:
                body["issued_at"] = issued_at
        try:
            data = request_ai("POST", "/api/mcp/ai-keys/revoke", json=body)
        except RuntimeError as e:
            return str(e)
        if not isinstance(data, dict):
            data = {"raw": data}
        clear_knopka_ai_key(prefix=str(data.get("prefix") or prefix), key=secret)
        return _dump(data)

    @mcp.tool()
    def ai_keys_rename(alias: str, key: str = "", prefix: str = "", issued_at: str = "") -> str:
        """Rename the local display alias of a user LLM key. Parent awp_ only. Does not change the LiteLLM user id."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        body: dict[str, Any] = {"alias": alias}
        secret = (key or "").strip()
        if not secret and not prefix.strip() and not str(issued_at).strip():
            secret = resolve_knopka_ai_key()
        if secret:
            body["key"] = secret
        if prefix.strip():
            body["prefix"] = prefix.strip()
        if str(issued_at).strip():
            try:
                body["issued_at"] = int(str(issued_at).strip())
            except ValueError:
                body["issued_at"] = issued_at
        return _call_ai("POST", "/api/mcp/ai-keys/rename", json=body)

    @mcp.tool()
    def ai_keys_wallet_info() -> str:
        """Agent wallet: personal balance (USD) vs agent LLM-key budget (max_budget/spend). Parent awp_ only."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        return _call_ai("GET", "/api/mcp/ai-keys/wallet/info")

    @mcp.tool()
    def ai_keys_wallet_topup_request(amount_usd: float) -> str:
        """Request moving amount_usd from the human's personal balance into THIS agent's LLM-key budget. Does not move money by itself — sends a Telegram confirm/decline prompt to the human; poll ai_keys_wallet_status for the result. Parent awp_ only."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        return _call_ai("POST", "/api/mcp/ai-keys/wallet/topup-request", json={"amount_usd": amount_usd})

    @mcp.tool()
    def ai_keys_wallet_status() -> str:
        """Status of the last wallet transfer (processing/done/failed/none) for this agent. Parent awp_ only."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        return _call_ai("GET", "/api/mcp/ai-keys/wallet/status")

    @mcp.tool()
    def ai_keys_wallet_withdraw(amount_usd: float) -> str:
        """Move amount_usd from THIS agent's LLM-key budget back to the human's personal balance. Executes immediately, no human confirmation needed (money only returns to the human). Parent awp_ only."""
        missing = _need_parent()
        if missing:
            return _dump(missing)
        return _call_ai("POST", "/api/mcp/ai-keys/wallet/withdraw", json={"amount_usd": amount_usd})

    @mcp.tool()
    def ai_models() -> str:
        """List models on api.knopka.click (GET /v1/models). Needs a saved LLM key (ai_keys_issue)."""
        return _call_knopka("GET", "/v1/models")

    @mcp.tool()
    def ai_chat(model: str, messages_json: str, extra_json: str = "") -> str:
        """POST /v1/chat/completions on api.knopka.click. messages_json is a JSON array of {role, content}. extra_json merges extra OpenAI fields. stream is always false."""
        try:
            messages = json.loads(messages_json or "[]")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid messages_json: {e}") from e
        if not isinstance(messages, list):
            raise ValueError("messages_json must be a JSON array")
        body: dict[str, Any] = {"model": model, "messages": messages, "stream": False}
        extra_raw = (extra_json or "").strip()
        if extra_raw:
            try:
                extra = json.loads(extra_raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid extra_json: {e}") from e
            if not isinstance(extra, dict):
                raise ValueError("extra_json must be a JSON object")
            extra.pop("stream", None)
            body.update(extra)
            body["model"] = model
            body["messages"] = messages
            body["stream"] = False
        return _call_knopka("POST", "/v1/chat/completions", json_body=body)

    @mcp.tool()
    def ai_request(method: str, path: str, body_json: str = "") -> str:
        """Call an allowlisted api.knopka.click path with the saved LLM key. OpenAI-compatible and custom inference (cursor, videos, rag, anthropic). Admin LiteLLM and /tg/ are rejected. JSON body only; stream forced false. Userbot CRM is tg_request / tg_*."""
        payload = None
        raw = (body_json or "").strip()
        if raw:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(f"invalid body_json: {e}") from e
        try:
            return _call_knopka(method, path, json_body=payload)
        except ValueError as e:
            return _dump({"success": False, "message": str(e), "status_code": 400})
