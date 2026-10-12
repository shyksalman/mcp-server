from datetime import UTC, datetime
from typing import Any

import httpx

from clickup_mcp.config import ClickUpSettings
from clickup_mcp.exceptions import ClickUpError
from clickup_mcp.schemas import ClickUpTask


def _from_epoch_ms(value: Any) -> datetime | None:
    if value in (None, "", 0, "0"):
        return None
    try:
        return datetime.fromtimestamp(int(value) / 1000, UTC)
    except (TypeError, ValueError, OSError):
        return None


def _priority(value: Any) -> str | None:
    if isinstance(value, dict):
        return value.get("priority") or value.get("color")
    return None


def normalize_task(raw: dict[str, Any]) -> ClickUpTask:
    status = raw.get("status")
    task_status = status.get("status") if isinstance(status, dict) else status
    list_value = raw.get("list") if isinstance(raw.get("list"), dict) else {}
    project_value = raw.get("project") if isinstance(raw.get("project"), dict) else {}
    assignees = []
    for item in raw.get("assignees") or []:
        if isinstance(item, dict):
            assignees.append(item.get("username") or item.get("email") or str(item.get("id")))
    return ClickUpTask(
        id=str(raw.get("id", "")),
        name=str(raw.get("name", "")),
        description=raw.get("description") or raw.get("text_content"),
        status=task_status,
        priority=_priority(raw.get("priority")),
        due_date=_from_epoch_ms(raw.get("due_date")),
        created_at=_from_epoch_ms(raw.get("date_created")),
        updated_at=_from_epoch_ms(raw.get("date_updated")),
        url=raw.get("url"),
        list_name=list_value.get("name"),
        project=project_value.get("name"),
        assignees=assignees,
    )


class ClickUpClient:
    def __init__(self, settings: ClickUpSettings, http: httpx.AsyncClient | None = None):
        self.settings = settings
        self.http = http or httpx.AsyncClient(timeout=20)
        self._owns_http = http is None

    async def __aenter__(self) -> "ClickUpClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_http:
            await self.http.aclose()

    @property
    def configured(self) -> bool:
        return bool(self.settings.clickup_api_token and self.settings.clickup_workspace_id)

    def _headers(self) -> dict[str, str]:
        if not self.settings.clickup_api_token:
            raise ClickUpError("ClickUp is not configured")
        return {"Authorization": self.settings.clickup_api_token}

    async def get_my_tasks(
        self,
        status: str | None = None,
        priority: str | None = None,
        due_before: datetime | None = None,
        due_after: datetime | None = None,
        limit: int = 50,
    ) -> list[ClickUpTask]:
        if not self.configured:
            return []
        params: dict[str, Any] = {
            "subtasks": "true",
            "include_closed": "true" if status and status.lower() in {"closed", "complete", "completed"} else "false",
            "page": 0,
        }
        if self.settings.clickup_user_id:
            params["assignees[]"] = self.settings.clickup_user_id
        if due_before:
            params["due_date_lt"] = int(due_before.timestamp() * 1000)
        if due_after:
            params["due_date_gt"] = int(due_after.timestamp() * 1000)
        url = f"{self.settings.clickup_base_url}/team/{self.settings.clickup_workspace_id}/task"
        try:
            response = await self.http.get(url, headers=self._headers(), params=params)
        except httpx.HTTPError as exc:
            raise ClickUpError("ClickUp request failed") from exc
        if response.status_code == 429:
            raise ClickUpError("ClickUp rate limit reached")
        if response.status_code >= 400:
            raise ClickUpError("ClickUp API error")
        tasks = [normalize_task(item) for item in response.json().get("tasks", [])]
        if status:
            tasks = [item for item in tasks if (item.status or "").lower() == status.lower()]
        if priority:
            tasks = [item for item in tasks if (item.priority or "").lower() == priority.lower()]
        return tasks[:limit]

    async def get_task(self, task_id: str) -> ClickUpTask:
        if not self.configured:
            raise ClickUpError("ClickUp is not configured")
        url = f"{self.settings.clickup_base_url}/task/{task_id}"
        try:
            response = await self.http.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise ClickUpError("ClickUp request failed") from exc
        if response.status_code >= 400:
            raise ClickUpError("ClickUp task was not found")
        return normalize_task(response.json())
