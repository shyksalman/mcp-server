from datetime import datetime

from slack_mcp.client import SlackClient
from slack_mcp.services.search import search_messages


async def search_slack_messages(
    client: SlackClient,
    query: str,
    conversation_id: str | None,
    user_id: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
    limit: int,
) -> dict:
    return await search_messages(client, query, conversation_id, user_id, start_date, end_date, limit)
