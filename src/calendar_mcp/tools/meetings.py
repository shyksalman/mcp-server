from datetime import date, datetime
from typing import Any

from calendar_mcp.providers.base import CalendarProvider


async def list_meetings(
    provider: CalendarProvider,
    start_date: date | None,
    end_date: date | None,
    limit: int,
) -> dict[str, Any]:
    result = await provider.list_meetings(start_date, end_date, limit)
    return result.model_dump(mode="json")


async def meeting(provider: CalendarProvider, meeting_id: str) -> dict[str, Any]:
    result = await provider.get_meeting(meeting_id)
    return result.model_dump(mode="json")


async def create(
    provider: CalendarProvider,
    title: str,
    start_datetime: datetime,
    end_datetime: datetime,
    attendees: list[str],
    description: str | None,
    location: str | None,
    create_video_meeting: bool,
) -> dict[str, Any]:
    result = await provider.create_meeting(
        title,
        start_datetime,
        end_datetime,
        attendees,
        description,
        location,
        create_video_meeting,
    )
    return {"success": True, "meeting": result.model_dump(mode="json")}
