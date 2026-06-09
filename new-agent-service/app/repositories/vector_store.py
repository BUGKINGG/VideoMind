from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
from pathlib import Path
import sqlite3

from app.core.config import get_data_path
from app.models import TranscriptChunk, VectorSearchResult


DEFAULT_OWNER_USER_ID = "__shared__"


@dataclass
class SQLiteVectorStore:
    db_path: Path = field(default_factory=lambda: get_data_path("vector_store.db"))

    def __post_init__(self) -> None:
        self.db_path = Path(self.db_path)
        self.init_db()

    def init_db(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS video_chunk_vectors (
                    chunk_id TEXT NOT NULL,
                    video_id TEXT NOT NULL,
                    owner_user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    vector_json TEXT NOT NULL,
                    start_time REAL,
                    end_time REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (chunk_id, owner_user_id)
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_video_chunk_vectors_owner_video
                ON video_chunk_vectors(owner_user_id, video_id)
                """
            )

    def upsert_chunks(
        self,
        chunks: list[TranscriptChunk],
        vectors: list[list[float]],
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        if not chunks:
            return 0

        video_ids = {chunk.video_id for chunk in chunks}
        if len(video_ids) != 1:
            raise ValueError("all chunks must belong to the same video")
        video_id = chunks[0].video_id

        with self._connect() as conn:
            conn.execute(
                "DELETE FROM video_chunk_vectors WHERE video_id = ? AND owner_user_id = ?",
                (video_id, owner_user_id),
            )
            conn.executemany(
                """
                INSERT INTO video_chunk_vectors (
                    chunk_id, video_id, owner_user_id, content, vector_json, start_time, end_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, owner_user_id) DO UPDATE SET
                    video_id = excluded.video_id,
                    content = excluded.content,
                    vector_json = excluded.vector_json,
                    start_time = excluded.start_time,
                    end_time = excluded.end_time,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.video_id,
                        owner_user_id,
                        chunk.text,
                        json.dumps(vector),
                        chunk.start_time,
                        chunk.end_time,
                    )
                    for chunk, vector in zip(chunks, vectors)
                ],
            )
        return len(chunks)

    def search(
        self,
        query_vector: list[float],
        owner_user_id: str,
        video_id: str,
        limit: int = 3,
    ) -> list[VectorSearchResult]:
        rows = self._load_candidate_rows(owner_user_id=owner_user_id, video_id=video_id)
        scored_results = []

        for row in rows:
            stored_vector = json.loads(row["vector_json"])
            if len(query_vector) != len(stored_vector):
                continue
            score = self._cosine_similarity(query_vector, stored_vector)
            chunk = TranscriptChunk(
                chunk_id=row["chunk_id"],
                video_id=row["video_id"],
                text=row["content"],
                start_time=row["start_time"],
                end_time=row["end_time"],
            )
            scored_results.append(VectorSearchResult(chunk=chunk, score=score))

        scored_results.sort(key=lambda result: result.score, reverse=True)
        return scored_results[:limit]

    def count_chunks(self, owner_user_id: str = DEFAULT_OWNER_USER_ID, video_id: str | None = None) -> int:
        query = "SELECT COUNT(*) FROM video_chunk_vectors WHERE owner_user_id = ?"
        params: list[object] = [owner_user_id]

        if video_id:
            query += " AND video_id = ?"
            params.append(video_id)

        with self._connect() as conn:
            return int(conn.execute(query, params).fetchone()[0])

    def _load_candidate_rows(self, owner_user_id: str, video_id: str) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT chunk_id, video_id, content, vector_json, start_time, end_time
                FROM video_chunk_vectors
                WHERE owner_user_id = ? AND video_id = ?
                """,
                (owner_user_id, video_id),
            ).fetchall()
        return rows

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _cosine_similarity(self, first: list[float], second: list[float]) -> float:
        if len(first) != len(second):
            raise ValueError("vector dimensions must match")

        dot = sum(left * right for left, right in zip(first, second))
        first_length = math.sqrt(sum(value * value for value in first))
        second_length = math.sqrt(sum(value * value for value in second))

        if first_length == 0 or second_length == 0:
            return 0.0
        return dot / (first_length * second_length)
