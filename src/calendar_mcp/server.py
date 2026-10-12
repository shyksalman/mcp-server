import logging
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from calendar_mcp.config import load_settings
from calendar_mcp.providers import build_provider
from calendar_mcp.providers.base import CalendarProvider
from calendar_mcp.tools.availability import availability, free_slots
from calendar_mcp.tools.meetings import create, list_meetings, meeting

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
_provider: CalendarProvider | None = None


@asynccontextmanager
async def lifespan(_: FastMCP):
    global _provider
    _provider = build_provider(load_settings())
    try:
        yield
    finally:
        _provider = None


mcp = FastMCP("Employee calendar", lifespan=lifespan)


def provider() -> CalendarProvider:
    if _provider is None:
        raise RuntimeError("Calendar provider is not initialized")
    return _provider


@mcp.tool()
async def list_my_meetings(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = Field(default=20, ge=1, le=100),
) -> dict[str, Any]:
    """Retrieve meetings/events from the authenticated user's calendar. Use for today's meetings, tomorrow's meetings, this week, next meeting, or anything scheduled at a date/time."""
    log.info("MCP tool called: list_my_meetings")
    return await list_meetings(provider(), start_date, end_date, limit)


@mcp.tool()
async def get_meeting(meeting_id: str) -> dict[str, Any]:
    """Get detailed meeting information including attendees, location, organizer, and meeting link."""
    log.info("MCP tool called: get_meeting")
    return await meeting(provider(), meeting_id)


@mcp.tool()
async def create_meeting(
    title: str,
    start_datetime: datetime,
    end_datetime: datetime,
    attendees: list[str] = Field(default_factory=list),
    description: str | None = None,
    location: str | None = None,
    create_video_meeting: bool = True,
) -> dict[str, Any]:
    """Create a calendar meeting only after explicit user confirmation. Use for scheduling or creating meetings."""
    log.info("MCP tool called: create_meeting")
    return await create(
        provider(),
        title,
        start_datetime,
        end_datetime,
        attendees,
        description,
        location,
        create_video_meeting,
    )


@mcp.tool()
async def check_calendar_availability(start_datetime: datetime, end_datetime: datetime) -> dict[str, Any]:
    """Check if the user's calendar is free for a proposed time and return any conflicting meetings."""
    log.info("MCP tool called: check_calendar_availability")
    return await availability(provider(), start_datetime, end_datetime)


@mcp.tool()
async def find_free_slots(
    date: date,
    duration_minutes: int = Field(ge=1, le=480),
    working_hours_start: str = "09:00",
    working_hours_end: str = "18:00",
) -> dict[str, Any]:
    """Find available calendar slots on a date for the requested duration."""
    log.info("MCP tool called: find_free_slots")
    return await free_slots(provider(), date, duration_minutes, working_hours_start, working_hours_end)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
