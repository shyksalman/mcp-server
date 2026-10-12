import asyncio
import json
import sqlite3
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from assistant.chat import ChatSession


class SQLiteConversationStore:
    """Small durable store for conversation context.

    SQLite keeps this deployment self-contained while allowing conversations to
    survive backend restarts. A conversation UUID is the lookup key; no memory
    is shared between conversations.
    """

    def __init__(self, path: str, max_conversations: int = 500):
        database = Path(path)
        database.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(database)
        self.max_conversations = max_conversations
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                messages TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.connection.commit()

    def load(self, conversation_id: str) -> list[dict[str, Any]]:
        row = self.connection.execute(
            "SELECT messages FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if row is None:
            return []
        try:
            messages = json.loads(row[0])
        except (TypeError, json.JSONDecodeError):
            return []
        return messages if isinstance(messages, list) else []

    def save(self, conversation_id: str, messages: list[dict[str, Any]]) -> None:
        now = datetime.now(UTC).isoformat()
        self.connection.execute(
            """
            INSERT INTO conversations (id, messages, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET messages = excluded.messages, updated_at = excluded.updated_at
            """,
            (conversation_id, json.dumps(messages, default=str), now),
        )
        self.connection.execute(
            """
            DELETE FROM conversations
            WHERE id IN (
                SELECT id FROM conversations
                ORDER BY updated_at DESC
                LIMIT -1 OFFSET ?
            )
            """,
            (self.max_conversations,),
        )
        self.connection.commit()

    def delete(self, conversation_id: str) -> None:
        self.connection.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()


class ConversationMemory:
    """Create and coordinate isolated ChatSession instances by conversation."""

    def __init__(
        self,
        ollama: Any,
        mcp: Any,
        database_path: str,
        max_iterations: int = 10,
        max_context_messages: int = 100,
        max_conversations: int = 500,
    ):
        self.ollama = ollama
        self.mcp = mcp
        self.max_iterations = max_iterations
        self.max_context_messages = max_context_messages
        self.max_conversations = max_conversations
        self.store = SQLiteConversationStore(database_path, max_conversations)
        self.sessions: OrderedDict[str, ChatSession] = OrderedDict()
        self.locks: dict[str, asyncio.Lock] = {}

    @staticmethod
    def normalize_id(conversation_id: UUID | str | None) -> str:
        return str(UUID(str(conversation_id))) if conversation_id else str(uuid4())

    async def ask(self, message: str, conversation_id: UUID | str | None = None) -> tuple[str, str]:
        normalized_id = self.normalize_id(conversation_id)
        async with self._lock(normalized_id):
            session = self._session(normalized_id)
            previous_messages = list(session.messages)
            try:
                answer = await session.ask(message)
            except Exception:
                # A failed model request is not a completed turn and must not
                # contaminate the next retry with a duplicate user message.
                session.messages = previous_messages
                raise
            self.store.save(normalized_id, session.memory())
            return normalized_id, answer

    async def confirm(self, action_id: str, conversation_id: UUID | str | None) -> tuple[str, str]:
        normalized_id = self.normalize_id(conversation_id)
        async with self._lock(normalized_id):
            session = self._session(normalized_id)
            answer = await session.confirm(action_id)
            self.store.save(normalized_id, session.memory())
            return normalized_id, answer

    async def history(self, conversation_id: UUID | str) -> list[dict[str, str]]:
        normalized_id = self.normalize_id(conversation_id)
        async with self._lock(normalized_id):
            return self._session(normalized_id).visible_history()

    async def clear(self, conversation_id: UUID | str) -> None:
        normalized_id = self.normalize_id(conversation_id)
        async with self._lock(normalized_id):
            self.sessions.pop(normalized_id, None)
            self.store.delete(normalized_id)

    def close(self) -> None:
        self.store.close()

    def _lock(self, conversation_id: str) -> asyncio.Lock:
        return self.locks.setdefault(conversation_id, asyncio.Lock())

    def _session(self, conversation_id: str) -> ChatSession:
        existing = self.sessions.pop(conversation_id, None)
        if existing is not None:
            self.sessions[conversation_id] = existing
            return existing
        session = ChatSession(
            self.ollama,
            self.mcp,
            self.max_iterations,
            messages=self.store.load(conversation_id),
            max_context_messages=self.max_context_messages,
        )
        self.sessions[conversation_id] = session
        while len(self.sessions) > self.max_conversations:
            expired_id = next(
                (
                    item_id
                    for item_id in self.sessions
                    if item_id != conversation_id
                    and (item_id not in self.locks or not self.locks[item_id].locked())
                ),
                None,
            )
            if expired_id is None:
                break
            self.sessions.pop(expired_id, None)
            self.locks.pop(expired_id, None)
        return session
