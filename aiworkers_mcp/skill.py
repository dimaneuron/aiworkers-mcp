"""Bundled agent SKILL.md + install into Cursor/Claude skill dirs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from aiworkers_mcp.http import API_BASE, headers_ai


def bundled_skill_path() -> Path:
    return Path(__file__).resolve().parent / "SKILL.md"


def read_bundled_skill() -> str:
    path = bundled_skill_path()
    return path.read_text(encoding="utf-8")


def fetch_skill() -> dict:
    """Prefer live API (after deploy), else the copy inside this package."""
    import httpx

    try:
        with httpx.Client(timeout=20.0, headers=headers_ai()) as client:
            resp = client.get(f"{API_BASE}/api/mcp/skill")
        if resp.status_code < 400:
            data = resp.json()
            content = data.get("content") if isinstance(data, dict) else None
            if content:
                digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
                return {
                    "success": True,
                    "source": "api",
                    "content": content,
                    "sha256": digest,
                    "etag": digest[:16],
                }
    except Exception:
        pass
    content = read_bundled_skill()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return {
        "success": True,
        "source": "bundled",
        "content": content,
        "sha256": digest,
        "etag": digest[:16],
        "path": str(bundled_skill_path()),
    }


def install_destinations() -> list[Path]:
    home = Path.home()
    out = [home / ".cursor" / "skills" / "aiworkers" / "SKILL.md"]
    if (home / ".claude").is_dir():
        out.append(home / ".claude" / "skills" / "aiworkers" / "SKILL.md")
    cwd = Path.cwd()
    if (cwd / ".cursor").is_dir():
        out.append(cwd / ".cursor" / "skills" / "aiworkers" / "SKILL.md")
    if (cwd / ".claude").is_dir():
        out.append(cwd / ".claude" / "skills" / "aiworkers" / "SKILL.md")
    seen: set[str] = set()
    uniq: list[Path] = []
    for path in out:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        uniq.append(path)
    return uniq


def install_skill() -> dict:
    payload = fetch_skill()
    content = payload["content"]
    written: list[str] = []
    for path in install_destinations():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        written.append(str(path))
    return {
        "success": True,
        "source": payload.get("source"),
        "sha256": payload.get("sha256"),
        "written": written,
        "hint": "Restart the agent (or start a new chat) so it picks up the skill.",
    }


def skill_as_json(install: bool = False) -> str:
    data = install_skill() if install else fetch_skill()
    if not install:
        data = {
            "success": data.get("success"),
            "source": data.get("source"),
            "sha256": data.get("sha256"),
            "etag": data.get("etag"),
            "content": data.get("content"),
            "update": "call aiworkers_skill_update to write ~/.cursor/skills/aiworkers/SKILL.md",
        }
    return json.dumps(data, ensure_ascii=False, indent=2)
