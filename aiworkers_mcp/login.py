"""Save a parent or module child token to ~/.config/aiworkers/credentials.json."""

from __future__ import annotations

import getpass
import json
import sys

import httpx

from aiworkers_mcp.http import (
    API_BASE,
    LOGIN_TELEGRAM_URL,
    load_credentials,
    save_credentials,
)
from aiworkers_mcp.module_names import canonicalize_module


def login_help() -> dict:
    return {
        "success": True,
        "url": LOGIN_TELEGRAM_URL,
        "token_in_url": False,
        "next": [
            "Open the url in Telegram (no token in the link)",
            "Mint a module token in the Mini App — it is shown once",
            "Run: aiworkers-mcp login",
            "Paste the token; ~/.config/aiworkers/credentials.json is written automatically",
        ],
    }


def cmd_login() -> None:
    help_ = login_help()
    print("Open this link in Telegram. There is no token in the URL.")
    print(help_["url"])
    print()
    print("The Mini App shows the token once. Copy it, then paste here.")
    print("After that credentials.json is written and MCP is ready.")
    print()
    try:
        token = getpass.getpass("token: ").strip()
    except Exception:
        token = input("token: ").strip()
    if not token:
        print("empty token", file=sys.stderr)
        raise SystemExit(1)
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
    }
    with httpx.Client(timeout=30.0, headers=headers) as client:
        resp = client.get(f"{API_BASE}/api/mcp/whoami")
    try:
        data = resp.json()
    except Exception:
        data = {"success": False, "message": resp.text[:400]}
    if resp.status_code >= 400 or not data.get("success"):
        print(json.dumps(data, ensure_ascii=False, indent=2), file=sys.stderr)
        raise SystemExit(1)
    cred = load_credentials()
    kind = data.get("kind") or "legacy"
    module = data.get("module")
    group_id = data.get("group_id")
    if kind == "parent" or module in (None, "", "*"):
        cred["parent"] = token
    else:
        keys = cred.get("keys") if isinstance(cred.get("keys"), dict) else {}
        keys[canonicalize_module(str(module))] = {"token": token, "group_id": group_id}
        cred["keys"] = keys
    path = save_credentials(cred)
    print(f"saved {kind} {module or '*'} → {path}")
    print(json.dumps(
        {
            "kind": kind,
            "module": module,
            "group_id": group_id,
            "prefix": data.get("prefix"),
            "eth_address": data.get("eth_address"),
        },
        ensure_ascii=False,
        indent=2,
    ))


def save_child_token(token: str, *, module: str, group_id: str):
    """Write an awm_ child into credentials.json keys.<module>."""
    cred = load_credentials()
    keys = cred.get("keys") if isinstance(cred.get("keys"), dict) else {}
    keys[canonicalize_module(str(module))] = {"token": token, "group_id": str(group_id or "").strip() or None}
    cred["keys"] = keys
    return save_credentials(cred)


def save_knopka_ai_key(key: str, *, alias: str = "", prefix: str = ""):
    """Write the LiteLLM user key into credentials.json knopka_ai."""
    secret = (key or "").strip()
    if not secret:
        raise ValueError("key required")
    cred = load_credentials()
    cred["knopka_ai"] = {
        "key": secret,
        "prefix": (prefix or secret[:12]).strip() or secret[:12],
        "key_alias": (alias or "").strip() or None,
    }
    return save_credentials(cred)


def clear_knopka_ai_key(*, prefix: str = "", key: str = ""):
    """Drop knopka_ai from credentials if it matches prefix or full key."""
    cred = load_credentials()
    row = cred.get("knopka_ai")
    if row is None:
        return None
    stored = row if isinstance(row, dict) else {"key": row, "prefix": str(row)[:12]}
    stored_key = str(stored.get("key") or "").strip()
    stored_prefix = str(stored.get("prefix") or stored_key[:12]).strip()
    want_key = (key or "").strip()
    want_prefix = (prefix or "").strip()
    if want_key and stored_key and stored_key != want_key:
        return None
    if want_prefix and stored_prefix and stored_prefix != want_prefix:
        return None
    cred.pop("knopka_ai", None)
    return save_credentials(cred)
