"""Direct client for api.knopka.click (LiteLLM). User key, allowlisted paths."""

from __future__ import annotations

import json
import os
from typing import Any
from urllib.parse import urlparse

import httpx

from aiworkers_mcp.http import KNOPKA_AI_BASE, load_credentials

INFERENCE_TIMEOUT = 180.0

_DENY_PREFIXES = (
    "/key/issue",
    "/key/generate",
    "/key/delete",
    "/key/update",
    "/key/regenerate",
    "/user/",
    "/team/",
    "/organization/",
    "/global/",
    "/credentials",
    "/config",
    "/budget",
    "/model/new",
    "/model/delete",
)

_ALLOW_EXACT = frozenset({
    "/v1/chat/completions",
    "/v1/completions",
    "/v1/embeddings",
    "/v1/images/generations",
    "/v1/images/edits",
    "/v1/audio/speech",
    "/v1/audio/transcriptions",
    "/v1/models",
    "/v1/moderations",
    "/v1/responses",
    "/v1/files",
    "/v1/messages",
    "/v1/ocr",
    "/v1/rerank",
    "/v2/rerank",
    "/models",
    "/chat/completions",
    "/completions",
    "/embeddings",
    "/ocr",
    "/rerank",
    "/key/info",
})

_ALLOW_PREFIXES = (
    "/v1/responses/",
    "/v1/files/",
    "/v1/videos",
    "/v1/rag/",
    "/images/",
    "/audio/",
    "/cursor/",
    "/anthropic/",
    "/videos",
    "/rag/",
)


def normalize_ai_path(path: str) -> str:
    raw = (path or "").strip()
    if not raw:
        raise ValueError("path not allowed")
    if "://" in raw:
        raw = urlparse(raw).path or "/"
    else:
        if "?" in raw:
            raw = raw.split("?", 1)[0]
        if "#" in raw:
            raw = raw.split("#", 1)[0]
    raw = raw.strip()
    if not raw.startswith("/"):
        raw = "/" + raw
    while "//" in raw:
        raw = raw.replace("//", "/")
    if any(part == ".." for part in raw.split("/")):
        raise ValueError("path not allowed")
    parts = [part for part in raw.split("/") if part and part != "."]
    return "/" + "/".join(parts)


def path_allowed(path: str) -> bool:
    try:
        normalized = normalize_ai_path(path)
    except ValueError:
        return False
    for deny in _DENY_PREFIXES:
        if deny.endswith("/"):
            if normalized == deny.rstrip("/") or normalized.startswith(deny):
                return False
        elif normalized == deny or normalized.startswith(deny + "/"):
            return False
    if normalized in _ALLOW_EXACT:
        return True
    for allow in _ALLOW_PREFIXES:
        if allow.endswith("/"):
            if normalized == allow.rstrip("/") or normalized.startswith(allow):
                return True
        elif normalized == allow or normalized.startswith(allow + "/"):
            return True
    return False


def resolve_knopka_ai_key() -> str:
    env_key = (os.getenv("AIWORKERS_KNOPKA_AI_KEY") or "").strip()
    if env_key:
        return env_key
    cred = load_credentials()
    row = cred.get("knopka_ai")
    if isinstance(row, dict):
        return str(row.get("key") or "").strip()
    if isinstance(row, str):
        return row.strip()
    return ""


def _missing_knopka_ai_key() -> None:
    raise RuntimeError(json.dumps({
        "success": False,
        "message": "нужен ключ api.knopka.click. Вызови ai_keys_issue (parent awp_)",
        "status_code": 401,
    }, ensure_ascii=False))


def request_knopka_ai(method: str, path: str, json_body: Any = None) -> Any:
    method_u = (method or "GET").strip().upper()
    if method_u not in {"GET", "POST", "DELETE"}:
        raise ValueError("method must be GET, POST, or DELETE")
    if not path_allowed(path):
        raise ValueError("path not allowed")
    key = resolve_knopka_ai_key()
    if not key:
        _missing_knopka_ai_key()
    url = f"{KNOPKA_AI_BASE}{normalize_ai_path(path)}"
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {key}",
    }
    payload = json_body
    if isinstance(payload, dict) and "stream" in payload:
        payload = dict(payload)
        payload["stream"] = False
    if payload is not None:
        headers["Content-Type"] = "application/json"
    with httpx.Client(timeout=INFERENCE_TIMEOUT, headers=headers) as client:
        resp = client.request(method_u, url, json=payload)
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
