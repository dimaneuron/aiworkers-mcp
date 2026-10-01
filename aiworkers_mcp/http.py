"""Shared HTTP client for AIWorkers private REST APIs."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

import httpx

from aiworkers_mcp.module_names import (
    credential_module_names,
    expand_enabled_modules,
)

API_BASE = (
    os.getenv("AIWORKERS_API_BASE")
    or os.getenv("SURVEY_API_BASE")
    or "https://ai.knopka.click"
).rstrip("/")

BOOKING_BASE = (
    os.getenv("AIWORKERS_BOOKING_BASE")
    or os.getenv("TASKS_API_BASE")
    or os.getenv("BOOKING_API_BASE")
    or "https://book.knopka.click/booking"
).rstrip("/")

KNOPKA_AI_BASE = (
    os.getenv("AIWORKERS_KNOPKA_AI_BASE") or "https://api.knopka.click"
).rstrip("/")

INTERNAL_SECRET = (
    os.getenv("BOOKING_INTERNAL_SECRET") or os.getenv("AIWORKERS_CRM_SECRET") or ""
).strip()

DEFAULT_GROUP_ID = (
    os.getenv("AIWORKERS_GROUP_ID") or os.getenv("TASKS_GROUP_ID") or ""
).strip()

LOGIN_TELEGRAM_URL = (
    os.getenv("AIWORKERS_LOGIN_URL") or "https://t.me/aiworkersbot?start=mcp"
).strip()

_MODULE_ENV = {
    "surveys": "AIWORKERS_KEY_SURVEYS",
    "tasks": "AIWORKERS_KEY_TASKS",
    "workers": "AIWORKERS_KEY_WORKERS",
    "telegram": "AIWORKERS_KEY_TELEGRAM",
    "crm": "AIWORKERS_KEY_CRM",
    "booking": "AIWORKERS_KEY_BOOKING",
    "book": "AIWORKERS_KEY_BOOK",
    "calendar": "AIWORKERS_KEY_CALENDAR",
}

DEFAULT_MODULES = "surveys,tasks,workers,telegram,crm"


def credentials_path() -> Path:
    raw = (os.getenv("AIWORKERS_CREDENTIALS") or "").strip()
    if raw:
        return Path(raw).expanduser()
    return Path.home() / ".config" / "aiworkers" / "credentials.json"


def load_credentials() -> dict:
    path = credentials_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def save_credentials(data: dict) -> Path:
    path = credentials_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def _token_from_row(row: Any) -> str:
    if isinstance(row, str):
        return row.strip()
    if isinstance(row, dict):
        return str(row.get("token") or row.get("key") or "").strip()
    return ""


def _group_from_row(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("group_id") or "").strip()
    return ""


def _generic_or_parent_token() -> str:
    env_key = (
        os.getenv("AIWORKERS_API_KEY")
        or os.getenv("SURVEY_MCP_API_KEY")
        or os.getenv("TASKS_MCP_API_KEY")
        or os.getenv("AIWORKERS_SURVEY_API_KEY")
        or ""
    ).strip()
    if env_key:
        return env_key
    cred = load_credentials()
    parent = str(cred.get("parent") or "").strip()
    if parent:
        return parent
    return ""


def _groups_match(bound: str, wanted: str) -> bool:
    if not wanted:
        return True
    if not bound:
        return False
    return bound.strip() == wanted.strip()


def _iter_module_candidates(module: Optional[str]):
    cred = load_credentials()
    keys = cred.get("keys") if isinstance(cred.get("keys"), dict) else {}
    for name in credential_module_names(module or ""):
        env_name = _MODULE_ENV.get(name)
        if env_name:
            tok = (os.getenv(env_name) or "").strip()
            if tok:
                yield tok, ""
        tok = _token_from_row(keys.get(name))
        if tok:
            yield tok, _group_from_row(keys.get(name))


def resolve_token(module: Optional[str] = None, group_id: Optional[str] = None) -> str:
    """Pick a child key for this module. Never use another module's narrow key.

    If group_id is set, skip child rows bound to a different group so a key for
    worker A cannot be sent at worker B. Parent is last-resort fallback.
    """
    wanted = (group_id or "").strip()
    if not (module or "").strip():
        got = _generic_or_parent_token()
        if got:
            return got
        cred = load_credentials()
        keys = cred.get("keys") if isinstance(cred.get("keys"), dict) else {}
        for row in keys.values():
            tok = _token_from_row(row)
            if tok:
                return tok
        return ""

    unbound = ""
    for tok, bound in _iter_module_candidates(module):
        if bound:
            if wanted and not _groups_match(bound, wanted):
                continue
            if wanted:
                return tok
            return unbound or tok
        if not unbound:
            unbound = tok
            if not wanted:
                return tok
    if wanted:
        return unbound or _generic_or_parent_token()
    return unbound or _generic_or_parent_token()


API_KEY = resolve_token()


def resolve_group_id(group_id: Optional[str] = None, module: Optional[str] = None) -> str:
    gid = (group_id or "").strip()
    if gid:
        return gid
    env_gid = DEFAULT_GROUP_ID
    if env_gid:
        return env_gid
    mod = (module or "").strip().lower() or None
    if not mod:
        return ""
    cred = load_credentials()
    keys = cred.get("keys") if isinstance(cred.get("keys"), dict) else {}
    for name in credential_module_names(mod):
        gid_row = _group_from_row(keys.get(name))
        if gid_row:
            return gid_row
    return ""


def headers_ai(module: Optional[str] = None, group_id: Optional[str] = None) -> dict[str, str]:
    h = {"Accept": "application/json", "Content-Type": "application/json"}
    token = resolve_token(module, group_id=group_id)
    if token:
        h["Authorization"] = f"Bearer {token}"
    return h


def headers_booking(module: Optional[str] = None, group_id: Optional[str] = None) -> dict[str, str]:
    h = headers_ai(module or "tasks", group_id=group_id)
    if INTERNAL_SECRET:
        h["X-Booking-Internal-Secret"] = INTERNAL_SECRET
    return h


def _missing_module_key(module: str) -> None:
    raise RuntimeError(json.dumps({
        "success": False,
        "message": f"нужен child для {module}, не общий",
        "status_code": 403,
    }, ensure_ascii=False))


def _group_from_request_kwargs(kwargs: dict) -> str:
    params = kwargs.get("params")
    if isinstance(params, dict):
        gid = str(params.get("group_id") or "").strip()
        if gid:
            return gid
    body = kwargs.get("json")
    if isinstance(body, dict):
        gid = str(body.get("group_id") or body.get("defaultGroupId") or "").strip()
        if gid:
            return gid
        event = body.get("event")
        if isinstance(event, dict):
            return str(event.get("defaultGroupId") or event.get("group_id") or "").strip()
    return ""


def request_ai(method: str, path: str, **kwargs: Any) -> Any:
    module = kwargs.pop("module", None)
    gid = _group_from_request_kwargs(kwargs)
    if module and not resolve_token(module, group_id=gid):
        _missing_module_key(str(module))
    url = f"{API_BASE}{path}"
    with httpx.Client(timeout=60.0, headers=headers_ai(module, group_id=gid)) as client:
        resp = client.request(method, url, **kwargs)
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


def request_booking(method: str, path: str, **kwargs: Any) -> Any:
    module = kwargs.pop("module", "tasks")
    gid = _group_from_request_kwargs(kwargs)
    if module and not resolve_token(module, group_id=gid):
        _missing_module_key(str(module))
    url = f"{BOOKING_BASE}{path}"
    with httpx.Client(timeout=60.0, headers=headers_booking(module, group_id=gid)) as client:
        resp = client.request(method, url, **kwargs)
    try:
        data = resp.json()
    except Exception:
        data = {"ok": False, "error": resp.text[:500], "status_code": resp.status_code}
    if resp.status_code >= 400:
        raise RuntimeError(json.dumps(data, ensure_ascii=False))
    return data


def require_group_id(group_id: Optional[str] = None, module: Optional[str] = None) -> str:
    gid = resolve_group_id(group_id, module)
    if not gid:
        raise ValueError("group_id required (arg, AIWORKERS_GROUP_ID, or credentials.json)")
    return gid


def enabled_modules() -> set[str]:
    raw = (os.getenv("AIWORKERS_MODULES") or DEFAULT_MODULES).strip()
    if raw in ("*", "all"):
        return {"surveys", "tasks", "workers", "telegram", "finance", "crm", "booking"}
    chosen = {part.strip().lower() for part in raw.split(",") if part.strip()}
    enabled = expand_enabled_modules(chosen)
    if "crm" in enabled and "tasks" in enabled:
        enabled.add("booking")
    return enabled
