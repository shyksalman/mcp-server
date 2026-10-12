from datetime import UTC, datetime, time, timedelta
from typing import Any

from clickup_mcp.client import ClickUpClient


async def my_tasks(
    client: ClickUpClient,
    status: str | None,
    priority: str | None,
    due_before: datetime | None,
    due_after: datetime | None,
    limit: int,
) -> dict[str, Any]:
    tasks = await client.get_my_tasks(status, priority, due_before, due_after, limit)
    return {"tasks": [item.model_dump(mode="json", by_alias=True) for item in tasks]}


async def task(client: ClickUpClient, task_id: str) -> dict[str, Any]:
    item = await client.get_task(task_id)
    return item.model_dump(mode="json", by_alias=True)


async def summary(client: ClickUpClient) -> dict[str, Any]:
    now = datetime.now(UTC)
    today_start = datetime.combine(now.date(), time.min, UTC)
    today_end = datetime.combine(now.date(), time.max, UTC)
    week_end = today_start + timedelta(days=7)
    tasks = await client.get_my_tasks(limit=100)
    open_tasks = [item for item in tasks if (item.status or "").lower() not in {"closed", "complete", "completed"}]
    return {
        "total_open": len(open_tasks),
        "high_priority": len([item for item in open_tasks if (item.priority or "").lower() in {"urgent", "high"}]),
        "overdue": len([item for item in open_tasks if item.due_date and item.due_date < today_start]),
        "due_today": len([item for item in open_tasks if item.due_date and today_start <= item.due_date <= today_end]),
        "due_this_week": len([item for item in open_tasks if item.due_date and today_start <= item.due_date <= week_end]),
    }


async def due_today(client: ClickUpClient) -> dict[str, Any]:
    now = datetime.now(UTC)
    return await my_tasks(client, None, None, datetime.combine(now.date(), time.max, UTC), datetime.combine(now.date(), time.min, UTC), 50)


async def overdue(client: ClickUpClient) -> dict[str, Any]:
    return await my_tasks(client, None, None, datetime.now(UTC), None, 50)


async def high_priority(client: ClickUpClient) -> dict[str, Any]:
    tasks = await client.get_my_tasks(limit=100)
    filtered = [item for item in tasks if (item.priority or "").lower() in {"urgent", "high"}]
    return {"tasks": [item.model_dump(mode="json", by_alias=True) for item in filtered]}
