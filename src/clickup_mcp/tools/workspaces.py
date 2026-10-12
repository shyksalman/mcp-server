from typing import Any

from clickup_mcp.client import ClickUpClient


async def workspace_status(client: ClickUpClient) -> dict[str, Any]:
    return {"configured": client.configured}
