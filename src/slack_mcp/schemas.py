from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SlackUser(BaseModel):
    id: str
    display_name: str | None = None
    real_name: str | None = None
    email: str | None = None
    deleted: bool = False


class SlackConversation(BaseModel):
    id: str
    name: str | None = None
    type: str
    is_member: bool = False
    latest_message: str | None = None
    latest_timestamp: str | None = None
    unread_count: int | None = None


class SlackMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    ts: str
    date_time: datetime | None = Field(default=None, serialization_alias="datetime", validation_alias="datetime")
    user_id: str | None = None
    user_name: str | None = None
    text: str = ""
    thread_ts: str | None = None
    reply_count: int = 0
    raw_metadata: dict[str, Any] = Field(default_factory=dict)


class SlackSendResult(BaseModel):
    user: str | None = None
    user_id: str | None = None
    channel_id: str | None = None
    message_ts: str | None = None
    message_url: str | None = None
    success: bool
    error: str | None = None


class SlackPreparedMessage(BaseModel):
    recipients: list[SlackUser]
    unresolved: list[str] = Field(default_factory=list)
    ambiguous: dict[str, list[SlackUser]] = Field(default_factory=dict)
    delivery_mode: Literal["individual", "group"]
    message: str
    requires_confirmation: bool = True
