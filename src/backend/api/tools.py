from fastapi import APIRouter, Depends

from assistant.mcp_client import MultiMCPClient
from backend.agent.tool_registry import public_tool
from backend.dependencies import mcp

router = APIRouter(prefix="/api", tags=["tools"])


@router.get("/tools")
async def get_tools(client: MultiMCPClient = Depends(mcp)) -> dict:
    return {
        "tools": [public_tool(tool) for tool in client.tools],
        "unavailable": client.unavailable,
    }
