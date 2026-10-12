from datetime import UTC, datetime
from typing import Any

import httpx

from slack_mcp.config import SlackSettings
from slack_mcp.exceptions import SlackAuthenticationError, SlackMCPError, SlackPermissionError, SlackRateLimitError
from slack_mcp.schemas import SlackConversation, SlackMessage, SlackUser

try:
    from slack_sdk.web.async_client import AsyncWebClient
except ImportError:  # pragma: no cover - exercised in environments without slack_sdk
    AsyncWebClient = None  # type: ignore[assignment]


def _dt_from_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromtimestamp(float(ts), UTC)
    except (TypeError, ValueError, OSError):
        return None


def normalize_user(raw: dict[str, Any]) -> SlackUser:
    profile = raw.get("profile") if isinstance(raw.get("profile"), dict) else {}
    return SlackUser(
        id=str(raw.get("id", "")),
        display_name=profile.get("display_name") or raw.get("name"),
        real_name=profile.get("real_name") or raw.get("real_name"),
        email=profile.get("email"),
        deleted=bool(raw.get("deleted", False)),
    )


def normalize_conversation(raw: dict[str, Any]) -> SlackConversation:
    if raw.get("is_im"):
        conversation_type = "im"
    elif raw.get("is_mpim"):
        conversation_type = "mpim"
    elif raw.get("is_private"):
        conversation_type = "private_channel"
    else:
        conversation_type = "public_channel"
    latest = raw.get("latest") if isinstance(raw.get("latest"), dict) else {}
    return SlackConversation(
        id=str(raw.get("id", "")),
        name=raw.get("name") or raw.get("user") or raw.get("id"),
        type=conversation_type,
        is_member=bool(raw.get("is_member") or raw.get("is_im") or raw.get("is_mpim")),
        latest_message=latest.get("text"),
        latest_timestamp=latest.get("ts"),
        unread_count=raw.get("unread_count_display") or raw.get("unread_count"),
    )


def normalize_message(raw: dict[str, Any], user_names: dict[str, str] | None = None) -> SlackMessage:
    user_id = raw.get("user") or raw.get("bot_id")
    return SlackMessage(
        ts=str(raw.get("ts", "")),
        date_time=_dt_from_ts(raw.get("ts")),
        user_id=user_id,
        user_name=(user_names or {}).get(user_id, user_id),
        text=raw.get("text") or "",
        thread_ts=raw.get("thread_ts"),
        reply_count=int(raw.get("reply_count") or 0),
        raw_metadata={key: raw.get(key) for key in ("subtype", "team", "channel") if key in raw},
    )


class SlackClient:
    def __init__(self, settings: SlackSettings, http: httpx.AsyncClient | None = None, sdk_client: Any | None = None):
        self.settings = settings
        self.http = http or httpx.AsyncClient(timeout=20)
        self._owns_http = http is None
        if sdk_client is not None:
            self.sdk_client = sdk_client
        elif AsyncWebClient is not None and settings.slack_bot_token:
            self.sdk_client = AsyncWebClient(token=settings.slack_bot_token)
        else:
            self.sdk_client = None

    async def __aenter__(self) -> "SlackClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        if self._owns_http:
            await self.http.aclose()

    @property
    def configured(self) -> bool:
        return bool(self.settings.slack_bot_token)

    def _headers(self) -> dict[str, str]:
        if not self.settings.slack_bot_token:
            raise SlackAuthenticationError("Slack bot token is not configured")
        return {"Authorization": f"Bearer {self.settings.slack_bot_token}"}

    async def api_call(self, method: str, **params: Any) -> dict[str, Any]:
        if not self.configured:
            raise SlackAuthenticationError("Slack bot token is not configured")
        if self.sdk_client is not None:
            try:
                response = await self.sdk_client.api_call(method, json=params)
                payload = dict(response)
            except Exception as exc:
                retry_after = getattr(getattr(exc, "response", None), "headers", {}).get("Retry-After")
                if retry_after:
                    raise SlackRateLimitError(int(retry_after)) from exc
                raise SlackMCPError("Slack API request failed") from exc
        else:
            try:
                response = await self.http.post(
                    f"{self.settings.slack_base_url.rstrip('/')}/{method}",
                    headers={**self._headers(), "Content-Type": "application/json"},
                    json={key: value for key, value in params.items() if value is not None},
                )
            except httpx.HTTPError as exc:
                raise SlackMCPError("Slack API request failed") from exc
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After")
                raise SlackRateLimitError(int(retry_after) if retry_after else None)
            payload = response.json()
        if payload.get("ok"):
            return payload
        error = str(payload.get("error") or "unknown_error")
        if error in {"not_authed", "invalid_auth", "account_inactive"}:
            raise SlackAuthenticationError("Slack authentication failed")
        if error in {"missing_scope", "not_in_channel", "channel_not_found", "is_archived"}:
            raise SlackPermissionError(f"This Slack app does not have access to that conversation. error: {error}")
        raise SlackMCPError(f"Slack API error: {error}")

    async def list_users(self, include_deactivated: bool = False, cursor: str | None = None, limit: int = 200) -> tuple[list[SlackUser], str | None]:
        payload = await self.api_call("users.list", cursor=cursor, limit=limit, team_id=self.settings.slack_team_id)
        users = [normalize_user(item) for item in payload.get("members", [])]
        if not include_deactivated:
            users = [item for item in users if not item.deleted]
        next_cursor = payload.get("response_metadata", {}).get("next_cursor") or None
        return users, next_cursor

    async def list_conversations(self, types: list[str], limit: int, cursor: str | None = None) -> tuple[list[SlackConversation], str | None]:
        payload = await self.api_call("conversations.list", types=",".join(types), limit=limit, cursor=cursor, exclude_archived=True)
        conversations = [normalize_conversation(item) for item in payload.get("channels", [])]
        next_cursor = payload.get("response_metadata", {}).get("next_cursor") or None
        return conversations, next_cursor

    async def open_conversation(self, user_ids: list[str]) -> SlackConversation:
        payload = await self.api_call("conversations.open", users=",".join(user_ids), return_im=True)
        return normalize_conversation(payload.get("channel", {}))

    async def post_message(self, channel_id: str, message: str) -> dict[str, Any]:
        return await self.api_call("chat.postMessage", channel=channel_id, text=message)

    async def get_permalink(self, channel_id: str, message_ts: str) -> str | None:
        try:
            payload = await self.api_call("chat.getPermalink", channel=channel_id, message_ts=message_ts)
            return payload.get("permalink")
        except SlackMCPError:
            return None

    async def conversation_history(
        self,
        conversation_id: str,
        limit: int,
        oldest: str | None = None,
        latest: str | None = None,
        cursor: str | None = None,
    ) -> tuple[list[SlackMessage], str | None]:
        payload = await self.api_call(
            "conversations.history",
            channel=conversation_id,
            limit=limit,
            oldest=oldest,
            latest=latest,
            cursor=cursor,
        )
        messages = [normalize_message(item) for item in payload.get("messages", [])]
        next_cursor = payload.get("response_metadata", {}).get("next_cursor") or None
        return messages, next_cursor

    async def thread_replies(self, conversation_id: str, thread_ts: str, limit: int) -> list[SlackMessage]:
        payload = await self.api_call("conversations.replies", channel=conversation_id, ts=thread_ts, limit=limit)
        return [normalize_message(item) for item in payload.get("messages", [])]

    async def search_messages(self, query: str, limit: int = 50) -> list[dict[str, Any]]:
        payload = await self.api_call("search.messages", query=query, count=limit)
        return list(payload.get("messages", {}).get("matches", []))
