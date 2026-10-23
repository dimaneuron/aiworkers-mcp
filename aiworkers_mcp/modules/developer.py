"""contact_developer — agent files a structured ticket (bug / feature / question) to the developer."""
from __future__ import annotations

import json
from typing import Any, Literal

from aiworkers_mcp.http import request_ai


def register(mcp) -> None:
    @mcp.tool()
    def contact_developer(
        kind: Literal["bug", "feature", "question", "other"],
        title: str,
        summary: str,
        tool: str = "",
        steps: str = "",
        expected: str = "",
        actual: str = "",
        context: str = "",
    ) -> str:
        """Send a ticket to the AIWorkers developer (arrives in his Telegram). Use ONLY when the MCP itself is at fault or lacks something: a tool errors unexpectedly (5xx, wrong/empty result, contradicts SKILL.md) or a needed capability is missing. NOT for user mistakes, 401/403 permission or balance issues, or your own bugs — fix or explain those. Before sending: retry once, check aiworkers_whoami, search your own context for a known workaround, and show the human the draft and get a yes unless they asked you to report. One ticket per problem; max 10/hour.
        Write it so the developer can act without asking back:
        - kind: bug | feature | question | other.
        - title: ≤100 chars, specific, starts with the tool/area: «workers_chat_send: 500 при channel=topic», not «не работает».
        - summary: 2-5 sentences — what happened (bug) or what is needed and WHY, i.e. the user's goal (feature). Facts, no apologies.
        - bug: tool = exact tool name; steps = numbered calls with arguments (redact tokens, awp_/awm_/sk- keys, seed, phone numbers); expected vs actual = exact error text / status_code / response snippet; context = group_id, date/time, how often.
        - feature: expected = desired behaviour (tool name + args you wish existed); actual = current workaround or why it's insufficient.
        NEVER include secrets (tokens, keys, 12-word seed, bot tokens) or private user data. Returns ticket_id; tell the human it was sent."""
        body: dict[str, Any] = {
            "kind": kind,
            "title": title,
            "summary": summary,
            "tool": tool,
            "steps": steps,
            "expected": expected,
            "actual": actual,
            "context": context,
        }
        try:
            return json.dumps(request_ai("POST", "/api/mcp/developer/contact", json=body), ensure_ascii=False, indent=2)
        except RuntimeError as exc:
            try:
                payload = json.loads(str(exc))
            except json.JSONDecodeError:
                raise exc
            if isinstance(payload, dict) and payload.get("status_code") in (400, 429, 502, 503):
                return json.dumps(payload, ensure_ascii=False, indent=2)
            raise
