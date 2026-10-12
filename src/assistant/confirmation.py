from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4


WRITE_TOOLS = {
    "create_meeting": "CREATE_MEETING",
    "send_slack_dm": "SEND_SLACK_MESSAGE",
    "send_slack_message_to_users": "SEND_SLACK_MESSAGE",
    "send_slack_group_message": "SEND_SLACK_MESSAGE",
    "post_slack_channel_message": "SEND_SLACK_MESSAGE",
}


@dataclass
class PendingAction:
    action_id: str
    type: str
    tool_name: str
    payload: dict
    expires_at: datetime


class ConfirmationStore:
    def __init__(self, ttl_minutes: int = 10):
        self.ttl = timedelta(minutes=ttl_minutes)
        self._actions: dict[str, PendingAction] = {}

    def create(self, action_type: str, tool_name: str, payload: dict) -> PendingAction:
        self.prune()
        action = PendingAction(
            action_id=uuid4().hex,
            type=action_type,
            tool_name=tool_name,
            payload=payload,
            expires_at=datetime.now(UTC) + self.ttl,
        )
        self._actions[action.action_id] = action
        return action

    def latest(self) -> PendingAction | None:
        self.prune()
        actions = sorted(self._actions.values(), key=lambda item: item.expires_at, reverse=True)
        return actions[0] if actions else None

    def pop(self, action_id: str) -> PendingAction | None:
        self.prune()
        return self._actions.pop(action_id, None)

    def prune(self) -> None:
        now = datetime.now(UTC)
        for action_id, action in list(self._actions.items()):
            if action.expires_at <= now:
                self._actions.pop(action_id, None)


def is_confirmation(message: str) -> bool:
    normalized = message.strip().lower()
    return normalized in {"yes", "y", "confirm", "confirmed", "ok", "okay", "please do", "go ahead"}
