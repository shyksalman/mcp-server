from slack_mcp.client import SlackClient
from slack_mcp.schemas import SlackUser


def _matches(user: SlackUser, query: str) -> bool:
    text = query.lower()
    return any(
        text in (value or "").lower()
        for value in (user.display_name, user.real_name, user.email, user.id)
    )


async def list_users(client: SlackClient, query: str | None, include_deactivated: bool) -> dict:
    users: list[SlackUser] = []
    cursor = None
    while True:
        page, cursor = await client.list_users(include_deactivated=include_deactivated, cursor=cursor)
        users.extend(page)
        if not cursor or len(users) >= 500:
            break
    if query:
        users = [item for item in users if _matches(item, query)]
    return {"users": [item.model_dump(mode="json") for item in users[:100]]}


async def find_user(client: SlackClient, name_or_email: str) -> dict:
    payload = await list_users(client, name_or_email, include_deactivated=False)
    users = payload["users"]
    query = name_or_email.lower()
    exact = [
        item
        for item in users
        if query in {str(item.get("id", "")).lower(), str(item.get("email", "")).lower(), str(item.get("display_name", "")).lower(), str(item.get("real_name", "")).lower()}
    ]
    if len(exact) == 1:
        return {"found": True, "user": exact[0], "candidates": []}
    if len(users) == 1:
        return {"found": True, "user": users[0], "candidates": []}
    return {
        "found": False,
        "ambiguous": len(users) > 1,
        "candidates": users[:10],
        "error": "Multiple Slack users matched. Ask the user to clarify." if len(users) > 1 else "Slack user was not found.",
    }
