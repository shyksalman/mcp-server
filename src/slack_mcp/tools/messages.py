from datetime import datetime

from slack_mcp.client import SlackClient
from slack_mcp.services.messages import get_messages, post_channel_message, recent_activity, send_dm, send_group, send_to_users
from slack_mcp.services.users import find_user


async def send_slack_dm(client: SlackClient, user_id: str, message: str) -> dict:
    return await send_dm(client, user_id, message)


async def send_slack_message_to_users(client: SlackClient, user_ids: list[str], message: str, mode: str) -> dict:
    return await send_to_users(client, user_ids, message, mode)


async def send_slack_group_message(client: SlackClient, user_ids: list[str], message: str) -> dict:
    return await send_group(client, user_ids, message)


async def post_slack_channel_message(client: SlackClient, conversation_id: str, message: str) -> dict:
    return await post_channel_message(client, conversation_id, message)


async def prepare_slack_message(client: SlackClient, recipients: list[str], message: str, delivery_mode: str) -> dict:
    resolved = []
    unresolved = []
    ambiguous = {}
    for recipient in recipients:
        lookup = await find_user(client, recipient)
        if lookup.get("found"):
            resolved.append(lookup["user"])
        elif lookup.get("ambiguous"):
            ambiguous[recipient] = lookup.get("candidates", [])
        else:
            unresolved.append(recipient)
    return {
        "recipients": resolved,
        "unresolved": unresolved,
        "ambiguous": ambiguous,
        "delivery_mode": delivery_mode,
        "message": message,
        "requires_confirmation": True,
        "next_tool": "send_slack_message_to_users" if delivery_mode == "individual" else "send_slack_group_message",
    }


async def get_slack_messages(
    client: SlackClient,
    conversation_id: str,
    limit: int,
    oldest: datetime | None,
    latest: datetime | None,
    cursor: str | None,
) -> dict:
    return await get_messages(client, conversation_id, limit, oldest, latest, cursor)


async def get_recent_slack_activity(client: SlackClient, limit_per_conversation: int) -> dict:
    return await recent_activity(client, limit_per_conversation)
