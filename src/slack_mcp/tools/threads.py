from datetime import datetime

from slack_mcp.client import SlackClient
from slack_mcp.services.threads import action_items, get_thread, list_threads, summarize_thread


async def get_slack_thread(client: SlackClient, conversation_id: str, thread_ts: str, limit: int) -> dict:
    return await get_thread(client, conversation_id, thread_ts, limit)


async def list_slack_threads(
    client: SlackClient,
    conversation_id: str,
    start_date: datetime | None,
    end_date: datetime | None,
    limit: int,
) -> dict:
    return await list_threads(client, conversation_id, start_date, end_date, limit)


async def summarize_slack_thread(client: SlackClient, conversation_id: str, thread_ts: str) -> dict:
    return await summarize_thread(client, conversation_id, thread_ts)


async def get_slack_action_items(client: SlackClient, conversation_id: str, thread_ts: str) -> dict:
    return await action_items(client, conversation_id, thread_ts)
