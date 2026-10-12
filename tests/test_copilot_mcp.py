from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from assistant.chat import ChatSession
from calendar_mcp.providers.local import LocalCalendarProvider
from clickup_mcp.client import normalize_task


def response(content="", calls=None):
    return SimpleNamespace(role="assistant", content=content, tool_calls=calls)


def call(name, args=None):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=args or {}))


class FakeOllama:
    def __init__(self, responses):
        self.responses = responses

    async def chat(self, messages, tools):
        return SimpleNamespace(message=self.responses.pop(0))


class FakeMCP:
    def __init__(self):
        self.tools = [
            SimpleNamespace(
                name="create_meeting",
                description="Create a meeting",
                inputSchema={"type": "object", "properties": {"title": {"type": "string"}}},
            )
        ]
        self.called = []

    async def call_tool(self, name, args):
        self.called.append((name, args))
        return SimpleNamespace(structuredContent={"success": True, "meeting": {"title": args["title"]}})


@pytest.mark.asyncio
async def test_calendar_local_provider_availability_and_creation() -> None:
    provider = LocalCalendarProvider("UTC")
    start = datetime.now(UTC).replace(hour=16, minute=0, second=0, microsecond=0) + timedelta(days=3)
    end = start + timedelta(minutes=30)
    assert (await provider.check_availability(start, end)).available is True
    created = await provider.create_meeting("Project Review", start, end, ["ali@example.com"], None, None, True)
    assert created.title == "Project Review"
    availability = await provider.check_availability(start, end)
    assert availability.available is False
    assert availability.conflicts[0].id == created.id


def test_clickup_task_normalization_uses_public_list_field() -> None:
    task = normalize_task(
        {
            "id": "ABC-123",
            "name": "Fix payroll export",
            "status": {"status": "open"},
            "priority": {"priority": "high"},
            "due_date": "1735689600000",
            "list": {"name": "Payroll"},
            "project": {"name": "OMS"},
            "assignees": [{"username": "Ali"}],
        }
    )
    payload = task.model_dump(mode="json", by_alias=True)
    assert payload["list"] == "Payroll"
    assert payload["priority"] == "high"
    assert payload["assignees"] == ["Ali"]


@pytest.mark.asyncio
async def test_create_meeting_requires_confirmation_before_tool_execution() -> None:
    mcp = FakeMCP()
    chat = ChatSession(
        FakeOllama(
            [
                response(calls=[call("create_meeting", {"title": "Meeting with Ali"})]),
                response("Please confirm Meeting with Ali."),
                response("Meeting created successfully."),
            ]
        ),
        mcp,
    )
    assert await chat.ask("Create a meeting with Ali") == "Please confirm Meeting with Ali."
    assert mcp.called == []
    assert await chat.ask("yes") == "Meeting created successfully."
    assert mcp.called == [("create_meeting", {"title": "Meeting with Ali"})]
