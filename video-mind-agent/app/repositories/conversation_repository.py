from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sqlite3

from app.core.config import get_data_path
from app.models import ChatTurn


@dataclass
class SQLiteConversationRepository:
    db_path: Path = field(default_factory=lambda: get_data_path("conversation_store.db"))

    def __post_init__(self) -> None:
        self.db_path = Path(self.db_path)
        self.init_db()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    video_id TEXT NOT NULL DEFAULT '',
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_conversation_messages_lookup
                ON conversation_messages(user_id, session_id, video_id, id)
                """
            )

    def add_turn(
        self,
        user_id: str,
        session_id: str,
        turn: ChatTurn,
        video_id: str | None = None,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_messages (user_id, session_id, video_id, role, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, session_id, video_id or "", turn.role, turn.content),
            )

    def recent_turns(
        self,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
        limit: int = 12,
    ) -> list[ChatTurn]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT role, content
                FROM conversation_messages
                WHERE user_id = ? AND session_id = ? AND video_id = ?
                ORDER BY id DESC
                LIMIT ?
                """,
                (user_id, session_id, video_id or "", limit),
            ).fetchall()

        return [
            ChatTurn(role=row["role"], content=row["content"])
            for row in reversed(rows)
        ]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
