from datetime import datetime

from slack_mcp.client import SlackClient
from slack_mcp.exceptions import SlackBulkLimitError, SlackMCPError
from slack_mcp.schemas import SlackSendResult


def _slack_ts(value: datetime | None) -> str | None:
    return str(value.timestamp()) if value else None


async def send_dm(client: SlackClient, user_id: str, message: str) -> dict:
    conversation = await client.open_conversation([user_id])
    posted = await client.post_message(conversation.id, message)
    message_ts = posted.get("ts")
    return {
        "success": True,
        "recipient": {"id": user_id, "name": user_id},
        "channel_id": conversation.id,
        "message_ts": message_ts,
        "message_url": await client.get_permalink(conversation.id, message_ts) if message_ts else None,
    }


async def send_to_users(client: SlackClient, user_ids: list[str], message: str, mode: str) -> dict:
    if mode != "individual":
        raise ValueError("mode must be individual")
    if len(user_ids) > client.settings.slack_max_bulk_recipients:
        raise SlackBulkLimitError("Too many Slack recipients for one request")
    results: list[SlackSendResult] = []
    for user_id in user_ids:
        try:
            sent = await send_dm(client, user_id, message)
            results.append(SlackSendResult(user_id=user_id, user=user_id, channel_id=sent["channel_id"], message_ts=sent["message_ts"], message_url=sent["message_url"], success=True))
        except SlackMCPError as exc:
            results.append(SlackSendResult(user_id=user_id, user=user_id, success=False, error=str(exc)))
    return {
        "requested": len(user_ids),
        "sent": len([item for item in results if item.success]),
        "failed": len([item for item in results if not item.success]),
        "results": [item.model_dump(mode="json") for item in results],
    }


async def send_group(client: SlackClient, user_ids: list[str], message: str) -> dict:
    if len(user_ids) > client.settings.slack_max_bulk_recipients:
        raise SlackBulkLimitError("Too many Slack recipients for one request")
    conversation = await client.open_conversation(user_ids)
    posted = await client.post_message(conversation.id, message)
    message_ts = posted.get("ts")
    return {
        "success": True,
        "requested": len(user_ids),
        "delivery_mode": "group",
        "channel_id": conversation.id,
        "message_ts": message_ts,
        "message_url": await client.get_permalink(conversation.id, message_ts) if message_ts else None,
    }


async def post_channel_message(client: SlackClient, conversation_id: str, message: str) -> dict:
    posted = await client.post_message(conversation_id, message)
    message_ts = posted.get("ts")
    return {
        "success": True,
        "conversation_id": conversation_id,
        "message_ts": message_ts,
        "message_url": await client.get_permalink(conversation_id, message_ts) if message_ts else None,
    }


async def get_messages(
    client: SlackClient,
    conversation_id: str,
    limit: int,
    oldest: datetime | None,
    latest: datetime | None,
    cursor: str | None,
) -> dict:
    messages, next_cursor = await client.conversation_history(conversation_id, limit, _slack_ts(oldest), _slack_ts(latest), cursor)
    return {
        "conversation": {"id": conversation_id},
        "messages": [item.model_dump(mode="json", by_alias=True) for item in messages],
        "next_cursor": next_cursor,
    }


async def recent_activity(client: SlackClient, limit_per_conversation: int) -> dict:
    conversations, _ = await client.list_conversations(["public_channel", "private_channel", "im", "mpim"], 20)
    activity = []
    for conversation in conversations[:10]:
        try:
            messages, _ = await client.conversation_history(conversation.id, limit_per_conversation)
            activity.append({"conversation": conversation.model_dump(mode="json"), "messages": [item.model_dump(mode="json", by_alias=True) for item in messages]})
        except SlackMCPError as exc:
            activity.append({"conversation": conversation.model_dump(mode="json"), "error": str(exc)})
    return {"activity": activity}
