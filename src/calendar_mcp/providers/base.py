from abc import ABC, abstractmethod
from datetime import date, datetime

from calendar_mcp.schemas import Availability, FreeSlotList, Meeting, MeetingList


class CalendarProvider(ABC):
    @abstractmethod
    async def list_meetings(self, start_date: date | None, end_date: date | None, limit: int) -> MeetingList:
        raise NotImplementedError

    @abstractmethod
    async def get_meeting(self, meeting_id: str) -> Meeting:
        raise NotImplementedError

    @abstractmethod
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
        raise NotImplementedError

    @abstractmethod
    async def check_availability(self, start_datetime: datetime, end_datetime: datetime) -> Availability:
        raise NotImplementedError

    @abstractmethod
    async def find_free_slots(
        self,
        day: date,
        duration_minutes: int,
        working_hours_start: str,
        working_hours_end: str,
    ) -> FreeSlotList:
        raise NotImplementedError
