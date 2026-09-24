import json
import logging
from typing import Any

from assistant.tool_adapter import result_for_model, to_ollama_tool

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an employee assistant connected to Enigmatix OMS through tools.
Use the available tools for factual questions about the user's attendance, leaves, leave balance, or leave requests. Never invent OMS facts. If data is unavailable or a tool fails, say so. Credentials are handled internally; never ask for tokens. Explain results naturally, mention dates and statuses when relevant, and combine tools for summaries. Use no tools for unrelated questions.
The OMS schemas may be partially unknown. If a field is missing, do not infer its value from another field. A leave list may be paginated; never claim there are no matching requests beyond the retrieved page. For a request for the latest five, call get_my_leaves with size=5."""


class ChatSession:
    def __init__(self, ollama: Any, mcp: Any, max_iterations: int = 10):
        self.ollama = ollama
        self.mcp = mcp
        self.max_iterations = max_iterations
        self.clear()

    def clear(self) -> None:
        self.messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT}]

    async def ask(self, message: str) -> str:
        self.messages.append({"role": "user", "content": message})
        tools = [to_ollama_tool(tool) for tool in self.mcp.tools]
        for _ in range(self.max_iterations):
            response = await self.ollama.chat(self.messages, tools)
            assistant = response.message
            self.messages.append(assistant)
            calls = assistant.tool_calls or []
            if not calls:
                return assistant.content or "I could not produce an answer."
            for call in calls:
                name = call.function.name
                args = dict(call.function.arguments or {})
                log.info("Executing MCP tool: %s", name)
                try:
                    result = await self.mcp.call_tool(name, args)
                    content = result_for_model(result)
                except Exception:
                    log.warning("MCP tool execution failed: %s", name)
                    content = json.dumps({"success": False, "error": "MCP tool unavailable or failed"})
                self.messages.append({"role": "tool", "tool_name": name, "content": content})
        answer = "I reached the tool-call limit before I could answer. Please try a narrower question."
        self.messages.append({"role": "assistant", "content": answer})
        return answer
