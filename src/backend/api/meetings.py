from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query

from assistant.mcp_client import MultiMCPClient
from assistant.tool_adapter import result_for_model
from backend.dependencies import mcp
import json

router = APIRouter(prefix="/api", tags=["meetings"])


@router.get("/meetings")
async def meetings(
    range: str = Query(default="today", pattern="^(today|tomorrow|week|upcoming)$"),
    client: MultiMCPClient = Depends(mcp),
) -> dict:
    tz = ZoneInfo("Asia/Karachi")
    today = datetime.now(tz).date()
    start = today
    end = today
    if range == "tomorrow":
        start = end = today + timedelta(days=1)
    elif range in {"week", "upcoming"}:
        end = today + timedelta(days=7)
    try:
        result = await client.call_tool("list_my_meetings", {"start_date": start.isoformat(), "end_date": end.isoformat(), "limit": 50})
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Calendar is unavailable") from exc
    return json.loads(result_for_model(result) or "{}")
