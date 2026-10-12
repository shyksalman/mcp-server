from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: UUID | None = None


class ChatResponse(BaseModel):
    message: str
    conversation_id: UUID


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class ChatHistory(BaseModel):
    conversation_id: UUID
    messages: list[HistoryMessage]
