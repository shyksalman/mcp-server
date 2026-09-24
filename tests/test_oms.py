import httpx
import pytest

from oms_mcp.config import Settings, load_settings
from oms_mcp.exceptions import AuthenticationError, OMSError
from oms_mcp.oms.auth import extract_tokens
from oms_mcp.oms.client import OMSClient
from oms_mcp.tools.leave import leaves
from oms_mcp.tools.attendance import attendance_stats
from oms_mcp.tools.leave import leave_summary
from oms_mcp.schemas import AttendanceStats, LeaveList, LeaveSummary


def settings() -> Settings:
    return Settings(
        oms_email="test@example.com",
        oms_password="secret",
        oms_tenant="enigmatix",
        oms_auth_base_url="https://auth.example.com",
        oms_employee_base_url="https://employee.example.com",
        oms_refresh_path="",
        ollama_base_url="http://localhost:11434",
        ollama_model="test-model",
        max_tool_iterations=10,
        _env_file=None,
    )


def test_token_extraction() -> None:
    assert extract_tokens({"data": {"access_token": "abc", "refresh_token": "def"}}) == ("abc", "def")
    with pytest.raises(AuthenticationError):
        extract_tokens({"data": {}})


def test_all_settings_loaded_from_environment(monkeypatch, tmp_path) -> None:
    monkeypatch.chdir(tmp_path)
    values = {
        "OMS_EMAIL": "env@example.com",
        "OMS_PASSWORD": "from-env",
        "OMS_TENANT": "custom-tenant",
        "OMS_AUTH_BASE_URL": "https://auth.custom.test",
        "OMS_EMPLOYEE_BASE_URL": "https://employee.custom.test",
        "OMS_REFRESH_PATH": "/refresh/",
        "OLLAMA_BASE_URL": "http://127.0.0.1:12000",
        "OLLAMA_MODEL": "custom-model",
        "MAX_TOOL_ITERATIONS": "7",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    loaded = load_settings()
    assert loaded.oms_email == values["OMS_EMAIL"]
    assert loaded.oms_password == values["OMS_PASSWORD"]
    assert loaded.oms_tenant == values["OMS_TENANT"]
    assert loaded.oms_auth_base_url == values["OMS_AUTH_BASE_URL"]
    assert loaded.oms_employee_base_url == values["OMS_EMPLOYEE_BASE_URL"]
    assert loaded.oms_refresh_path == values["OMS_REFRESH_PATH"]
    assert loaded.ollama_base_url == values["OLLAMA_BASE_URL"]
    assert loaded.ollama_model == values["OLLAMA_MODEL"]
    assert loaded.max_tool_iterations == 7
    monkeypatch.delenv("OMS_PASSWORD")
    with pytest.raises(ValueError, match="OMS_PASSWORD") as error:
        load_settings()
    assert "from-env" not in str(error.value)


@pytest.mark.asyncio
async def test_auth_and_all_api_routes() -> None:
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/api/v1/login/":
            assert request.headers["x-tenant"] == "enigmatix"
            return httpx.Response(200, json={"data": {"access": "private"}})
        assert request.headers["authorization"] == "Bearer private"
        if request.url.path.endswith("attendance_stats"):
            return httpx.Response(200, json={"total_present": 18, "total_absent": 2})
        if request.url.path.endswith("/leave/leave"):
            assert dict(request.url.params) == {"page": "2", "size": "5"}
            return httpx.Response(200, json={"data": [{"id": 7, "status": "approved"}]})
        if request.url.path.endswith("get-leaves-count/"):
            assert dict(request.url.params) == {"page": "1"}
            return httpx.Response(200, json={"remaining": 4})
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OMSClient(settings(), http)
        assert (await client.get_attendance_stats()).present == 18
        assert (await client.get_leaves(2, 5)).requests[0].status == "approved"
        assert (await client.get_leave_summary()).remaining == 4
    assert len(requests) == 4


@pytest.mark.asyncio
async def test_401_reauthenticates_once() -> None:
    login_count = 0
    api_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal login_count, api_count
        if request.url.path.endswith("login/"):
            login_count += 1
            return httpx.Response(200, json={"access": f"token-{login_count}"})
        api_count += 1
        return httpx.Response(401 if api_count == 1 else 200, json={"present": 1})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = OMSClient(settings(), http)
        assert (await client.get_attendance_stats()).present == 1
    assert login_count == 2 and api_count == 2


@pytest.mark.asyncio
async def test_repeated_401_stops() -> None:
    count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal count
        if request.url.path.endswith("login/"):
            return httpx.Response(200, json={"access": "token"})
        count += 1
        return httpx.Response(401)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(AuthenticationError):
            await OMSClient(settings(), http).get_attendance_stats()
    assert count == 2


@pytest.mark.asyncio
async def test_refresh_token_path() -> None:
    paths = []

    def handler(request: httpx.Request) -> httpx.Response:
        paths.append(request.url.path)
        if request.url.path.endswith("login/"):
            return httpx.Response(200, json={"access": "old", "refresh": "refresh-private"})
        if request.url.path.endswith("refresh/"):
            return httpx.Response(200, json={"access": "new"})
        return httpx.Response(401 if request.headers["authorization"] == "Bearer old" else 200, json={"present": 2})

    configured = settings().model_copy(update={"oms_refresh_path": "/api/v1/token/refresh/"})
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        assert (await OMSClient(configured, http).get_attendance_stats()).present == 2
    assert paths.count("/api/v1/login/") == 1
    assert "/api/v1/token/refresh/" in paths


@pytest.mark.asyncio
async def test_validation_and_safe_errors() -> None:
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: httpx.Response(403))) as http:
        client = OMSClient(settings(), http)
        for page, size in [(0, 10), (1, 101), ("1&admin=true", 10), (True, 10)]:
            with pytest.raises(ValueError):
                await client.get_leaves(page, size)
        assert (await leaves(client, 0, 10))["success"] is False


@pytest.mark.parametrize("status,message", [(403, "permission"), (404, "unavailable"), (429, "rate limit"), (500, "unavailable")])
@pytest.mark.asyncio
async def test_http_errors(status: int, message: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access": "token"}) if request.url.path.endswith("login/") else httpx.Response(status)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        with pytest.raises(OMSError, match=message):
            await OMSClient(settings(), http).get_leave_summary()


@pytest.mark.asyncio
async def test_invalid_json_and_timeout() -> None:
    def invalid(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"access": "token"}) if request.url.path.endswith("login/") else httpx.Response(200, text="not json")

    async with httpx.AsyncClient(transport=httpx.MockTransport(invalid)) as http:
        with pytest.raises(OMSError, match="invalid JSON"):
            await OMSClient(settings(), http).get_leave_summary()

    def timeout(_: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out")

    async with httpx.AsyncClient(transport=httpx.MockTransport(timeout)) as http:
        with pytest.raises(OMSError, match="timed out"):
            await OMSClient(settings(), http).get_leave_summary()


@pytest.mark.asyncio
async def test_tool_execution() -> None:
    class FakeClient:
        async def get_attendance_stats(self):
            return AttendanceStats(present=10)

        async def get_leaves(self, page, size):
            return LeaveList(page=page, size=size)

        async def get_leave_summary(self):
            return LeaveSummary(remaining=3)

    client = FakeClient()
    assert (await attendance_stats(client))["present"] == 10
    assert (await leaves(client, 2, 5))["page"] == 2
    assert (await leave_summary(client))["remaining"] == 3
