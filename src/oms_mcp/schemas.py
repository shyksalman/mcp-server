from typing import Any

from pydantic import BaseModel, Field


class AttendanceStats(BaseModel):
    name: str | None = None
    designation_name: str | None = None
    attendance_list: list | None = None
    raw: Any = None


class LeaveRequest(BaseModel):
    id: str | int | None = None
    status: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class LeaveList(BaseModel):
    requests: list[LeaveRequest] = Field(default_factory=list)
    page: int
    size: int
    raw: Any = None


class LeaveSummary(BaseModel):
    available: int | float | None = None
    consumed: int | float | None = None
    remaining: int | float | None = None
    raw: Any = None


class ToolError(BaseModel):
    success: bool = False
    error: str
