from slack_mcp.client import SlackClient
from slack_mcp.services.conversations import find_conversation, list_conversations


async def list_slack_conversations(client: SlackClient, types: list[str], limit: int) -> dict:
    return await list_conversations(client, types, limit)


async def find_slack_conversation(client: SlackClient, name_or_id: str) -> dict:
    return await find_conversation(client, name_or_id)
