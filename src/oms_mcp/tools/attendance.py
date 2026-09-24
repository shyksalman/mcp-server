from typing import Any

from oms_mcp.exceptions import OMSError
from oms_mcp.oms.client import OMSClient
from oms_mcp.schemas import ToolError


async def attendance_stats(client: OMSClient) -> dict[str, Any]:
    try:
        return (await client.get_attendance_stats()).model_dump()
    except (OMSError, ValueError) as exc:
        return ToolError(error=str(exc)).model_dump()
