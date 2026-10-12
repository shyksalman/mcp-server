from fastapi import APIRouter, Depends, HTTPException, Query
import json

from assistant.mcp_client import MultiMCPClient
from assistant.tool_adapter import result_for_model
from backend.dependencies import mcp

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/tasks")
async def tasks(
    filter: str = Query(default="all"),
    search: str | None = None,
    client: MultiMCPClient = Depends(mcp),
) -> dict:
    tool = {
        "due_today": "get_tasks_due_today",
        "overdue": "get_overdue_tasks",
        "high_priority": "get_high_priority_tasks",
    }.get(filter, "get_my_clickup_tasks")
    args = {"limit": 100} if tool == "get_my_clickup_tasks" else {}
    if filter in {"open", "in_progress", "completed"} and tool == "get_my_clickup_tasks":
        args["status"] = filter.replace("_", " ")
    try:
        result = await client.call_tool(tool, args)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="ClickUp is unavailable") from exc
    payload = json.loads(result_for_model(result) or "{}")
    if search:
        needle = search.lower()
        payload["tasks"] = [item for item in payload.get("tasks", []) if needle in item.get("name", "").lower()]
    return payload
