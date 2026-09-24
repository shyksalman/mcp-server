import logging
import time
from typing import Any

import httpx

from oms_mcp.config import Settings
from oms_mcp.exceptions import AuthenticationError, OMSError
from oms_mcp.oms.attendance import normalize_attendance
from oms_mcp.oms.auth import extract_tokens
from oms_mcp.oms.leave import normalize_leave_summary, normalize_leaves
from oms_mcp.schemas import AttendanceStats, LeaveList, LeaveSummary

log = logging.getLogger(__name__)


class OMSClient:
    def __init__(self, settings: Settings, http: httpx.AsyncClient | None = None):
        self.settings = settings
        self.http = http or httpx.AsyncClient(timeout=20)
        self._owns_http = http is None
        self.access_token: str | None = None
        self.refresh_token: str | None = None

    async def __aenter__(self) -> "OMSClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_http:
            await self.http.aclose()

    def _base_headers(self) -> dict[str, str]:
        return {"Accept": "application/json", "x-tenant": self.settings.oms_tenant}

    async def login(self) -> None:
        self.settings.require_credentials()
        try:
            response = await self.http.post(
                f"{self.settings.oms_auth_base_url.rstrip('/')}/api/v1/login/",
                headers={**self._base_headers(), "Content-Type": "application/json"},
                json={"email": self.settings.oms_email, "password": self.settings.oms_password},
            )
            if response.status_code in (400, 401, 403):
                raise AuthenticationError("OMS authentication failed")
            self._check_status(response)
            self.access_token, self.refresh_token = extract_tokens(self._json(response))
        except httpx.TimeoutException as exc:
            raise OMSError("OMS authentication timed out") from exc
        except httpx.RequestError as exc:
            raise OMSError("Could not connect to OMS authentication service") from exc

    async def _refresh_or_login(self) -> None:
        path = self.settings.oms_refresh_path
        if self.refresh_token and path and path.startswith("/") and not path.startswith("//"):
            try:
                response = await self.http.post(
                    f"{self.settings.oms_auth_base_url.rstrip('/')}{path}",
                    headers={**self._base_headers(), "Content-Type": "application/json"},
                    json={"refresh": self.refresh_token},
                )
                if response.is_success:
                    access, refresh = extract_tokens(self._json(response))
                    self.access_token = access
                    self.refresh_token = refresh or self.refresh_token
                    return
            except (httpx.RequestError, OMSError):
                pass
        await self.login()

    async def ensure_authenticated(self) -> None:
        if not self.access_token:
            await self.login()

    @staticmethod
    def _json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except ValueError as exc:
            raise OMSError("OMS returned invalid JSON") from exc

    @staticmethod
    def _check_status(response: httpx.Response) -> None:
        status = response.status_code
        if status == 401:
            raise AuthenticationError("OMS authentication failed")
        if status == 403:
            raise OMSError("OMS permission denied")
        if status == 404:
            raise OMSError("OMS resource unavailable")
        if status == 429:
            raise OMSError("OMS rate limit reached; please try again later")
        if status >= 500:
            raise OMSError("OMS service unavailable")
        if status >= 400:
            raise OMSError(f"OMS request failed (HTTP {status})")

    async def request(self, path: str, *, params: dict[str, int] | None = None) -> Any:
        if not path.startswith("/api/v1/"):
            raise ValueError("Invalid OMS API path")
        await self.ensure_authenticated()
        url = f"{self.settings.oms_employee_base_url.rstrip('/')}{path}"
        for attempt in range(2):
            started = time.monotonic()
            try:
                response = await self.http.get(
                    url, headers={**self._base_headers(), "Authorization": f"Bearer {self.access_token}"}, params=params,
                )
            except httpx.TimeoutException as exc:
                raise OMSError("OMS request timed out") from exc
            except httpx.RequestError as exc:
                raise OMSError("Could not connect to OMS service") from exc
            log.info("OMS request: GET %s; response: %s; duration: %dms", path, response.status_code, round((time.monotonic()-started)*1000))
            if response.status_code == 401 and attempt == 0:
                self.access_token = None
                await self._refresh_or_login()
                continue
            self._check_status(response)
            return self._json(response)
        raise AuthenticationError("OMS authentication failed")

    async def get_attendance_stats(self) -> AttendanceStats:
        return normalize_attendance(await self.request("/api/v1/attendance/attendance_hierarchy"))

    async def get_leaves(self, page: int = 1, size: int = 10) -> LeaveList:
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("page must be an integer of at least 1")
        if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 100:
            raise ValueError("size must be an integer between 1 and 100")
        return normalize_leaves(await self.request("/api/v1/leave/leave", params={"page": page, "size": size}), page, size)

    async def get_leave_summary(self) -> LeaveSummary:
        return normalize_leave_summary(await self.request("/api/v1/leave/get-leaves-count/", params={"page": 1}))
