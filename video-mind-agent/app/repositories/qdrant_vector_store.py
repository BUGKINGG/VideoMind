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

from app.models import TranscriptChunk


@dataclass
class SearchResult:
    chunk: TranscriptChunk
    score: float


class QdrantVectorStore:
    """
    基于 Qdrant 的向量存储，替换 SQLiteVectorStore。
    保持接口一致：upsert_chunks / search
    """

    def __init__(
            self,
            host: str = "localhost",
            port: int = 6333,
            collection_name: str = "video_chunks",
            vector_size: int = 768,
    ):
        self.client = QdrantClient(host=host, port=port)
        self.collection_name = collection_name
        self.vector_size = vector_size
        self._ensure_collection()

    def _ensure_collection(self):
        """如果 collection 不存在则创建（Cosine 距离）；维度不匹配则重建"""
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