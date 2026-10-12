from slack_mcp.client import SlackClient


async def list_conversations(client: SlackClient, types: list[str], limit: int) -> dict:
    conversations = []
    cursor = None
    while len(conversations) < limit:
        page, cursor = await client.list_conversations(types, min(200, limit - len(conversations)), cursor)
        conversations.extend(page)
        if not cursor:
            break
    return {"conversations": [item.model_dump(mode="json") for item in conversations]}


async def find_conversation(client: SlackClient, name_or_id: str, types: list[str] | None = None) -> dict:
    payload = await list_conversations(client, types or ["public_channel", "private_channel", "im", "mpim"], 500)
    query = name_or_id.strip().lstrip("#").lower()
    matches = [
        item
        for item in payload["conversations"]
        if query in {str(item.get("id", "")).lower(), str(item.get("name", "")).lower()}
    ]
    if len(matches) == 1:
        return {"found": True, "conversation": matches[0], "candidates": []}
    fuzzy = [item for item in payload["conversations"] if query in str(item.get("name", "")).lower()]
    return {
        "found": len(fuzzy) == 1,
        "conversation": fuzzy[0] if len(fuzzy) == 1 else None,
        "candidates": fuzzy[:10],
        "ambiguous": len(fuzzy) > 1,
        "error": "Multiple Slack conversations matched. Ask the user to clarify." if len(fuzzy) > 1 else "Slack conversation was not found.",
    }
