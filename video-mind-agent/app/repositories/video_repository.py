from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import sqlite3

from app.core.config import get_data_path
from app.models import TranscriptChunk, TranscriptSegment, VideoTranscript
from app.repositories.vector_store import DEFAULT_OWNER_USER_ID


@dataclass
class SQLiteVideoRepository:
    db_path: Path = field(default_factory=lambda: get_data_path("video_store.db"))

    def __post_init__(self) -> None:
        self.db_path = Path(self.db_path)
        self.init_db()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS videos (
                    video_id TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (video_id, owner_user_id)
                );

                CREATE TABLE IF NOT EXISTS transcript_segments (
                    video_id TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL,
                    segment_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    start_time REAL,
                    end_time REAL,
                    PRIMARY KEY (video_id, owner_user_id, segment_index)
                );

                CREATE TABLE IF NOT EXISTS transcript_chunks (
                    chunk_id TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    start_time REAL,
                    end_time REAL,
                    PRIMARY KEY (chunk_id, owner_user_id)
                );
                """
            )

    def save_transcript(
        self,
        transcript: VideoTranscript,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO videos (video_id, owner_user_id, title)
                VALUES (?, ?, ?)
                ON CONFLICT(video_id, owner_user_id) DO UPDATE SET
                    title = excluded.title,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (transcript.video_id, owner_user_id, transcript.title),
            )
            conn.execute(
                "DELETE FROM transcript_segments WHERE video_id = ? AND owner_user_id = ?",
                (transcript.video_id, owner_user_id),
            )
            conn.executemany(
                """
                INSERT INTO transcript_segments (
                    video_id, owner_user_id, segment_index, content, start_time, end_time
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        transcript.video_id,
                        owner_user_id,
                        index,
                        segment.text,
                        segment.start_time,
                        segment.end_time,
                    )
                    for index, segment in enumerate(transcript.segments)
                ],
            )

    def save_chunks(
        self,
        video_id: str,
        chunks: list[TranscriptChunk],
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM transcript_chunks WHERE video_id = ? AND owner_user_id = ?",
                (video_id, owner_user_id),
            )
            conn.executemany(
                """
                INSERT INTO transcript_chunks (
                    chunk_id, video_id, owner_user_id, content, start_time, end_time
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.video_id,
                        owner_user_id,
                        chunk.text,
                        chunk.start_time,
                        chunk.end_time,
                    )
                    for chunk in chunks
                ],
            )

    def load_transcript(
        self,
        video_id: str,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> VideoTranscript | None:
        with self._connect() as conn:
            video = conn.execute(
                "SELECT title FROM videos WHERE video_id = ? AND owner_user_id = ?",
                (video_id, owner_user_id),
            ).fetchone()
            if video is None:
                return None

            rows = conn.execute(
                """
                SELECT content, start_time, end_time
                FROM transcript_segments
                WHERE video_id = ? AND owner_user_id = ?
                ORDER BY segment_index
                """,
                (video_id, owner_user_id),
            ).fetchall()

        return VideoTranscript(
            video_id=video_id,
            title=video["title"],
            segments=[
                TranscriptSegment(
                    text=row["content"],
                    start_time=row["start_time"],
                    end_time=row["end_time"],
                )
                for row in rows
            ],
        )

    def load_chunks(
        self,
        video_id: str,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> list[TranscriptChunk]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chunk_id, video_id, content, start_time, end_time
                FROM transcript_chunks
                WHERE video_id = ? AND owner_user_id = ?
                ORDER BY chunk_id
                """,
                (video_id, owner_user_id),
            ).fetchall()

        return [
            TranscriptChunk(
                chunk_id=row["chunk_id"],
                video_id=row["video_id"],
                text=row["content"],
                start_time=row["start_time"],
                end_time=row["end_time"],
            )
            for row in rows
        ]

    def list_videos(self, owner_user_id: str = DEFAULT_OWNER_USER_ID) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT video_id, owner_user_id, title, updated_at
                FROM videos
                WHERE owner_user_id IN (?, ?)
                ORDER BY updated_at DESC
                """,
                (owner_user_id, DEFAULT_OWNER_USER_ID),
            ).fetchall()
        return [dict(row) for row in rows]

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
