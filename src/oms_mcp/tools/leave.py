from typing import Any

from oms_mcp.exceptions import OMSError
from oms_mcp.oms.client import OMSClient
from oms_mcp.schemas import ToolError


async def leaves(client: OMSClient, page: int = 1, size: int = 10) -> dict[str, Any]:
    try:
        return (await client.get_leaves(page, size)).model_dump()
    except (OMSError, ValueError) as exc:
        return ToolError(error=str(exc)).model_dump()


async def leave_summary(client: OMSClient) -> dict[str, Any]:
    try:
        return (await client.get_leave_summary()).model_dump()
    except (OMSError, ValueError) as exc:
        return ToolError(error=str(exc)).model_dump()
