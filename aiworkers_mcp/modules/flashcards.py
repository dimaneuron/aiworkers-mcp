"""Admin-only flashcards tools — HTTP to api.knopka.click (aiworkersbot's own deck/cards).

Not a purchasable per-group module: no awm_ child token needed, works on the
admin's own parent awp_ token like ai.py's tools. The server rejects any
non-admin caller with a 403 body, which we surface as clean JSON via
_call_ai below instead of letting it raise.
"""
from __future__ import annotations

import json
from typing import Any

from aiworkers_mcp.http import request_ai

_EXPECTED_ERROR_CODES = (400, 401, 403, 404, 409, 429, 502, 503)


def _dump(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


def _call_ai(method: str, path: str, **kwargs: Any) -> str:
    try:
        return _dump(request_ai(method, path, **kwargs))
    except RuntimeError as exc:
        try:
            payload = json.loads(str(exc))
        except json.JSONDecodeError:
            raise
        if isinstance(payload, dict) and payload.get("status_code") in _EXPECTED_ERROR_CODES:
            return _dump(payload)
        raise


def register(mcp) -> None:
    @mcp.tool()
    def flashcards_decks_list() -> str:
        """List the admin's own flashcard decks (aiworkersbot /cards data). Admin-only."""
        return _call_ai("GET", "/api/mcp/flashcards/decks")

    @mcp.tool()
    def flashcards_deck_create(name: str, description: str = "") -> str:
        """Create a new flashcard deck. Admin-only."""
        return _call_ai("POST", "/api/mcp/flashcards/decks", json={"name": name, "description": description})

    @mcp.tool()
    def flashcards_deck_get(deck_id: int) -> str:
        """Get one deck plus its stats (new/due/total). Admin-only."""
        return _call_ai("GET", f"/api/mcp/flashcards/decks/{int(deck_id)}")

    @mcp.tool()
    def flashcards_deck_rename(deck_id: int, name: str) -> str:
        """Rename a deck. Admin-only."""
        return _call_ai("POST", f"/api/mcp/flashcards/decks/{int(deck_id)}", json={"name": name})

    @mcp.tool()
    def flashcards_deck_delete(deck_id: int) -> str:
        """Delete a deck and all its cards/progress. Admin-only, irreversible."""
        return _call_ai("DELETE", f"/api/mcp/flashcards/decks/{int(deck_id)}")

    @mcp.tool()
    def flashcards_cards_list(deck_id: int, limit: int = 50, offset: int = 0) -> str:
        """List cards in a deck (paginated). Admin-only."""
        return _call_ai(
            "GET", f"/api/mcp/flashcards/decks/{int(deck_id)}/cards",
            params={"limit": limit, "offset": offset},
        )

    @mcp.tool()
    def flashcards_card_add(deck_id: int, front: str, back: str, hint: str = "", tags_json: str = "[]") -> str:
        """Add one card to a deck. tags_json is a JSON array of strings. Admin-only."""
        try:
            tags = json.loads(tags_json or "[]")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid tags_json: {e}") from e
        return _call_ai(
            "POST", f"/api/mcp/flashcards/decks/{int(deck_id)}/cards",
            json={"front": front, "back": back, "hint": hint, "tags": tags},
        )

    @mcp.tool()
    def flashcards_card_get(card_id: int) -> str:
        """Get one card's current content and FSRS state. Admin-only."""
        return _call_ai("GET", f"/api/mcp/flashcards/cards/{int(card_id)}")

    @mcp.tool()
    def flashcards_card_edit(card_id: int, front: str = "", back: str = "") -> str:
        """Edit a card's front/back text (leave blank to keep unchanged). Admin-only."""
        body: dict[str, Any] = {}
        if front:
            body["front"] = front
        if back:
            body["back"] = back
        return _call_ai("POST", f"/api/mcp/flashcards/cards/{int(card_id)}", json=body)

    @mcp.tool()
    def flashcards_card_toggle_suspend(card_id: int) -> str:
        """Suspend/unsuspend a card (suspended cards never come up for review). Admin-only."""
        return _call_ai("POST", f"/api/mcp/flashcards/cards/{int(card_id)}", json={"action": "toggle_suspend"})

    @mcp.tool()
    def flashcards_card_delete(card_id: int) -> str:
        """Delete a card and its review progress. Admin-only, irreversible."""
        return _call_ai("DELETE", f"/api/mcp/flashcards/cards/{int(card_id)}")

    @mcp.tool()
    def flashcards_import_csv(deck_id: int, csv_base64: str) -> str:
        """Import/update cards in a deck from a base64-encoded CSV (front,back,hint,tags,... columns).
        Cards matching an existing front are updated in place (progress kept); new fronts are added.
        Admin-only."""
        return _call_ai("POST", f"/api/mcp/flashcards/decks/{int(deck_id)}/import", json={"csv_base64": csv_base64})

    @mcp.tool()
    def flashcards_export_csv(deck_id: int) -> str:
        """Export all cards in a deck as base64-encoded CSV. Admin-only."""
        return _call_ai("GET", f"/api/mcp/flashcards/decks/{int(deck_id)}/export")

    @mcp.tool()
    def flashcards_stats() -> str:
        """Overview stats across all of the admin's decks (new/due/total). Admin-only."""
        return _call_ai("GET", "/api/mcp/flashcards/stats")
