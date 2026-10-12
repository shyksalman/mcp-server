from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ClickUpTask(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    name: str
    status: str | None = None
    priority: str | None = None
    due_date: datetime | None = None
    url: str | None = None
    list_name: str | None = Field(default=None, serialization_alias="list", validation_alias="list")
    project: str | None = None
    assignees: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    comments: list[dict[str, Any]] = Field(default_factory=list)


class TaskList(BaseModel):
    tasks: list[ClickUpTask]


class TaskSummary(BaseModel):
    total_open: int = 0
    high_priority: int = 0
    overdue: int = 0
    due_today: int = 0
    due_this_week: int = 0
