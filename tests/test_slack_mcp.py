from types import SimpleNamespace

import pytest

from assistant.chat import ChatSession
from slack_mcp.client import SlackClient, normalize_conversation, normalize_message, normalize_user
from slack_mcp.config import SlackSettings
from slack_mcp.exceptions import SlackRateLimitError
from slack_mcp.server import mcp
from slack_mcp.services.messages import send_to_users
from slack_mcp.services.users import find_user


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
                name="send_slack_message_to_users",
                description="Send Slack DMs",
                inputSchema={"type": "object", "properties": {"user_ids": {"type": "array"}}},
            )
        ]
        self.called = []

    async def call_tool(self, name, args):
        self.called.append((name, args))
        return SimpleNamespace(structuredContent={"sent": len(args["user_ids"]), "failed": 0})


class FakeSlackClient:
    def __init__(self):
        self.settings = SlackSettings(slack_bot_token="xoxb-test", slack_max_bulk_recipients=20, _env_file=None)
        self.users = [
            normalize_user({"id": "U1", "name": "ali", "profile": {"display_name": "Ali", "real_name": "Ali Ahmed", "email": "ali@example.com"}}),
            normalize_user({"id": "U2", "name": "ali-k", "profile": {"display_name": "Ali", "real_name": "Ali Khan", "email": "ali.k@example.com"}}),
            normalize_user({"id": "U3", "name": "ravi", "profile": {"display_name": "Ravi", "real_name": "Ravi Kumar", "email": "ravi@example.com"}}),
        ]
        self.opened = []
        self.posted = []

    async def list_users(self, include_deactivated=False, cursor=None, limit=200):
        return self.users, None

    async def open_conversation(self, user_ids):
        self.opened.append(user_ids)
        return normalize_conversation({"id": f"D{user_ids[0]}", "is_im": True, "user": user_ids[0]})

    async def post_message(self, channel_id, message):
        self.posted.append((channel_id, message))
        if channel_id == "DU2":
            raise RuntimeError("message rejected")
        return {"ts": f"1.{len(self.posted)}"}

    async def get_permalink(self, channel_id, message_ts):
        return f"https://slack.test/{channel_id}/{message_ts}"


def test_slack_normalizers() -> None:
    user = normalize_user({"id": "U1", "profile": {"display_name": "Ali", "email": "ali@example.com"}})
    assert user.display_name == "Ali"
    conversation = normalize_conversation({"id": "C1", "name": "backend", "is_member": True, "latest": {"text": "done", "ts": "1.0"}})
    assert conversation.type == "public_channel"
    message = normalize_message({"ts": "1735689600.0", "user": "U1", "text": "hello", "reply_count": 2}, {"U1": "Ali"})
    assert message.user_name == "Ali"
    assert message.reply_count == 2


@pytest.mark.asyncio
async def test_find_user_exact_and_ambiguous() -> None:
    client = FakeSlackClient()
    exact = await find_user(client, "ravi@example.com")
    assert exact["found"] is True
    assert exact["user"]["id"] == "U3"
    ambiguous = await find_user(client, "Ali")
    assert ambiguous["found"] is False
    assert ambiguous["ambiguous"] is True
    assert len(ambiguous["candidates"]) == 2


@pytest.mark.asyncio
async def test_individual_multi_user_fanout_partial_failure() -> None:
    class PartialFailureClient(FakeSlackClient):
        async def post_message(self, channel_id, message):
            self.posted.append((channel_id, message))
            if channel_id == "DU2":
                from slack_mcp.exceptions import SlackMCPError

                raise SlackMCPError("message rejected")
            return {"ts": f"1.{len(self.posted)}"}

    client = PartialFailureClient()
    result = await send_to_users(client, ["U1", "U2", "U3"], "Deployment done", "individual")
    assert client.opened == [["U1"], ["U2"], ["U3"]]
    assert result["requested"] == 3
    assert result["sent"] == 2
    assert result["failed"] == 1


@pytest.mark.asyncio
async def test_slack_rate_limit_from_http(monkeypatch) -> None:
    class Response:
        status_code = 429
        headers = {"Retry-After": "12"}

        def json(self):
            return {"ok": False}

    class HTTP:
        async def post(self, *args, **kwargs):
            return Response()

    client = SlackClient(SlackSettings(slack_bot_token="xoxb-test", _env_file=None), http=HTTP(), sdk_client=None)
    with pytest.raises(SlackRateLimitError) as error:
        await client.api_call("users.list")
    assert error.value.retry_after == 12


def test_slack_mcp_discovery() -> None:
    registered = {item.name for item in mcp._tool_manager.list_tools()}
    assert {"find_slack_user", "send_slack_message_to_users", "get_slack_thread", "search_slack_messages"} <= registered


@pytest.mark.asyncio
async def test_slack_send_requires_confirmation() -> None:
    mcp_client = FakeMCP()
    chat = ChatSession(
        FakeOllama(
            [
                response(calls=[call("send_slack_message_to_users", {"user_ids": ["U1", "U2"], "message": "Done", "mode": "individual"})]),
                response("Send two individual Slack DMs?"),
                response("Sent 2 Slack messages."),
            ]
        ),
        mcp_client,
    )
    assert await chat.ask("Send Ali and Ahmed individually") == "Send two individual Slack DMs?"
    assert mcp_client.called == []
    assert await chat.ask("confirm") == "Sent 2 Slack messages."
    assert mcp_client.called == [("send_slack_message_to_users", {"user_ids": ["U1", "U2"], "message": "Done", "mode": "individual"})]
