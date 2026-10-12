from typing import Any


def public_tool(tool: Any) -> dict[str, str]:
    return {"name": tool.name, "description": tool.description or ""}
