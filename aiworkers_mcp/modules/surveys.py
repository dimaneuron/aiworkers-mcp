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
        redirect_to_own_bot: bool = True,
    ) -> str:
        """Create a survey from DSL. redirect_to_own_bot (default true): after the form, redirect into the group's own connected bot (https://t.me/<bot>?start=ref_form_<key>); otherwise redirect_after_complete / default aiworkersbot. Child token: group_id must match the key or be omitted. Mismatch → 403. Do not add questions for name/phone/contacts unless the user asks: the respondent's Telegram profile is available after submit. «Survey with a ready reply» = then survey_agent_share → workers_readyreply_upsert (button) → give the user start_link."""
        payload: dict[str, Any] = {"dsl": dsl, "source": "mcp"}
        if creator_id is not None:
            payload["creator_id"] = creator_id
        if group_id:
            payload["group_id"] = group_id
        payload["redirect_to_own_bot"] = bool(redirect_to_own_bot)
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
        """Read survey settings. Keys: redirect_to_own_bot (bool, missing=false), redirect_after_complete (URL: empty, https://t.me/..., tg://resolve..., https://...), redirect_mini_app_action (close|minimize), defaultViewMode (all|blocks|single). Also returns read-only top-level resolved_redirect {url, source, bot_username} and own_bot_username (null if no bot connected). Redirect priority: own bot > redirect_after_complete > default https://t.me/aiworkersbot?start=ref_forms."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        data = request_ai("GET", f"/api/survey/agent/{sid}/settings")
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def survey_agent_settings_save(survey_id: str, settings_json: str) -> str:
        """Save survey settings. settings_json is a bare settings object or {\"settings\": {...}, \"replace\": true}. By default MERGES into stored settings; a null value deletes that key; \"replace\": true (top level of the payload) replaces ALL settings. Keys: redirect_to_own_bot, redirect_after_complete, redirect_mini_app_action, defaultViewMode. Returns resolved_redirect. Do NOT use a readyreply start_link (P<id>) as redirect_after_complete: it would re-send the post with the survey button."""
        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        try:
            payload = json.loads(settings_json)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid settings_json: {exc}") from exc
        if isinstance(payload, dict) and isinstance(payload.get("settings"), dict):
            body = {"settings": payload["settings"]}
            if payload.get("replace"):
                body["replace"] = True
        elif isinstance(payload, dict):
            payload = dict(payload)
            replace = payload.pop("replace", None)
            body = {"settings": payload}
            if replace:
                body["replace"] = True
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
    def survey_agent_share(
        survey_id: str,
        mode: str = "",
        utm_source: str = "",
        utm_medium: str = "",
        utm_campaign: str = "",
        utm_content: str = "",
        utm_term: str = "",
        button_text: str = "",
    ) -> str:
        """Share links. RECOMMENDED: button_url = SHORT form_url (https://ai.knopka.click/form/<slug>) + ?mode&utm_*&user_id={{user_id}} as a ready-reply button (the bot substitutes the recipient id; the Mini App logs the user in). client_url (long) is a fallback. Optional mode=all|blocks|single and utm_* are appended to the URL."""
        from urllib.parse import urlencode

        sid = _normalize_survey_ref(survey_id)
        if not sid:
            raise ValueError("survey_id is required")
        mode = (mode or "").strip().lower()
        if mode and mode not in ("all", "blocks", "single"):
            raise ValueError("mode must be all, blocks or single")
        data = request_ai("GET", f"/api/survey/agent/{sid}")
        data = data if isinstance(data, dict) else {}
        meta = data.get("meta") or {}
        title = str(meta.get("title") or "").strip()
        form_url = data.get("form_url")
        client_url = data.get("client_url")
        extra = {
            k: v.strip()
            for k, v in (
                ("mode", mode),
                ("utm_source", utm_source),
                ("utm_medium", utm_medium),
                ("utm_campaign", utm_campaign),
                ("utm_content", utm_content),
                ("utm_term", utm_term),
            )
            if v and v.strip()
        }
        button_url = None
        base_url = form_url or client_url
        if base_url:
            sep = "&" if "?" in base_url else "?"
            query = urlencode(extra)
            # {{user_id}} must stay literal (double braces = Mini App format).
            button_url = base_url + sep + (query + "&" if query else "") + "user_id={{user_id}}"
        redirect_after_submit = None
        try:
            st = request_ai("GET", f"/api/survey/agent/{sid}/settings")
            rr = st.get("resolved_redirect") if isinstance(st, dict) else None
            if isinstance(rr, dict):
                redirect_after_submit = rr.get("url")
        except Exception:
            redirect_after_submit = None
        text = (button_text or "").strip() or title or "Пройти опрос"
        chat_text = f"{title}\n{form_url}".strip() if title else str(form_url or "")
        return json.dumps({
            "success": True,
            "survey_id": data.get("survey_id") or sid,
            "title": title,
            "button_url": button_url,
            "button": {"text": text, "url": button_url} if button_url else None,
            "form_url": form_url,
            "client_url": client_url,
            "chat_text": chat_text,
            "redirect_after_submit": redirect_after_submit,
            "hint": (
                "redirect_after_submit = where the respondent lands after the form (own bot > redirect_after_complete > default); "
                "change via survey_agent_settings_save. "
                "Recommended: workers_readyreply_upsert with item_json buttons=[button] and a post text, "
                "then give the user the ready-reply link. button_url is the short /form/<slug> link "
                "with mode/utm_* and user_id={{user_id}} (substituted by the bot). "
                "client_url (long) is a fallback; chat_text (plain form_url) has no user_id."
            ),
        }, ensure_ascii=False, indent=2)

    @mcp.resource("survey://dsl/spec")
    def survey_dsl_spec_resource() -> str:
        """Read-only Survey DSL specification (markdown)."""
        with httpx.Client(timeout=60.0, headers=headers_ai()) as client:
            resp = client.get(f"{API_BASE}/api/survey/dsl", params={"format": "markdown"})
            resp.raise_for_status()
            return resp.text
