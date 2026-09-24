import os
import sys
from contextlib import AsyncExitStack
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


class OMSMCPClient:
    def __init__(self) -> None:
        self._stack = AsyncExitStack()
        self.session: ClientSession | None = None
        self.tools: list[Any] = []

    async def __aenter__(self) -> "OMSMCPClient":
        params = StdioServerParameters(
            command=sys.executable, args=["-m", "oms_mcp.server"], env=os.environ.copy()
        )
        try:
            read, write = await self._stack.enter_async_context(stdio_client(params))
            self.session = await self._stack.enter_async_context(ClientSession(read, write))
            await self.session.initialize()
            self.tools = (await self.session.list_tools()).tools
            return self
        except Exception as exc:
            await self._stack.aclose()
            raise RuntimeError("Could not start or connect to the OMS MCP server") from exc

    async def __aexit__(self, *_: object) -> None:
        await self._stack.aclose()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in {tool.name for tool in self.tools}:
            raise ValueError(f"Unknown MCP tool: {name}")
        assert self.session is not None
        return await self.session.call_tool(name, arguments=arguments)
