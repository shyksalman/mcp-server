import os
import sys
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@dataclass(frozen=True)
class MCPServerSpec:
    name: str
    module: str
    required: bool = True


DEFAULT_MCP_SERVERS = [
    MCPServerSpec("oms", "oms_mcp.server", required=False),
    MCPServerSpec("calendar", "calendar_mcp.server", required=False),
    MCPServerSpec("clickup", "clickup_mcp.server", required=False),
    MCPServerSpec("slack", "slack_mcp.server", required=False),
]


class MultiMCPClient:
    def __init__(self, servers: list[MCPServerSpec] | None = None) -> None:
        self._stack = AsyncExitStack()
        self.servers = servers or DEFAULT_MCP_SERVERS
        self.sessions: dict[str, ClientSession] = {}
        self.tools: list[Any] = []
        self._tool_servers: dict[str, str] = {}
        self.unavailable: dict[str, str] = {}

    async def __aenter__(self) -> "MultiMCPClient":
        for server in self.servers:
            await self._connect(server)
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._stack.aclose()

    async def _connect(self, server: MCPServerSpec) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        env = os.environ.copy()
        src_path = str(repo_root / "src")
        env["PYTHONPATH"] = f"{src_path}{os.pathsep}{env['PYTHONPATH']}" if env.get("PYTHONPATH") else src_path
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", server.module],
            env=env,
            cwd=repo_root,
        )
        try:
            read, write = await self._stack.enter_async_context(stdio_client(params))
            session = await self._stack.enter_async_context(ClientSession(read, write, read_timeout_seconds=timedelta(seconds=5)))
            await session.initialize()
            listed = (await session.list_tools()).tools
        except Exception as exc:
            self.unavailable[server.name] = "unavailable"
            if server.required:
                await self._stack.aclose()
                raise RuntimeError(f"Could not start or connect to the {server.name} MCP server") from exc
            return
        self.sessions[server.name] = session
        for tool in listed:
            if tool.name in self._tool_servers:
                self.unavailable[server.name] = f"duplicate tool name: {tool.name}"
                continue
            self._tool_servers[tool.name] = server.name
            self.tools.append(tool)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        server_name = self._tool_servers.get(name)
        if server_name is None:
            raise ValueError(f"Unknown MCP tool: {name}")
        return await self.sessions[server_name].call_tool(name, arguments=arguments)


class OMSMCPClient(MultiMCPClient):
    def __init__(self) -> None:
        super().__init__([MCPServerSpec("oms", "oms_mcp.server")])
