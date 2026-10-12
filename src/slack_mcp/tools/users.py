from slack_mcp.client import SlackClient
from slack_mcp.services.users import find_user, list_users


async def list_slack_users(client: SlackClient, query: str | None, include_deactivated: bool) -> dict:
    return await list_users(client, query, include_deactivated)


async def find_slack_user(client: SlackClient, name_or_email: str) -> dict:
    return await find_user(client, name_or_email)
