from __future__ import annotations

from dataclasses import dataclass
import uuid
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)

from app.models import TranscriptChunk, ConversationMemory, MemorySearchResult


@dataclass
class SearchResult:
    """
    视频字幕块的 Qdrant 检索结果
    """
    chunk: TranscriptChunk
    score: float


class QdrantVectorStore:
    """
    基于 Qdrant 的向量存储，管理两个 collection：
    1. video_chunks            — 视频字幕块的向量索引（RAG 检索）
    2. conversation_memories   — 对话记忆的向量索引（历史记忆检索）

    使用确定性 UUID v5 保证幂等 upsert。
    """

    def __init__(
            self,
            host: str = "localhost",
            port: int = 6333,
            collection_name: str = "video_chunks",
            memory_collection_name: str = "conversation_memories",
            vector_size: int = 768,
    ):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.memory_collection_name = memory_collection_name
        self.vector_size = vector_size
        self._ensure_collection()
        self._ensure_memory_collection()

    # ======================== 视频字幕块 collection ========================

    def _ensure_collection(self):
        """
        确保 video_chunks collection 存在且维度匹配，不匹配则重建
        """
        collections = self.client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            return

        info = self.client.get_collection(self.collection_name)
        existing_size = info.config.params.vectors.size
        if existing_size != self.vector_size:
            print(
                f"[WARN] Qdrant collection '{self.collection_name}' 维度不匹配: "
                f"现有 {existing_size} vs 配置 {self.vector_size}，正在删除重建..."
            )
            self.client.delete_collection(self.collection_name)
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def upsert_chunks(
            self,
            chunks: List[TranscriptChunk],
            vectors: List[List[float]],
            owner_user_id: str,
    ) -> int:
        """
        批量 upsert 视频字幕块的向量，使用 UUID v5 保证幂等
        """
        points = []
        for chunk, vector in zip(chunks, vectors):
            # 用确定性 UUID 作为 point id，保证同一 chunk 幂等
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk.chunk_id))

            payload = {
                "chunk_id": chunk.chunk_id,
                "video_id": chunk.video_id,
                "text": chunk.text,
                "start_time": chunk.start_time,
                "end_time": chunk.end_time,
                "owner_user_id": owner_user_id,
            }
            points.append(PointStruct(id=point_id, vector=vector, payload=payload))

        self.client.upsert(collection_name=self.collection_name, points=points)
        return len(points)

    def search(
            self,
            query_vector: List[float],
            owner_user_id: str | None,
            video_id: str,
            limit: int = 3,
    ) -> List[SearchResult]:
        """
        在 video_chunks collection 中按 owner_user_id + video_id 过滤搜索
        """
        must_conditions = [
            FieldCondition(
                key="video_id", match=MatchValue(value=video_id)
            ),
        ]
        if owner_user_id is not None:
            must_conditions.insert(
                0,
                FieldCondition(
                    key="owner_user_id", match=MatchValue(value=owner_user_id)
                ),
            )

        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions),
            limit=limit,
            with_payload=True,
        )

        search_results = []
        for res in results:
            p = res.payload
            chunk = TranscriptChunk(
                chunk_id=p.get("chunk_id"),
                video_id=p.get("video_id"),
                text=p.get("text"),
                start_time=p.get("start_time"),
                end_time=p.get("end_time"),
            )
            search_results.append(SearchResult(chunk=chunk, score=res.score))

        return search_results

    # ======================== 对话记忆 collection ========================

    def _ensure_memory_collection(self):
        """
        确保 conversation_memories collection 存在且维度匹配，不匹配则重建
        """
        collections = self.client.get_collections().collections
        exists = any(c.name == self.memory_collection_name for c in collections)
        if not exists:
            self.client.create_collection(
                collection_name=self.memory_collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )
            return

        info = self.client.get_collection(self.memory_collection_name)
        existing_size = info.config.params.vectors.size
        if existing_size != self.vector_size:
            print(
                f"[WARN] Qdrant collection '{self.memory_collection_name}' 维度不匹配: "
                f"现有 {existing_size} vs 配置 {self.vector_size}，正在删除重建..."
            )
            self.client.delete_collection(self.memory_collection_name)
            self.client.create_collection(
                collection_name=self.memory_collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance.COSINE,
                ),
            )

    def upsert_conversation_memory(
            self,
            memory: ConversationMemory,
            vector: List[float],
    ) -> None:
        """
        将一条对话记忆向量化并存入 Qdrant conversation_memories collection。
        使用 memory_id 的 UUID v5 保证幂等。
        """
        point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, memory.memory_id))
        payload = {
            "memory_id": memory.memory_id,
            "user_id": memory.user_id,
            "session_id": memory.session_id,
            "video_id": memory.video_id,
            "content": memory.content,
            "message_start_id": memory.message_start_id,
            "message_end_id": memory.message_end_id,
        }
        self.client.upsert(
            collection_name=self.memory_collection_name,
            points=[PointStruct(id=point_id, vector=vector, payload=payload)],
        )

    def search_conversation_memories(
            self,
            query_vector: List[float],
            user_id: str,
            video_id: str | None = None,
            limit: int = 4,
    ) -> List[MemorySearchResult]:
        """
        在 conversation_memories collection 中按 user_id（+ 可选 video_id）过滤搜索。
        用于根据用户当前问题检索相关的历史对话记忆。
        """
        must_conditions = [
            FieldCondition(
                key="user_id", match=MatchValue(value=user_id)
            ),
        ]
        if video_id:
            must_conditions.append(
                FieldCondition(
                    key="video_id", match=MatchValue(value=video_id)
                ),
            )

        results = self.client.search(
            collection_name=self.memory_collection_name,
            query_vector=query_vector,
            query_filter=Filter(must=must_conditions),
            limit=limit,
            with_payload=True,
        )

        search_results = []
        for res in results:
            p = res.payload
            memory = ConversationMemory(
                memory_id=p.get("memory_id"),
                user_id=p.get("user_id"),
                session_id=p.get("session_id"),
                video_id=p.get("video_id"),
                content=p.get("content"),
                message_start_id=p.get("message_start_id"),
                message_end_id=p.get("message_end_id"),
            )
            search_results.append(MemorySearchResult(memory=memory, score=res.score))

        return search_results
