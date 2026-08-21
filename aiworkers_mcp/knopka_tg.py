"""Userbot CRM behind api.knopka.click /tg/. Same LLM key as knopka_ai, own allowlist."""

from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import urlencode

import httpx

from aiworkers_mcp.http import KNOPKA_AI_BASE
from aiworkers_mcp.knopka_ai import (
    INFERENCE_TIMEOUT,
    _missing_knopka_ai_key,
    normalize_ai_path,
    resolve_knopka_ai_key,
)

_ACCOUNT_RE = re.compile(r"^[A-Za-z0-9_+\-.@%]+$")

_DENY_PREFIXES = (
    "/env",
    "/pm2",
    "/login",
    "/logout",
    "/update",
    "/api/tokens",
    "/accounts/import-session",
    "/accounts/start-all",
    "/accounts/stop-all",
)

_ALLOW_EXACT: dict[str, frozenset[str]] = {
    "/health": frozenset({"GET"}),
    "/accounts": frozenset({"GET"}),
    "/accounts/phone/check": frozenset({"POST"}),
    "/accounts/phone/check-batch": frozenset({"POST"}),
    "/accounts/login/start": frozenset({"POST"}),
    "/accounts/login/confirm": frozenset({"POST"}),
    "/accounts/login/password": frozenset({"POST"}),
    "/groups-channels": frozenset({"GET", "POST"}),
    "/groups-channels/sync": frozenset({"POST"}),
    "/messages": frozenset({"GET"}),
    "/messages/sync": frozenset({"POST"}),
    "/tasks": frozenset({"GET"}),
    "/tasks/batch": frozenset({"POST"}),
    "/api/records": frozenset({"GET"}),
    "/api/monitoring": frozenset({"GET", "POST"}),
}

_TASK_ACTIONS = frozenset({
    "send-message",
    "join-group",
    "leave-group",
    "create-channel",
    "create-bot",
})

_ACCOUNT_GET = re.compile(r"^/accounts/([^/]+)$")
_ACCOUNT_POWER = re.compile(r"^/accounts/([^/]+)/(start|stop)$")
_ACCOUNT_TASK = re.compile(r"^/accounts/([^/]+)/tasks/([^/]+)$")
_GROUPS_ITEM = re.compile(r"^/groups-channels/([^/]+)$")


def normalize_tg_path(path: str) -> str:
    normalized = normalize_ai_path(path)
    if normalized == "/tg":
        raise ValueError("path not allowed")
    if normalized.startswith("/tg/"):
        normalized = normalized[3:]
        if not normalized.startswith("/"):
            normalized = "/" + normalized
    if normalized in {"/", "/docs", "/redoc", "/openapi.json"}:
        raise ValueError("path not allowed")
    return normalized


def _account_ok(name: str) -> bool:
    return bool(name) and _ACCOUNT_RE.fullmatch(name) is not None and name not in {".", ".."}


def tg_path_allowed(method: str, path: str) -> bool:
    method_u = (method or "GET").strip().upper()
    if method_u not in {"GET", "POST", "PUT", "DELETE"}:
        return False
    try:
        normalized = normalize_tg_path(path)
    except ValueError:
        return False
    for deny in _DENY_PREFIXES:
        if deny.endswith("/"):
            if normalized == deny.rstrip("/") or normalized.startswith(deny):
                return False
        elif normalized == deny or normalized.startswith(deny + "/"):
            return False
    allowed_methods = _ALLOW_EXACT.get(normalized)
    if allowed_methods is not None:
        return method_u in allowed_methods
    match = _ACCOUNT_GET.fullmatch(normalized)
    if match and _account_ok(match.group(1)):
        return method_u == "GET"
    match = _ACCOUNT_POWER.fullmatch(normalized)
    if match and _account_ok(match.group(1)):
        return method_u == "POST"
    match = _ACCOUNT_TASK.fullmatch(normalized)
    if match and _account_ok(match.group(1)) and match.group(2) in _TASK_ACTIONS:
        return method_u == "POST"
    match = _GROUPS_ITEM.fullmatch(normalized)
    if match and match.group(1) not in {".", ".."}:
        return method_u in {"GET", "PUT", "DELETE"}
    return False


def account_segment(account: str) -> str:
    name = (account or "").strip()
    if not _account_ok(name):
        raise ValueError("invalid account")
    return name


def request_knopka_tg(
    method: str,
    path: str,
    json_body: Any = None,
    params: dict[str, Any] | None = None,
) -> Any:
    method_u = (method or "GET").strip().upper()
    if method_u not in {"GET", "POST", "PUT", "DELETE"}:
        raise ValueError("method must be GET, POST, PUT, or DELETE")
    if not tg_path_allowed(method_u, path):
        raise ValueError("path not allowed")
    key = resolve_knopka_ai_key()
    if not key:
        _missing_knopka_ai_key()
    crm_path = normalize_tg_path(path)
    url = f"{KNOPKA_AI_BASE}/tg{crm_path}"
    query: dict[str, str] = {}
    if params:
        for key_name, value in params.items():
            if value is None or value == "":
                continue
            query[str(key_name)] = str(value)
    if query:
        url = f"{url}?{urlencode(query)}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {key}",
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    timeout = float(os.getenv("AIWORKERS_TG_TIMEOUT") or INFERENCE_TIMEOUT)
    with httpx.Client(timeout=timeout, headers=headers, follow_redirects=False) as client:
        resp = client.request(method_u, url, json=json_body)
    location = (resp.headers.get("location") or "").lower()
    if resp.status_code in (301, 302, 303, 307, 308) and "/login" in location:
        raise RuntimeError(json.dumps({
            "success": False,
            "message": "tg crm returned login redirect; LLM key reached the proxy but CRM auth is missing",
            "status_code": 401,
        }, ensure_ascii=False))
    try:
        data = resp.json()
    except Exception:
        data = {"success": False, "message": resp.text[:500], "status_code": resp.status_code}
    if resp.status_code >= 400:
        if not isinstance(data, dict):
            data = {"success": False, "message": str(data)[:500], "status_code": resp.status_code}
        else:
            data.setdefault("status_code", resp.status_code)
        raise RuntimeError(json.dumps(data, ensure_ascii=False))
    return data
