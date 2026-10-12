from datetime import date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from calendar_mcp.exceptions import CalendarError
from calendar_mcp.providers.base import CalendarProvider
from calendar_mcp.schemas import Availability, FreeSlot, FreeSlotList, Meeting, MeetingList


class LocalCalendarProvider(CalendarProvider):
    """Small local provider used for development and tests.

    Real Google or Microsoft implementations can replace this class without
    changing MCP tools or backend orchestration.
    """

    def __init__(self, timezone: str):
        self.timezone = timezone
        self._tz = ZoneInfo(timezone)
        self._meetings: dict[str, Meeting] = {}
        self._seed()

    def _seed(self) -> None:
        if self._meetings:
            return
        today = datetime.now(self._tz).date()
        samples = [
            ("Daily Standup", time(10, 0), 30, ["team@enigmatix.local"]),
            ("Project Review", time(14, 0), 45, ["ali@enigmatix.local"]),
            ("Planning Sync", time(11, 30), 30, ["pm@enigmatix.local"]),
        ]
        for index, (title, start_time, minutes, attendees) in enumerate(samples):
            day = today if index < 2 else today + timedelta(days=1)
            start = datetime.combine(day, start_time, self._tz)
            end = start + timedelta(minutes=minutes)
            meeting = Meeting(
                id=f"local-{index + 1}",
                title=title,
                start=start,
                end=end,
                timezone=self.timezone,
                location="Conference Room" if index == 1 else None,
                meeting_url="https://meet.example.com/local",
                organizer="you@enigmatix.local",
                attendees=attendees,
            )
            self._meetings[meeting.id] = meeting

    async def list_meetings(self, start_date: date | None, end_date: date | None, limit: int) -> MeetingList:
        start_date = start_date or datetime.now(self._tz).date()
        end_date = end_date or start_date
        meetings = [
            item
            for item in self._meetings.values()
            if start_date <= item.start.astimezone(self._tz).date() <= end_date
        ]
        meetings.sort(key=lambda item: item.start)
        return MeetingList(meetings=meetings[:limit])

    async def get_meeting(self, meeting_id: str) -> Meeting:
        try:
            return self._meetings[meeting_id]
        except KeyError as exc:
            raise CalendarError("Meeting was not found") from exc

    async def create_meeting(
        self,
        title: str,
        start_datetime: datetime,
        end_datetime: datetime,
        attendees: list[str],
        description: str | None,
        location: str | None,
        create_video_meeting: bool,
    ) -> Meeting:
        if end_datetime <= start_datetime:
            raise CalendarError("Meeting end time must be after the start time")
        meeting_url = f"https://meet.example.com/{uuid4().hex[:10]}" if create_video_meeting else None
        meeting = Meeting(
            id=f"local-{uuid4().hex}",
            title=title,
            start=start_datetime,
            end=end_datetime,
            timezone=self.timezone,
            location=location,
            meeting_url=meeting_url,
            organizer="you@enigmatix.local",
            attendees=attendees,
            description=description,
        )
        self._meetings[meeting.id] = meeting
        return meeting

    async def check_availability(self, start_datetime: datetime, end_datetime: datetime) -> Availability:
        conflicts = [
            item
            for item in self._meetings.values()
            if start_datetime < item.end and end_datetime > item.start
        ]
        conflicts.sort(key=lambda item: item.start)
        return Availability(available=not conflicts, conflicts=conflicts)

    async def find_free_slots(
        self,
        day: date,
        duration_minutes: int,
        working_hours_start: str,
        working_hours_end: str,
    ) -> FreeSlotList:
        start_time = time.fromisoformat(working_hours_start)
        end_time = time.fromisoformat(working_hours_end)
        cursor = datetime.combine(day, start_time, self._tz)
        boundary = datetime.combine(day, end_time, self._tz)
        duration = timedelta(minutes=duration_minutes)
        slots: list[FreeSlot] = []
        while cursor + duration <= boundary and len(slots) < 10:
            end = cursor + duration
            availability = await self.check_availability(cursor, end)
            if availability.available:
                slots.append(FreeSlot(start=cursor, end=end, timezone=self.timezone))
            cursor += timedelta(minutes=30)
        return FreeSlotList(slots=slots)
