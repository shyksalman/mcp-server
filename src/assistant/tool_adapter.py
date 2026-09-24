import json
from typing import Any


def to_ollama_tool(tool: Any) -> dict[str, Any]:
    return {"type": "function", "function": {
        "name": tool.name,
        "description": tool.description or "",
        "parameters": tool.inputSchema,
    }}


def result_for_model(result: Any) -> str:
    if getattr(result, "isError", False):
        return json.dumps({"success": False, "error": "MCP tool failed"})
    structured = getattr(result, "structuredContent", None)
    if structured is not None:
        return json.dumps(structured, default=str)
    content = [block.text for block in getattr(result, "content", []) if getattr(block, "type", None) == "text"]
    return "\n".join(content) or "{}"
