from datetime import datetime

from slack_mcp.client import SlackClient


def _format_date_filter(prefix: str, value: datetime | None) -> str:
    return f" {prefix}:{value.date().isoformat()}" if value else ""


async def search_messages(
    client: SlackClient,
    query: str,
    conversation_id: str | None,
    user_id: str | None,
    start_date: datetime | None,
    end_date: datetime | None,
    limit: int,
) -> dict:
    slack_query = query
    if conversation_id:
        slack_query += f" in:{conversation_id}"
    if user_id:
        slack_query += f" from:<@{user_id}>"
    slack_query += _format_date_filter("after", start_date)
    slack_query += _format_date_filter("before", end_date)
    matches = await client.search_messages(slack_query, limit)
    return {"query": slack_query, "messages": matches[:limit]}
