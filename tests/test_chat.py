from types import SimpleNamespace

import pytest

from assistant.chat import ChatSession
from assistant.tool_adapter import result_for_model, to_ollama_tool
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
