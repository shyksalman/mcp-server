from datetime import date, datetime
from typing import Any

from calendar_mcp.providers.base import CalendarProvider


async def availability(provider: CalendarProvider, start_datetime: datetime, end_datetime: datetime) -> dict[str, Any]:
    result = await provider.check_availability(start_datetime, end_datetime)
    return result.model_dump(mode="json")


async def free_slots(
    provider: CalendarProvider,
    day: date,
    duration_minutes: int,
    working_hours_start: str,
    working_hours_end: str,
) -> dict[str, Any]:
    result = await provider.find_free_slots(day, duration_minutes, working_hours_start, working_hours_end)
    return result.model_dump(mode="json")
