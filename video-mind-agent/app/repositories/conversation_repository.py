from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sqlite3

from app.core.config import get_data_path
from app.models import ChatTurn


@dataclass
class SQLiteConversationRepository:
    """
    对话持久化仓库，管理三张表：
    1. conversation_messages  — 短期记忆（原始对话轮次）
    2. conversation_summaries — 长期记忆摘要（LLM 定期总结的压缩记忆）
    3. user_profiles          — 用户画像（用户的偏好、身份等长期信息）
    """
    db_path: Path = field(default_factory=lambda: get_data_path("conversation_store.db"))

    def __post_init__(self) -> None:
        self.db_path = Path(self.db_path)
        self.init_db()

    def init_db(self) -> None:
        """初始化数据库，创建所有需要的表和索引"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            # 原始对话轮次表（短期记忆）
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
            # 长期记忆摘要表：每个 (user_id, session_id, video_id) 存一条 LLM 生成的摘要
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversation_summaries (
                    user_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    video_id TEXT NOT NULL DEFAULT '',
                    summary TEXT NOT NULL DEFAULT '',
                    message_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, session_id, video_id)
                )
                """
            )
            # 用户画像表：每个 user_id 一条记录
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

    def add_turn(
        self,
        user_id: str,
        session_id: str,
        turn: ChatTurn,
        video_id: str | None = None,
    ) -> int:
        """
        添加一条对话轮次，返回插入行的 id（用于后续的记忆索引关联）
        """
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO conversation_messages (user_id, session_id, video_id, role, content)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, session_id, video_id or "", turn.role, turn.content),
            )
            return int(cursor.lastrowid)

    def recent_turns(
        self,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
        limit: int = 12,
    ) -> list[ChatTurn]:
        """
        获取最近的 N 轮对话（按 id 倒序取，再反转回正序），用作短期记忆
        """
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

    def count_turns(
        self,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
    ) -> int:
        """
        统计某个会话下的对话轮次总数，用于判断是否达到触发长期摘要的阈值
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT COUNT(*) AS count
                FROM conversation_messages
                WHERE user_id = ? AND session_id = ? AND video_id = ?
                """,
                (user_id, session_id, video_id or ""),
            ).fetchone()

        return int(row["count"] if row else 0)

    # ======================== 长期记忆摘要 ========================

    def get_summary(
        self,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
    ) -> str:
        """
        获取某个会话的长期记忆摘要，若无则返回空字符串
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT summary
                FROM conversation_summaries
                WHERE user_id = ? AND session_id = ? AND video_id = ?
                """,
                (user_id, session_id, video_id or ""),
            ).fetchone()

        return str(row["summary"]) if row else ""

    def upsert_summary(
        self,
        user_id: str,
        session_id: str,
        summary: str,
        message_count: int,
        video_id: str | None = None,
    ) -> None:
        """
        插入或更新某个会话的长期记忆摘要
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO conversation_summaries (
                    user_id, session_id, video_id, summary, message_count, updated_at
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, session_id, video_id)
                DO UPDATE SET
                    summary = excluded.summary,
                    message_count = excluded.message_count,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, session_id, video_id or "", summary, message_count),
            )

    # ======================== 用户画像 ========================

    def get_user_profile(self, user_id: str) -> str:
        """
        获取某个用户的画像，若无则返回空字符串
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT profile
                FROM user_profiles
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()

        return str(row["profile"]) if row else ""

    def upsert_user_profile(self, user_id: str, profile: str) -> None:
        """
        插入或更新某个用户的画像
        """
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO user_profiles (user_id, profile, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id)
                DO UPDATE SET
                    profile = excluded.profile,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (user_id, profile),
            )

    def _connect(self) -> sqlite3.Connection:
        """获取数据库连接，设置 row_factory 以便通过列名访问"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
