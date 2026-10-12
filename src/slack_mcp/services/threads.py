from datetime import datetime

from slack_mcp.client import SlackClient
from slack_mcp.services.messages import _slack_ts


async def get_thread(client: SlackClient, conversation_id: str, thread_ts: str, limit: int) -> dict:
    replies = await client.thread_replies(conversation_id, thread_ts, limit)
    parent = replies[0].model_dump(mode="json", by_alias=True) if replies else {}
    return {
        "parent": parent,
        "replies": [item.model_dump(mode="json", by_alias=True) for item in replies[1:]],
        "reply_count": max(0, len(replies) - 1),
    }


async def list_threads(
    client: SlackClient,
    conversation_id: str,
    start_date: datetime | None,
    end_date: datetime | None,
    limit: int,
) -> dict:
    messages, _ = await client.conversation_history(conversation_id, limit, _slack_ts(start_date), _slack_ts(end_date))
    threads = [
        {
            "thread_ts": item.thread_ts or item.ts,
            "author": item.user_name,
            "text": item.text,
            "reply_count": item.reply_count,
            "latest_reply": item.raw_metadata.get("latest_reply"),
        }
        for item in messages
        if item.reply_count > 0
    ]
    return {"threads": threads}


async def summarize_thread(client: SlackClient, conversation_id: str, thread_ts: str) -> dict:
    return await get_thread(client, conversation_id, thread_ts, 100)


async def action_items(client: SlackClient, conversation_id: str, thread_ts: str) -> dict:
    payload = await get_thread(client, conversation_id, thread_ts, 100)
    return {"messages": [payload["parent"], *payload["replies"]], "instruction": "Summarize likely action items from these Slack messages."}
