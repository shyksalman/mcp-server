import logging
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import Field

from clickup_mcp.client import ClickUpClient
from clickup_mcp.config import load_settings
from clickup_mcp.tools.tasks import due_today, high_priority, my_tasks, overdue, summary, task
from clickup_mcp.tools.workspaces import workspace_status

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)
_client: ClickUpClient | None = None


@asynccontextmanager
async def lifespan(_: FastMCP):
    global _client
    async with ClickUpClient(load_settings()) as client:
        _client = client
        try:
            yield
        finally:
            _client = None


mcp = FastMCP("ClickUp employee tasks", lifespan=lifespan)


def client() -> ClickUpClient:
    if _client is None:
        raise RuntimeError("ClickUp client is not initialized")
    return _client


@mcp.tool()
async def get_my_clickup_tasks(
    status: str | None = None,
    priority: str | None = None,
    due_before: datetime | None = None,
    due_after: datetime | None = None,
    limit: int = Field(default=50, ge=1, le=100),
) -> dict[str, Any]:
    """List ClickUp tickets/tasks assigned to the configured user. Use for assigned tickets, open tasks, priority filters, due date filters, overdue work, and ClickUp workload."""
    log.info("MCP tool called: get_my_clickup_tasks")
    return await my_tasks(client(), status, priority, due_before, due_after, limit)


@mcp.tool()
async def get_clickup_task(task_id: str) -> dict[str, Any]:
    """Get full details for a specific ClickUp ticket/task by id."""
    log.info("MCP tool called: get_clickup_task")
    return await task(client(), task_id)


@mcp.tool()
async def get_task_summary() -> dict[str, Any]:
    """Return aggregate ClickUp workload counts for open, high-priority, overdue, due today, and due this week tasks."""
    log.info("MCP tool called: get_task_summary")
    return await summary(client())


@mcp.tool()
async def get_tasks_due_today() -> dict[str, Any]:
    """Return ClickUp tasks assigned to the user that are due today."""
    log.info("MCP tool called: get_tasks_due_today")
    return await due_today(client())


@mcp.tool()
async def get_overdue_tasks() -> dict[str, Any]:
    """Return ClickUp tasks assigned to the user that are overdue."""
    log.info("MCP tool called: get_overdue_tasks")
    return await overdue(client())


@mcp.tool()
async def get_high_priority_tasks() -> dict[str, Any]:
    """Return urgent or high-priority ClickUp tasks assigned to the user."""
    log.info("MCP tool called: get_high_priority_tasks")
    return await high_priority(client())


@mcp.tool()
async def get_clickup_workspace_status() -> dict[str, Any]:
    """Check whether ClickUp credentials and workspace configuration are available."""
    log.info("MCP tool called: get_clickup_workspace_status")
    return await workspace_status(client())


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
