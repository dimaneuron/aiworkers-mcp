"""
MCP server: AIWorkers / НЕЙРОСОТРУДНИКИ.

Thin stdio client. Business logic stays on private HTTPS APIs.

Environment:
  AIWORKERS_API_KEY       — parent or legacy Bearer (fallback)
  AIWORKERS_KEY_WORKERS   — child token for workers (also surveys/tasks/telegram/crm)
  AIWORKERS_API_BASE      — default https://ai.knopka.click
  AIWORKERS_BOOKING_BASE  — default https://book.knopka.click/booking
  AIWORKERS_GROUP_ID      — default Telegram group for tasks
  AIWORKERS_MODULES       — comma list, default surveys,tasks,workers,telegram,crm
                            finance is stubbed (not in v1)
  AIWORKERS_KNOPKA_AI_KEY — user LLM key for api.knopka.click (or credentials knopka_ai)
  AIWORKERS_KNOPKA_AI_BASE — default https://api.knopka.click
  AIWORKERS_TG_TIMEOUT    — timeout seconds for /tg/ CRM calls (default 180)
  Tokens also from ~/.config/aiworkers/credentials.json (`aiworkers-mcp login`)
"""

from __future__ import annotations

import json
import sys

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:
    print(
        'Missing dependency "mcp". Install: pip install aiworkers-mcp',
        file=sys.stderr,
    )
    raise SystemExit(1) from exc

from aiworkers_mcp.http import enabled_modules, request_ai, resolve_group_id, resolve_token
from aiworkers_mcp.login import login_help, save_child_token
from aiworkers_mcp.module_names import CANONICAL_CHILD_MODULES, MINTABLE_MODULES, canonicalize_module
from aiworkers_mcp.modules import ai, crm, finance, surveys, tasks, telegram, tg, workers
from aiworkers_mcp.skill import fetch_skill, skill_as_json

mcp = FastMCP(
    "aiworkers",
    instructions=(
        "AIWorkers (НЕЙРОСОТРУДНИКИ) MCP. If there is no API key, call "
        "aiworkers_login_link and tell the human to open that Telegram URL "
        "(no token in the link), copy the one-time token from the Mini App, "
        "then run `aiworkers-mcp login` and paste it. Do not invent tokens. "
        "Call aiworkers_skill or aiworkers_skill_update to install SKILL.md. "
        "Call aiworkers_whoami first when a key exists. Live: surveys, tasks, "
        "workers (two-layer balance, salary/tt quote→confirm, partner), "
        "telegram (status+commands+restart, no send), booking CRM. "
        "Parent awp_ mints child awm_ via aiworkers_token_mint. "
        "ai_keys_issue mints an api.knopka.click LLM key (not awp_/awm_); "
        "then ai_chat / ai_request / ai_models and tg_* userbot CRM "
        "(/tg/: channels, bots, accounts). telegram_* is the worker bot "
        "process, not /tg/. Finance is not in v1."
    ),
)


@mcp.tool()
def aiworkers_login_link() -> str:
    """Share a Telegram URL to get a one-time MCP token. The link has no secret. After the Mini App shows the token once, run `aiworkers-mcp login` and paste it. Works without an existing key."""
    return json.dumps(login_help(), ensure_ascii=False, indent=2)


@mcp.tool()
def aiworkers_skill() -> str:
    """Return the AIWorkers MCP SKILL.md (how to log in and which tools to call). No existing key required."""
    return skill_as_json(install=False)


@mcp.tool()
def aiworkers_skill_update() -> str:
    """Write/refresh SKILL.md into ~/.cursor/skills/aiworkers (and project .cursor/skills if present). Call this to pick up the latest skill after a deploy. No existing key required."""
    return skill_as_json(install=True)


@mcp.tool()
def aiworkers_whoami() -> str:
    """Show what this API key can see: groups, modules, endpoint map. Call this first. If there is no key, returns the login URL."""
    if not resolve_token():
        payload = login_help()
        payload["success"] = False
        payload["message"] = (
            "no MCP token. Open url, copy the one-time token, then run aiworkers-mcp login"
        )
        return json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        data = request_ai("GET", "/api/mcp/whoami")
    except RuntimeError:
        data = request_ai("GET", "/api/survey/agent")
    if not isinstance(data, dict):
        data = {"raw": data}
    data["modules_enabled"] = sorted(enabled_modules())
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.tool()
def aiworkers_token_mint(module: str, group_id: str = "", save: bool = True) -> str:
    """Mint a child awm_ token for one module + one group. Parent awp_ only. Token is shown once. save=true (default) writes it to credentials.json so this MCP can call that module without Mini App. Free for now; later will debit group TokenTime."""
    requested = (module or "").strip().lower()
    if requested not in MINTABLE_MODULES:
        raise ValueError(f"module must be one of: {', '.join(sorted(MINTABLE_MODULES))}")
    mod = canonicalize_module(requested)
    if mod not in CANONICAL_CHILD_MODULES:
        raise ValueError(f"module must be one of: {', '.join(sorted(MINTABLE_MODULES))}")
    gid = resolve_group_id(group_id, module=mod)
    if not gid:
        raise ValueError("group_id required (arg, AIWORKERS_GROUP_ID, or credentials.json)")
    if not resolve_token():
        payload = login_help()
        payload["success"] = False
        payload["message"] = (
            "parent awp_ required to mint. Open url, copy the token, then aiworkers-mcp login"
        )
        return json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        data = request_ai(
            "POST",
            "/api/mcp/identity/tokens",
            json={"module": mod, "group_id": gid},
        )
    except RuntimeError as e:
        return str(e)
    if not isinstance(data, dict):
        data = {"raw": data}
    secret = str(data.get("token") or "").strip()
    saved = None
    if save and secret:
        path = save_child_token(secret, module=mod, group_id=gid)
        saved = str(path)
        data["saved"] = saved
        data["saved_module"] = mod
    data["restart_hint"] = (
        "child is in credentials.json; next tool calls for this module use it. "
        "Restart the agent if a tool still 403s. Do not commit the token or paste the seed."
    )
    return json.dumps(data, ensure_ascii=False, indent=2)


@mcp.resource("aiworkers://skill")
def aiworkers_skill_resource() -> str:
    """Latest SKILL.md for this MCP."""
    return fetch_skill()["content"]


_MODULE_LOADERS = {
    "surveys": surveys.register,
    "tasks": tasks.register,
    "workers": workers.register,
    "telegram": telegram.register,
    "finance": finance.register,
    "crm": crm.register,
}


def _load_modules() -> None:
    chosen = enabled_modules()
    for name, loader in _MODULE_LOADERS.items():
        if name in chosen:
            loader(mcp)
    ai.register(mcp)
    tg.register(mcp)


_load_modules()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        from aiworkers_mcp.login import cmd_login

        cmd_login()
        return
    if len(sys.argv) > 1 and sys.argv[1] in {"skill", "skill-update", "skill-install"}:
        from aiworkers_mcp.skill import read_bundled_skill, skill_as_json

        cmd = sys.argv[1]
        if cmd == "skill" and (len(sys.argv) < 3 or sys.argv[2] not in {"update", "install"}):
            print(read_bundled_skill())
            return
        print(skill_as_json(install=True))
        return
    if not resolve_token():
        print(
            "Warning: no MCP token (aiworkers-mcp login or AIWORKERS_API_KEY) — authenticated tools will return 401.",
            file=sys.stderr,
        )
    mcp.run()


if __name__ == "__main__":
    main()
