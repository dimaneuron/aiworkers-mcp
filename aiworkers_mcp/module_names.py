"""Child module names and aliases. Keep in sync with h/mcp_identity.py.

Security: aliases are names only. Existing tasks/crm keys stay narrow.
booking (book, calendar) grants tasks+crm on the bound group; never surveys/
workers/telegram. Group isolation is enforced on the server.
"""

from __future__ import annotations

CANONICAL_CHILD_MODULES = frozenset(
    {"surveys", "tasks", "workers", "telegram", "crm", "booking"}
)

MODULE_ALIASES = {
    "booking": "booking",
    "book": "booking",
    "calendar": "booking",
}

MINTABLE_MODULES = tuple(
    sorted(CANONICAL_CHILD_MODULES | frozenset(MODULE_ALIASES))
)

# Client credential lookup: exact module first, then umbrella aliases.
# Never borrow a narrower sibling (tasks must not be used as crm).
_MODULE_KEY_FALLBACKS = {
    "tasks": ("tasks", "booking", "book", "calendar"),
    "crm": ("crm", "booking", "book", "calendar"),
    "booking": ("booking", "book", "calendar"),
}


def canonicalize_module(module: str) -> str:
    raw = (module or "").strip().lower()
    return MODULE_ALIASES.get(raw, raw)


def credential_module_names(module: str) -> tuple[str, ...]:
    raw = (module or "").strip().lower()
    if not raw:
        return ()
    names = _MODULE_KEY_FALLBACKS.get(raw)
    if names:
        return names
    canon = canonicalize_module(raw)
    if canon != raw:
        names = _MODULE_KEY_FALLBACKS.get(canon)
        if names:
            return names
        return (canon,)
    return (raw,)


def expand_enabled_modules(names: set[str]) -> set[str]:
    out: set[str] = set()
    for name in names:
        raw = (name or "").strip().lower()
        canon = canonicalize_module(raw)
        if canon == "booking" or raw in MODULE_ALIASES:
            out.update({"tasks", "crm"})
        else:
            out.add(raw)
    return out
