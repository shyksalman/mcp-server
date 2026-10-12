import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from slack_mcp.client import SlackClient
from slack_mcp.config import load_settings
from slack_mcp.exceptions import SlackMCPError
from slack_mcp.tools.conversations import find_slack_conversation as find_conversation_tool
from slack_mcp.tools.conversations import list_slack_conversations as list_conversations_tool
from slack_mcp.tools.messages import (
    get_recent_slack_activity as recent_activity_tool,
    get_slack_messages as get_messages_tool,
    prepare_slack_message as prepare_message_tool,
    post_slack_channel_message as post_channel_tool,
    send_slack_dm as send_dm_tool,
    send_slack_group_message as send_group_tool,
    send_slack_message_to_users as send_to_users_tool,
)
from slack_mcp.tools.search import search_slack_messages as search_messages_tool
from slack_mcp.tools.threads import (
    get_slack_action_items as action_items_tool,
    get_slack_thread as get_thread_tool,
    list_slack_threads as list_threads_tool,
    summarize_slack_thread as summarize_thread_tool,
)
from slack_mcp.tools.users import find_slack_user as find_user_tool
from slack_mcp.tools.users import list_slack_users as list_users_tool

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
_client: SlackClient | None = None


@asynccontextmanager
async def lifespan(_: FastMCP):
    global _client
    async with SlackClient(load_settings()) as client:
        _client = client
        try:
            yield
        finally:
            _client = None


mcp = FastMCP("Slack employee messaging", lifespan=lifespan)


def client() -> SlackClient:
    if _client is None:
        raise RuntimeError("Slack client is not initialized")
    return _client


def safe_error(exc: Exception) -> dict[str, Any]:
    return {"success": False, "error": str(exc)}


@mcp.tool()
async def list_slack_users(query: str | None = None, include_deactivated: bool = False) -> dict[str, Any]:
    """List Slack users visible to the app. Use to find employees by display name, real name, or email before messaging."""
    try:
        return await list_users_tool(client(), query, include_deactivated)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def find_slack_user(name_or_email: str) -> dict[str, Any]:
    """Resolve a Slack user by name, display name, real name, id, or email. Return candidates when the name is ambiguous."""
    try:
        return await find_user_tool(client(), name_or_email)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def prepare_slack_message(
    recipients: list[str],
    message: str,
    delivery_mode: Literal["individual", "group"] = "individual",
) -> dict[str, Any]:
    """Resolve recipient names and prepare a Slack message preview that requires confirmation before sending. Use this before Slack write tools when users give names instead of ids."""
    try:
        return await prepare_message_tool(client(), recipients, message, delivery_mode)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def send_slack_dm(user_id: str, message: str) -> dict[str, Any]:
    """Send a direct Slack message to one user id. This is a write operation and must only run after explicit user confirmation."""
    try:
        return await send_dm_tool(client(), user_id, message)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def send_slack_message_to_users(
    user_ids: list[str],
    message: str,
    mode: Literal["individual"] = "individual",
) -> dict[str, Any]:
    """Send separate individual Slack DMs to each listed user id. One failed recipient should not stop successful sends to others. This write operation requires confirmation."""
    try:
        return await send_to_users_tool(client(), user_ids, message, mode)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def send_slack_group_message(user_ids: list[str], message: str) -> dict[str, Any]:
    """Open or reuse one group DM with all listed user ids and post one Slack message. This write operation requires confirmation."""
    try:
        return await send_group_tool(client(), user_ids, message)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def post_slack_channel_message(conversation_id: str, message: str) -> dict[str, Any]:
    """Post a message to an existing Slack channel/conversation id. This write operation requires confirmation."""
    try:
        return await post_channel_tool(client(), conversation_id, message)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def list_slack_conversations(
    types: list[str] = Field(default_factory=lambda: ["public_channel", "private_channel", "im", "mpim"]),
    limit: int = Field(default=100, ge=1, le=500),
) -> dict[str, Any]:
    """List Slack conversations visible to the app, including channels, private channels, DMs, and group DMs depending on permissions."""
    try:
        return await list_conversations_tool(client(), types, limit)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def find_slack_conversation(name_or_id: str) -> dict[str, Any]:
    """Resolve a Slack conversation/channel by name or id. Return candidates when ambiguous."""
    try:
        return await find_conversation_tool(client(), name_or_id)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def get_slack_messages(
    conversation_id: str,
    limit: int = Field(default=50, ge=1, le=200),
    oldest: datetime | None = None,
    latest: datetime | None = None,
    cursor: str | None = None,
) -> dict[str, Any]:
    """Read recent Slack messages from a conversation the app can access. Supports pagination and optional date bounds."""
    try:
        return await get_messages_tool(client(), conversation_id, limit, oldest, latest, cursor)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def get_slack_thread(
    conversation_id: str,
    thread_ts: str,
    limit: int = Field(default=100, ge=1, le=200),
) -> dict[str, Any]:
    """Read a Slack thread's parent and replies. Use for thread details, summaries, decisions, participants, or action items."""
    try:
        return await get_thread_tool(client(), conversation_id, thread_ts, limit)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def list_slack_threads(
    conversation_id: str,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Field(default=50, ge=1, le=200),
) -> dict[str, Any]:
    """List lightweight Slack thread metadata from a conversation without fetching every reply."""
    try:
        return await list_threads_tool(client(), conversation_id, start_date, end_date, limit)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def search_slack_messages(
    query: str,
    conversation_id: str | None = None,
    user_id: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    limit: int = Field(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """Search authorized Slack messages for tickets, names, project terms, incidents, decisions, or recent discussions."""
    try:
        return await search_messages_tool(client(), query, conversation_id, user_id, start_date, end_date, limit)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def get_recent_slack_activity(limit_per_conversation: int = Field(default=20, ge=1, le=50)) -> dict[str, Any]:
    """Fetch recent Slack activity from a small number of visible conversations. Use for daily briefs or recent discussions without full workspace downloads."""
    try:
        return await recent_activity_tool(client(), limit_per_conversation)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def summarize_slack_thread(conversation_id: str, thread_ts: str) -> dict[str, Any]:
    """Retrieve Slack thread messages so the AI can summarize topic, decisions, open questions, action items, and participants."""
    try:
        return await summarize_thread_tool(client(), conversation_id, thread_ts)
    except SlackMCPError as exc:
        return safe_error(exc)


@mcp.tool()
async def get_slack_action_items(conversation_id: str, thread_ts: str) -> dict[str, Any]:
    """Retrieve Slack thread messages and mark them for action-item extraction by the AI."""
    try:
        return await action_items_tool(client(), conversation_id, thread_ts)
    except SlackMCPError as exc:
        return safe_error(exc)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
