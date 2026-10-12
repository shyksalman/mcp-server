from types import SimpleNamespace

import pytest

from assistant.chat import ChatSession, direct_tool_answer, normalize_tool_args
from assistant.tool_adapter import result_for_model, to_ollama_tool
from backend.agent.memory import ConversationMemory
from oms_mcp.server import mcp


def tool(name: str = "get_my_leaves") -> SimpleNamespace:
    return SimpleNamespace(name=name, description="Leave data", inputSchema={"type": "object", "properties": {"size": {"type": "integer"}}})


def test_schema_conversion_and_registration() -> None:
    converted = to_ollama_tool(tool())
    assert converted["function"]["name"] == "get_my_leaves"
    assert converted["function"]["parameters"]["properties"]["size"]["type"] == "integer"
    registered = {item.name for item in mcp._tool_manager.list_tools()}
    assert registered == {"get_my_leaves", "get_my_leave_summary", "get_my_attendance_stats"}


def test_result_conversion() -> None:
    assert '"remaining": 4' in result_for_model(SimpleNamespace(structuredContent={"remaining": 4}))


def test_calendar_today_args_are_normalized() -> None:
    args = normalize_tool_args("list_my_meetings", {"start_date": "2024-01-01"}, "What meetings do I have today?")
    assert args["start_date"] == args["end_date"]
    assert args["limit"] == 20


def test_direct_meeting_answer_from_tool_result() -> None:
    answer = direct_tool_answer(
        "What meetings do I have today?",
        [
            {
                "name": "list_my_meetings",
                "args": {},
                "content": '{"meetings":[{"title":"Daily Standup","start":"2026-09-25T10:00:00+05:00","end":"2026-09-25T10:30:00+05:00"}]}',
            }
        ],
    )
    assert "Daily Standup" in answer
    assert "10:00 - 10:30" in answer


class FakeOllama:
    def __init__(self, responses):
        self.responses = responses
        self.seen = []

    async def chat(self, messages, tools):
        self.seen.append((list(messages), tools))
        return SimpleNamespace(message=self.responses.pop(0))


class FakeMCP:
    def __init__(self):
        self.tools = [tool()]
        self.called = []

    async def call_tool(self, name, args):
        self.called.append((name, args))
        return SimpleNamespace(structuredContent={"requests": [{"status": "pending"}]})


def response(content="", calls=None):
    return SimpleNamespace(role="assistant", content=content, tool_calls=calls)


def call(name="get_my_leaves", args=None):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=args or {}))


@pytest.mark.asyncio
async def test_agent_calls_tool_and_keeps_context() -> None:
    ollama = FakeOllama([response(calls=[call(args={"size": 5}), call(args={"page": 2})]), response("One pending leave."), response("A joke.")])
    mcp_client = FakeMCP()
    chat = ChatSession(ollama, mcp_client)
    assert await chat.ask("Show my leaves") == "One pending leave."
    assert mcp_client.called == [("get_my_leaves", {"size": 5}), ("get_my_leaves", {"page": 2})]
    assert [item.role if hasattr(item, "role") else item["role"] for item in ollama.seen[1][0]][-3:] == ["assistant", "tool", "tool"]
    assert await chat.ask("Tell me a joke") == "A joke."
    assert len(mcp_client.called) == 2
    chat.clear()
    assert len(chat.messages) == 1


@pytest.mark.asyncio
async def test_tool_error_and_iteration_limit() -> None:
    class BrokenMCP(FakeMCP):
        async def call_tool(self, name, args):
            raise RuntimeError("secret detail")

    ollama = FakeOllama([response(calls=[call()]), response("The service failed.")])
    chat = ChatSession(ollama, BrokenMCP())
    assert await chat.ask("My leaves?") == "The service failed."
    assert "secret detail" not in chat.messages[-2]["content"]
    loop = ChatSession(FakeOllama([response(calls=[call()])]), FakeMCP(), max_iterations=1)
    assert "tool-call limit" in await loop.ask("My leaves?")


@pytest.mark.asyncio
async def test_conversation_memory_persists_isolates_and_clears(tmp_path) -> None:
    database = str(tmp_path / "chat-memory.db")
    first_model = FakeOllama([response("You said the project is Atlas.")])
    memory = ConversationMemory(first_model, FakeMCP(), database)

    conversation_id, answer = await memory.ask("Remember that my project is Atlas")
    assert answer == "You said the project is Atlas."
    assert await memory.history(conversation_id) == [
        {"role": "user", "content": "Remember that my project is Atlas"},
        {"role": "assistant", "content": "You said the project is Atlas."},
    ]
    memory.close()

    restored_model = FakeOllama([response("Your project is Atlas."), response("I have no project context.")])
    restored = ConversationMemory(restored_model, FakeMCP(), database)
    same_id, answer = await restored.ask("What is my project?", conversation_id)
    assert same_id == conversation_id
    assert answer == "Your project is Atlas."
    sent_messages = restored_model.seen[0][0]
    assert [item["content"] for item in sent_messages if item["role"] == "user"] == [
        "Remember that my project is Atlas",
        "What is my project?",
    ]

    other_id, _ = await restored.ask("What is my project?")
    assert other_id != conversation_id
    other_messages = restored_model.seen[1][0]
    assert all(item.get("content") != "Remember that my project is Atlas" for item in other_messages)

    await restored.clear(conversation_id)
    assert await restored.history(conversation_id) == []
    restored.close()
