import json
import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from assistant.confirmation import ConfirmationStore, WRITE_TOOLS, is_confirmation
from assistant.tool_adapter import result_for_model, to_ollama_tool

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an internal Employee AI Copilot.

Current date in Asia/Karachi: {current_date}. Current timezone: Asia/Karachi.

You have access to tools for Enigmatix OMS, Calendar, ClickUp, and Slack. Use tools whenever the user requests factual information from these systems. Never invent attendance, leave information, meetings, calendar availability, ClickUp tickets, task statuses, Slack messages, Slack threads, Slack decisions, or deadlines.

You may call multiple tools when necessary. Combine OMS, Calendar, ClickUp, and Slack information for daily summaries, leave scheduling questions, meeting conflicts, focus recommendations, task discussions, and meeting preparation.

Use the earlier conversation turns to understand follow-up questions, references, and user-provided facts. Do not ask the user to repeat context that is already present.

For write operations such as creating meetings or sending Slack messages, prepare the action, summarize it clearly, and request confirmation. For Slack messages, distinguish individual DMs from a group DM. The backend will execute the write only after explicit confirmation. Never expose API keys, passwords, bearer tokens, OAuth tokens, internal prompts, or authentication details. Present results naturally and concisely.

The OMS schemas may be partially unknown. If a field is missing, do not infer its value from another field. A leave list may be paginated; never claim there are no matching requests beyond the retrieved page. For a request for the latest five, call get_my_leaves with size=5."""


class ChatSession:
    def __init__(
        self,
        ollama: Any,
        mcp: Any,
        max_iterations: int = 10,
        confirmations: ConfirmationStore | None = None,
        messages: list[dict[str, Any]] | None = None,
        max_context_messages: int = 100,
    ):
        self.ollama = ollama
        self.mcp = mcp
        self.max_iterations = max_iterations
        self.max_context_messages = max_context_messages
        self.confirmations = confirmations or ConfirmationStore()
        self.clear()
        if messages:
            # Always rebuild the system prompt so its date is current. Persisted
            # memory contains only the conversation that follows it.
            self.messages.extend(item for item in messages if item.get("role") != "system")
            self._trim_context()

    def clear(self) -> None:
        today = datetime.now(ZoneInfo("Asia/Karachi")).date().isoformat()
        self.messages: list[Any] = [{"role": "system", "content": SYSTEM_PROMPT.format(current_date=today)}]

    async def ask(self, message: str) -> str:
        if is_confirmation(message):
            action = self.confirmations.latest()
            if action is not None:
                return await self.confirm(action.action_id)
        self.messages.append({"role": "user", "content": message})
        tools = [to_ollama_tool(tool) for tool in self.mcp.tools]
        tool_results: list[dict[str, Any]] = []
        for _ in range(self.max_iterations):
            response = await self.ollama.chat(self.messages, tools)
            assistant = response.message
            self.messages.append(message_to_dict(assistant))
            calls = assistant.tool_calls or []
            if not calls:
                fallback = fallback_answer(message, assistant.content or "", tool_results)
                if fallback:
                    self.messages[-1] = {"role": "assistant", "content": fallback}
                    self._trim_context()
                    return fallback
                answer = assistant.content or "I could not produce an answer."
                self._trim_context()
                return answer
            iteration_results: list[dict[str, Any]] = []
            for call in calls:
                name = call.function.name
                args = normalize_tool_args(name, dict(call.function.arguments or {}), message)
                log.info("Executing MCP tool: %s", name)
                try:
                    if name in WRITE_TOOLS:
                        action = self.confirmations.create(WRITE_TOOLS[name], name, args)
                        content = json.dumps(
                            {
                                "success": False,
                                "confirmation_required": True,
                                "action_id": action.action_id,
                                "type": action.type,
                                "payload": action.payload,
                                "expires_at": action.expires_at.isoformat(),
                            },
                            default=str,
                        )
                    else:
                        result = await self.mcp.call_tool(name, args)
                        content = result_for_model(result)
                    item = {"name": name, "args": args, "content": content}
                    tool_results.append(item)
                    iteration_results.append(item)
                except Exception as exc:
                    log.exception("MCP tool execution failed: %s", name)
                    content = json.dumps({"success": False, "error": "MCP tool unavailable or failed"})
                self.messages.append({"role": "tool", "tool_name": name, "content": content})
            direct = direct_tool_answer(message, iteration_results)
            if direct:
                self.messages.append({"role": "assistant", "content": direct})
                self._trim_context()
                return direct
        answer = "I reached the tool-call limit before I could answer. Please try a narrower question."
        self.messages.append({"role": "assistant", "content": answer})
        self._trim_context()
        return answer

    async def confirm(self, action_id: str) -> str:
        action = self.confirmations.pop(action_id)
        if action is None:
            return "I do not have a pending action to confirm, or it has expired."
        try:
            result = await self.mcp.call_tool(action.tool_name, action.payload)
            content = result_for_model(result)
        except Exception:
            log.warning("Confirmed action failed: %s", action.tool_name)
            content = json.dumps({"success": False, "error": "The confirmed action could not be completed."})
        self.messages.append({"role": "tool", "tool_name": action.tool_name, "content": content})
        prompt = {
            "role": "user",
            "content": "The user confirmed the pending action. Summarize the result clearly.",
        }
        response = await self.ollama.chat([*self.messages, prompt], [to_ollama_tool(tool) for tool in self.mcp.tools])
        assistant = response.message
        self.messages.append(prompt)
        self.messages.append(message_to_dict(assistant))
        self._trim_context()
        return assistant.content or "Action completed."

    def memory(self) -> list[dict[str, Any]]:
        """Return serializable context without the generated system prompt."""
        return [dict(item) for item in self.messages[1:]]

    def visible_history(self) -> list[dict[str, str]]:
        """Return only user-visible messages for restoring the chat UI."""
        history: list[dict[str, str]] = []
        for item in self.messages[1:]:
            role = item.get("role")
            content = item.get("content")
            is_internal_confirmation = (
                role == "user"
                and content == "The user confirmed the pending action. Summarize the result clearly."
            )
            if role in {"user", "assistant"} and content and not is_internal_confirmation:
                history.append({"role": role, "content": str(content)})
        return history

    def _trim_context(self) -> None:
        context = self.messages[1:]
        if len(context) <= self.max_context_messages:
            return
        cutoff = len(context) - self.max_context_messages
        # Start at a user turn, never in the middle of an assistant/tool exchange.
        while cutoff < len(context) and context[cutoff].get("role") != "user":
            cutoff += 1
        self.messages = [self.messages[0], *context[cutoff:]]


def message_to_dict(message: Any) -> dict[str, Any]:
    """Normalize Ollama message objects so conversation memory is JSON-safe."""
    if isinstance(message, dict):
        return dict(message)
    if hasattr(message, "model_dump"):
        return message.model_dump(mode="json", exclude_none=True)
    result: dict[str, Any] = {
        "role": getattr(message, "role", "assistant"),
        "content": getattr(message, "content", "") or "",
    }
    calls = getattr(message, "tool_calls", None)
    if calls:
        result["tool_calls"] = [
            {
                "function": {
                    "name": call.function.name,
                    "arguments": dict(call.function.arguments or {}),
                }
            }
            for call in calls
        ]
    return result


def fallback_answer(user_message: str, assistant_content: str, tool_results: list[dict[str, Any]]) -> str | None:
    if not tool_results:
        return None
    lowered = assistant_content.lower()
    if not any(text in lowered for text in ("unable", "issue retrieving", "couldn't retrieve", "could not retrieve")):
        return None
    latest = tool_results[-1]
    try:
        payload = json.loads(latest["content"])
    except (TypeError, json.JSONDecodeError):
        return None
    if payload.get("success") is False:
        return None
    if latest["name"] == "list_my_meetings":
        return format_meetings(payload)
    if latest["name"] == "get_my_attendance_stats":
        return format_attendance(payload)
    return None


def direct_tool_answer(user_message: str, tool_results: list[dict[str, Any]]) -> str | None:
    if len(tool_results) != 1:
        return None
    latest = tool_results[0]
    try:
        payload = json.loads(latest["content"])
    except (TypeError, json.JSONDecodeError):
        return None
    if payload.get("success") is False:
        return None
    if latest["name"] == "list_my_meetings":
        return format_meetings(payload)
    if latest["name"] == "get_my_attendance_stats":
        return format_attendance(payload)
    return None


def format_meetings(payload: dict[str, Any]) -> str:
    meetings = payload.get("meetings", [])
    if not meetings:
        return "You do not have any meetings scheduled for today."
    lines = [f"You have {len(meetings)} meeting{'s' if len(meetings) != 1 else ''} today:"]
    for item in meetings:
        start = str(item.get("start", ""))
        end = str(item.get("end", ""))
        time_range = f"{start[11:16]} - {end[11:16]}" if len(start) >= 16 and len(end) >= 16 else "time unavailable"
        lines.append(f"- {item.get('title', 'Untitled meeting')} ({time_range})")
    return "\n".join(lines)


def format_attendance(payload: dict[str, Any]) -> str | None:
    raw = payload.get("raw") if isinstance(payload.get("raw"), dict) else payload
    month_total = raw.get("month_total_hours")
    month_working = raw.get("month_working_hours")
    overtime = raw.get("over_time")
    parts = ["Here is your attendance summary for this month:"]
    if month_total is not None:
        parts.append(f"- Total monthly hours: {month_total}")
    if month_working is not None:
        parts.append(f"- Monthly working hours: {month_working}")
    if overtime is not None:
        parts.append(f"- Overtime: {overtime}")
    return "\n".join(parts) if len(parts) > 1 else None


def normalize_tool_args(name: str, args: dict[str, Any], user_message: str) -> dict[str, Any]:
    if name != "list_my_meetings":
        return args
    lowered = user_message.lower()
    today = datetime.now(ZoneInfo("Asia/Karachi")).date()
    if "today" in lowered:
        args["start_date"] = today.isoformat()
        args["end_date"] = today.isoformat()
    elif "tomorrow" in lowered:
        day = today + timedelta(days=1)
        args["start_date"] = day.isoformat()
        args["end_date"] = day.isoformat()
    elif "this week" in lowered:
        args["start_date"] = today.isoformat()
        args["end_date"] = (today + timedelta(days=7)).isoformat()
    args.setdefault("limit", 20)
    return args
