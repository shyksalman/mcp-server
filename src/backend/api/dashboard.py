from datetime import datetime
from zoneinfo import ZoneInfo
import json

from fastapi import APIRouter, Depends

from assistant.mcp_client import MultiMCPClient
from assistant.tool_adapter import result_for_model
from backend.dependencies import mcp

router = APIRouter(prefix="/api", tags=["dashboard"])


async def _safe_tool(client: MultiMCPClient, name: str, args: dict | None = None) -> dict:
    try:
        result = await client.call_tool(name, args or {})
        return json.loads(result_for_model(result) or "{}")
    except Exception:
        return {"unavailable": True}


@router.get("/dashboard")
async def dashboard(client: MultiMCPClient = Depends(mcp)) -> dict:
    tz = ZoneInfo("Asia/Karachi")
    today = datetime.now(tz).date().isoformat()
    attendance = await _safe_tool(client, "get_my_attendance_stats")
    leaves = await _safe_tool(client, "get_my_leave_summary")
    meetings = await _safe_tool(client, "list_my_meetings", {"start_date": today, "end_date": today, "limit": 20})
    task_summary = await _safe_tool(client, "get_task_summary")
    due_today = await _safe_tool(client, "get_tasks_due_today")
    slack_activity = await _safe_tool(client, "get_recent_slack_activity", {"limit_per_conversation": 5})
    meeting_count = len(meetings.get("meetings", []))
    due_count = len(due_today.get("tasks", []))
    slack_threads = 0
    for item in slack_activity.get("activity", []):
        slack_threads += len([message for message in item.get("messages", []) if message.get("reply_count", 0) > 0])
    brief = (
        f"You have {meeting_count} meeting{'s' if meeting_count != 1 else ''} today, "
        f"{due_count} ClickUp task{'s' if due_count != 1 else ''} due today, "
        f"{task_summary.get('high_priority', 0)} high-priority task{'s' if task_summary.get('high_priority', 0) != 1 else ''}, "
        f"and {slack_threads} recent Slack thread{'s' if slack_threads != 1 else ''} with replies."
    )
    return {
        "attendance": attendance,
        "leave_balance": leaves,
        "meetings_today": meetings,
        "clickup_summary": task_summary,
        "tasks_due_today": due_today,
        "slack_activity": slack_activity,
        "ai_daily_brief": brief,
    }
