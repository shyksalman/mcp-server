from datetime import datetime

from pydantic import BaseModel, Field


class Meeting(BaseModel):
    id: str
    title: str
    start: datetime
    end: datetime
    timezone: str
    location: str | None = None
    meeting_url: str | None = None
    organizer: str | None = None
    attendees: list[str] = Field(default_factory=list)
    description: str | None = None


class MeetingList(BaseModel):
    meetings: list[Meeting]


class Availability(BaseModel):
    available: bool
    conflicts: list[Meeting] = Field(default_factory=list)


class FreeSlot(BaseModel):
    start: datetime
    end: datetime
    timezone: str


class FreeSlotList(BaseModel):
    slots: list[FreeSlot]
