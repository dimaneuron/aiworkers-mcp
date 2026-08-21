"""Survey / forms tools — HTTP to ai.knopka.click."""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from aiworkers_mcp.http import API_BASE, headers_ai as _headers_ai, request_ai as _request_ai


def _normalize_survey_ref(survey_id: str) -> str:
    """Full survey_id, public slug, /form/… path, or a pasted form URL."""
    raw = (survey_id or "").strip()
    if not raw:
        return raw
    lower = raw.lower()
    marker = "/form/"
    if marker in lower:
        raw = raw[lower.rfind(marker) + len(marker) :]
    elif lower.startswith("form/"):
        raw = raw[5:]
    return raw.split("?", 1)[0].split("#", 1)[0].strip().strip("/")


def headers_ai():
    return _headers_ai(module="surveys")


def request_ai(method: str, path: str, **kwargs: Any):
    kwargs.setdefault("module", "surveys")
    return _request_ai(method, path, **kwargs)


def register(mcp) -> None:
    @mcp.tool()
    def survey_get_dsl_rules(format: str = "markdown") -> str:
        """Fetch current Survey DSL parsing rules from the server."""
        fmt = (format or "markdown").strip().lower()
        if fmt == "json":
            data = request_ai("GET", "/api/survey/dsl")
            return json.dumps(data, ensure_ascii=False, indent=2)
        with httpx.Client(timeout=60.0, headers=headers_ai()) as client:
            resp = client.get(f"{API_BASE}/api/survey/dsl", params={"format": "markdown"})
            resp.raise_for_status()
            return resp.text

    @mcp.tool()
    def survey_validate_dsl(dsl: str) -> str:
        """Validate Survey DSL without saving."""
        data = request_ai("POST", "/api/survey/validate", json={"dsl": dsl})
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_list_forms(include_archived: bool = False) -> str:
        """List surveys for this API token (scoped by group_id). Archived hidden unless include_archived."""
        params = {"include_archived": "true"} if include_archived else None
        data = request_ai("GET", "/api/survey/agent/forms", params=params)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_get(survey_id: str) -> str:
        """Get survey DSL and metadata. survey_id may be the full id, public slug, or form URL."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai("GET", f"/api/survey/agent/{sid}")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_update(survey_id: str, dsl: str) -> str:
        """Update survey DSL (POST; nginx often 405s PUT)."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai("POST", f"/api/survey/agent/{sid}", json={"text": dsl})
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_responses(survey_id: str) -> str:
        """Fetch respondent answers for a survey."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai("GET", f"/api/survey/agent/{sid}/responses")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_scenarios_get(survey_id: str) -> str:
        """Get post-submit automation scenarios."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai("GET", f"/api/survey/agent/{sid}/scenarios")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_scenarios_save(survey_id: str, scenarios_json: str) -> str:
        """Save post-submit scenarios (JSON array or {\"scenarios\": [...]})."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        try:
            payload = json.loads(scenarios_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid scenarios_json: {exc}") from exc
        data = request_ai("POST", f"/api/survey/agent/{sid}/scenarios", json=payload)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_skill(format: str = "markdown") -> str:
        """Agent skill: auth, endpoints, group-bound token."""
        fmt = (format or "markdown").strip().lower()
        if fmt == "json":
            data = request_ai("GET", "/api/survey/agent/skill")
            return json.dumps(data, ensure_ascii=False, indent=2)
        with httpx.Client(timeout=60.0, headers=headers_ai()) as client:
            resp = client.get(
                f"{API_BASE}/api/survey/agent/skill", params={"format": "markdown"}
            )
            resp.raise_for_status()
            return resp.text

    @mcp.tool()
    def survey_create(
        dsl: str,
        creator_id: Optional[int] = None,
        group_id: Optional[str] = None,
    ) -> str:
        """Create a survey from DSL. Child token: group_id must match the key or be omitted. Mismatch → 403."""
        payload: dict[str, Any] = {"dsl": dsl, "source": "mcp"}
        if creator_id is not None:
            payload["creator_id"] = creator_id
        if group_id:
            payload["group_id"] = group_id
        data = request_ai("POST", "/api/survey/create", json=payload)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_stats(survey_id: str) -> str:
        """Funnel stats for a survey."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai("GET", f"/api/survey/agent/{sid}/stats")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_settings_get(survey_id: str) -> str:
        """Read survey settings (view mode, etc.)."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai("GET", f"/api/survey/agent/{sid}/settings")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_settings_save(survey_id: str, settings_json: str) -> str:
        """Save survey settings. settings_json is an object or {\"settings\": {...}}."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        try:
            payload = json.loads(settings_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid settings_json: {exc}") from exc
        if isinstance(payload, dict) and "settings" in payload:
            body = payload
        elif isinstance(payload, dict):
            body = {"settings": payload}
        else:
            raise ValueError("settings_json must be an object")
        data = request_ai("POST", f"/api/survey/agent/{sid}/settings", json=body)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_archive(survey_id: str, archived: bool = True) -> str:
        """Archive (hide from list) or restore a survey. Does not delete answers."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai(
            "POST",
            f"/api/survey/agent/{sid}/archive",
            json={"archived": archived},
        )
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_delete(survey_id: str, confirm: bool = False) -> str:
        """Permanently delete a survey, DSL file, and answers. Requires confirm=true."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        if not confirm:
            return json.dumps({
                "success": False,
                "message": "Pass confirm=true to permanently delete. Prefer survey_agent_archive.",
                "survey_id": sid,
            }, ensure_ascii=False, indent=2)
        data = request_ai("POST", f"/api/survey/agent/{sid}/delete")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_share(survey_id: str) -> str:
        """form_url + chat_text for workers_chat_send / readyreply. No native open-in-chat widget."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai("GET", f"/api/survey/agent/{sid}")
        meta = data.get("meta") if isinstance(data, dict) else {}
        title = str((meta or {}).get("title") or "").strip()
        form_url = data.get("form_url") if isinstance(data, dict) else None
        chat_text = f"{title}\n{form_url}".strip() if title else str(form_url or "")
        return json.dumps({
            "success": True,
            "survey_id": (data.get("survey_id") if isinstance(data, dict) else None) or sid,
            "title": title,
            "form_url": form_url,
            "client_url": data.get("client_url") if isinstance(data, dict) else None,
            "chat_text": chat_text,
            "hint": (
                "Send chat_text via workers_chat_send, or workers_readyreply_upsert "
                "then workers_broadcast_*. There is no Telegram Mini App open-form tool."
            ),
        }, ensure_ascii=False, indent=2)

    @mcp.resource("survey://dsl/spec")
    def survey_dsl_spec_resource() -> str:
        """Read-only Survey DSL specification (markdown)."""
        with httpx.Client(timeout=60.0, headers=headers_ai()) as client:
            resp = client.get(f"{API_BASE}/api/survey/dsl", params={"format": "markdown"})
            resp.raise_for_status()
            return resp.text
