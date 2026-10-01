"""Task tools — HTTP to book.knopka.click."""

from __future__ import annotations

import json
from typing import Any

from aiworkers_mcp.http import request_booking as _request_booking, require_group_id as _require_group_id


def request_booking(method: str, path: str, **kwargs: Any):
    kwargs.setdefault("module", "tasks")
    return _request_booking(method, path, **kwargs)


def require_group_id(group_id: str = ""):
    return _require_group_id(group_id, module="tasks")


def register(mcp) -> None:
    @mcp.tool()
    def tasks_list(
        group_id: str = "",
        status: str = "",
        source: str = "",
        from_time: str = "",
        to_time: str = "",
        q: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> str:
        """List tasks for a Telegram group (manual + booking)."""
        params: dict[str, Any] = {
            "group_id": require_group_id(group_id),
            "limit": limit,
            "offset": offset,
        }
        if status:
            params["status"] = status
        if source:
            params["source"] = source
        if from_time:
            params["from_time"] = from_time
        if to_time:
            params["to_time"] = to_time
        if q:
            params["q"] = q
        data = request_booking("GET", "/api/internal/tasks", params=params)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def tasks_count(
        group_id: str = "",
        status: str = "",
        source: str = "",
        from_time: str = "",
        to_time: str = "",
        q: str = "",
    ) -> str:
        """Count tasks with the same filters as tasks_list."""
        params: dict[str, Any] = {"group_id": require_group_id(group_id)}
        if status:
            params["status"] = status
        if source:
            params["source"] = source
        if from_time:
            params["from_time"] = from_time
        if to_time:
            params["to_time"] = to_time
        if q:
            params["q"] = q
        data = request_booking("GET", "/api/internal/tasks/count", params=params)
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def tasks_get(task_id: int, group_id: str = "") -> str:
        """Get one task by id."""
        data = request_booking(
            "GET",
            f"/api/internal/tasks/{int(task_id)}",
            params={"group_id": require_group_id(group_id)},
        )
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def tasks_create(
        title: str,
        group_id: str = "",
        description: str = "",
        start_date: str = "",
        end_date: str = "",
        contact: str = "",
        post_card: bool = True,
    ) -> str:
        """Create a manual task (optional Telegram card + calendar hold)."""
        task: dict[str, Any] = {"title": title}
        if description:
            task["description"] = description
        if start_date:
            task["start_date"] = start_date
        if end_date:
            task["end_date"] = end_date
        if contact:
            task["contact"] = contact
        data = request_booking(
            "POST",
            "/api/internal/tasks",
            json={
                "group_id": require_group_id(group_id),
                "task": task,
                "post_card": post_card,
            },
        )
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def tasks_update(task_id: int, group_id: str = "", patch_json: str = "{}") -> str:
        """Update task fields. patch_json: JSON object with title/description/status/dates."""
        try:
            patch = json.loads(patch_json or "{}")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid patch_json: {e}") from e
        if not isinstance(patch, dict):
            raise ValueError("patch_json must be an object")
        data = request_booking(
            "PATCH",
            f"/api/internal/tasks/{int(task_id)}",
            params={"group_id": require_group_id(group_id)},
            json=patch,
        )
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def tasks_batch_update(updates_json: str, group_id: str = "") -> str:
        """Batch update: updates_json is JSON array of {id, ...fields}."""
        try:
            updates = json.loads(updates_json or "[]")
        except json.JSONDecodeError as e:
            raise ValueError(f"invalid updates_json: {e}") from e
        if not isinstance(updates, list):
            raise ValueError("updates_json must be an array")
        data = request_booking(
            "POST",
            "/api/internal/tasks/batch",
            json={"group_id": require_group_id(group_id), "updates": updates},
        )
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def tasks_complete(task_id: int, group_id: str = "") -> str:
        """Mark task done (releases calendar hold)."""
        data = request_booking(
            "PATCH",
            f"/api/internal/tasks/{int(task_id)}",
            params={"group_id": require_group_id(group_id)},
            json={"status": "done"},
        )
        return json.dumps(data, ensure_ascii=False, indent=2)

    @mcp.tool()
    def tasks_cancel(task_id: int, group_id: str = "") -> str:
        """Cancel task (releases calendar hold)."""
        data = request_booking(
            "DELETE",
            f"/api/internal/tasks/{int(task_id)}",
            params={"group_id": require_group_id(group_id)},
        )
        return json.dumps(data, ensure_ascii=False, indent=2)
