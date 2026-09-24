import logging
from contextlib import asynccontextmanager
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from oms_mcp.config import load_settings
from oms_mcp.oms.client import OMSClient
from oms_mcp.tools.attendance import attendance_stats
from oms_mcp.tools.leave import leave_summary, leaves

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
_client: OMSClient | None = None


@asynccontextmanager
async def lifespan(_: FastMCP):
    global _client
    async with OMSClient(load_settings()) as client:
        _client = client
        try:
            yield
        finally:
            _client = None


mcp = FastMCP("Enigmatix OMS personal assistant", lifespan=lifespan)


def client() -> OMSClient:
    if _client is None:
        raise RuntimeError("OMS client is not initialized")
    return _client


@mcp.tool()
async def get_my_attendance_stats() -> dict[str, Any]:
    """Retrieve attendance statistics for the currently authenticated OMS employee. Use for attendance, presence, absence, lateness, or an attendance summary."""
    log.info("MCP tool called: get_my_attendance_stats")
    return await attendance_stats(client())


@mcp.tool()
async def get_my_leaves(
    page: int = Field(default=1, ge=1), size: int = Field(default=10, ge=1, le=100)
) -> dict[str, Any]:
    """Retrieve leave requests of the authenticated employee. Use for leave history, pending, approved, rejected, recent, or leave status questions."""
    log.info("MCP tool called: get_my_leaves")
    return await leaves(client(), page, size)


@mcp.tool()
async def get_my_leave_summary() -> dict[str, Any]:
    """Retrieve leave counts or balance for the authenticated employee. Use for available, remaining, consumed, or total leave questions."""
    log.info("MCP tool called: get_my_leave_summary")
    return await leave_summary(client())


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
