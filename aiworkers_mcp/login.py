"""Save a parent or module child token to ~/.config/aiworkers/credentials.json."""

from __future__ import annotations

import getpass
import json
import logging
import os
import sys
import time
from pathlib import Path

import httpx

from aiworkers_mcp.http import (
    API_BASE,
    LOGIN_TELEGRAM_URL,
    credentials_path,
    load_credentials,
    login_verify_url,
    request_ai,
    save_credentials,
)
from aiworkers_mcp.module_names import canonicalize_module

POLL_INTERVAL = 2.5

# httpx logs every request at INFO (once the mcp import configures logging); keep the login prompt clean.
logging.getLogger("httpx").setLevel(logging.WARNING)


def clickable(url: str) -> str:
    """OSC 8 terminal hyperlink on a tty, plain URL otherwise."""
    if sys.stdout.isatty() and os.environ.get("TERM") != "dumb":
        return f"\033]8;;{url}\033\\{url}\033]8;;\033\\"
    return url


def open_and_copy(url: str) -> None:
    """Best effort: copy the link to the clipboard and open it in the default browser.

    Skipped without a tty, over SSH, or when AIWORKERS_NO_OPEN is set.
    """
    if os.environ.get("AIWORKERS_NO_OPEN") or not sys.stdout.isatty():
        return
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY"):
        return
    import shutil
    import subprocess
    import webbrowser

    for cmd in (["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["clip"]):
        if shutil.which(cmd[0]):
            try:
                subprocess.run(cmd, input=url.encode(), check=True, timeout=3)
                print("(link copied to clipboard)")
            except Exception:
                pass
            break
    try:
        webbrowser.open(url)
    except Exception:
        pass


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


def device_start() -> tuple[str, str, int]:
    data = request_ai("POST", "/api/mcp/identity/device/start", json={})
    if not isinstance(data, dict):
        raise RuntimeError("unexpected response from device/start")
    device_code = str(data.get("device_code") or "").strip()
    user_code = str(data.get("user_code") or "").strip()
    if not device_code or not user_code:
        raise RuntimeError("device/start returned no codes")
    return device_code, user_code, int(data.get("expires_in") or 600)


def device_poll(device_code: str) -> dict:
    data = request_ai("POST", "/api/mcp/identity/device/poll", json={"device_code": device_code})
    return data if isinstance(data, dict) else {"raw": data}


def save_parent_token(secret: str) -> Path:
    cred = load_credentials()
    cred["parent"] = secret
    return save_credentials(cred)


def save_token(token: str) -> None:
    """Validate a pasted awp_/awm_ token via whoami and write it to credentials.json."""
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
    kind = data.get("kind") or "legacy"
    module = data.get("module")
    group_id = data.get("group_id")
    if kind == "parent" or module in (None, "", "*"):
        path = save_parent_token(token)
    else:
        cred = load_credentials()
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


def prompt_paste() -> None:
    print()
    print("Open this link in Telegram. There is no token in the URL.")
    print(clickable(LOGIN_TELEGRAM_URL))
    open_and_copy(LOGIN_TELEGRAM_URL)
    print("The Mini App shows the token once. Copy it, then paste here.")
    print()
    try:
        token = getpass.getpass("token: ").strip()
    except Exception:
        token = input("token: ").strip()
    if not token:
        print("empty token", file=sys.stderr)
        raise SystemExit(1)
    save_token(token)


def pair_device() -> bool:
    """Device pairing. True once a parent token is saved; False means fall back to paste."""
    try:
        device_code, user_code, expires_in = device_start()
    except Exception as e:
        print(f"pairing unavailable ({e}); falling back to paste", file=sys.stderr)
        return False
    print("Open this link in Telegram and tap Confirm in the Mini App:")
    print(clickable(login_verify_url(user_code)))
    open_and_copy(login_verify_url(user_code))
    print(f"code: {user_code}  (expires in {expires_in}s, Ctrl+C to paste a token instead)")
    deadline = time.monotonic() + expires_in
    failures = 0
    try:
        while time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL)
            try:
                data = device_poll(device_code)
                failures = 0
            except Exception as e:
                failures += 1
                if failures >= 5:
                    print(f"pairing poll failed ({e}); falling back to paste", file=sys.stderr)
                    return False
                continue
            status = data.get("status")
            if status == "pending":
                continue
            if status == "confirmed":
                secret = str(data.get("parent_token") or "").strip()
                if not secret:
                    print("pairing confirmed but no token returned; falling back to paste", file=sys.stderr)
                    return False
                prefix = data.get("prefix") or secret[:12]
                path = save_parent_token(secret)
                secret = ""
                print(f"saved parent * → {path}")
                print(json.dumps(
                    {
                        "kind": "parent",
                        "module": None,
                        "group_id": None,
                        "prefix": prefix,
                        "eth_address": data.get("eth_address"),
                    },
                    ensure_ascii=False,
                    indent=2,
                ))
                return True
            print(f"pairing {status or 'failed'}; falling back to paste", file=sys.stderr)
            return False
    except KeyboardInterrupt:
        print("\ninterrupted; falling back to paste")
        return False
    print("pairing expired; falling back to paste", file=sys.stderr)
    return False


def cmd_login(args: list[str] | None = None) -> None:
    args = list(args or [])
    paste_only = False
    for a in args:
        if a == "--paste":
            paste_only = True
        else:
            print(f"unknown argument: {a}\nusage: aiworkers-mcp login [--paste]", file=sys.stderr)
            raise SystemExit(2)
    if not paste_only and pair_device():
        return
    prompt_paste()


def pending_login_path() -> Path:
    return credentials_path().parent / "pending_login.json"


def save_pending_device_code(device_code: str, user_code: str) -> None:
    path = pending_login_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_text(json.dumps({"device_code": device_code, "user_code": user_code}), encoding="utf-8")
    os.chmod(path, 0o600)


def load_pending_device_code() -> dict:
    path = pending_login_path()
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def clear_pending_device_code() -> None:
    path = pending_login_path()
    try:
        path.unlink()
    except FileNotFoundError:
        pass


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


def save_knopka_ai_wallet_key(
    key: str,
    *,
    alias: str = "",
    prefix: str = "",
    eth_address: str = "",
    as_default: bool = False,
):
    """Write the wallet root (contract) key into credentials.json knopka_ai_wallet.

    as_default also copies it to knopka_ai and moves the previous value to knopka_ai_prev.
    """
    import time

    secret = (key or "").strip()
    if not secret:
        raise ValueError("key required")
    cred = load_credentials()
    row = {
        "key": secret,
        "prefix": (prefix or secret[:12]).strip() or secret[:12],
        "key_alias": (alias or "").strip() or None,
        "eth_address": (eth_address or "").strip() or None,
        "saved_at": int(time.time()),
    }
    cred["knopka_ai_wallet"] = row
    if as_default:
        old = cred.get("knopka_ai")
        if old:
            cred["knopka_ai_prev"] = old
        cred["knopka_ai"] = {k: row[k] for k in ("key", "prefix", "key_alias")}
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
