import os
from dataclasses import dataclass, field
from pathlib import Path

from app.agent.graph import AgentGraphRunner
from app.core.config import get_embedding_config
from app.llm.client import AnthropicLLMClient, LLMClient
from app.llm.embedding import EmbeddingClient, get_default_embedding_client
from app.models import ChatTurn, TranscriptChunk, VideoTranscript, TranscriptSegment
from app.repositories.conversation_repository import SQLiteConversationRepository
from app.repositories.qdrant_vector_store import QdrantVectorStore
from app.repositories.video_repository import SQLiteVideoRepository
from app.constants import DEFAULT_OWNER_USER_ID
from app.services.video_qa import VideoQA
from app.services.video_summarizer import VideoSummarizer
from app.transcripts.store import TranscriptStore


@dataclass
class SimpleAgentService:

    llm_client: LLMClient = field(default_factory=AnthropicLLMClient.from_env)
    embedding_client: EmbeddingClient = field(default_factory=get_default_embedding_client)
    vector_store: QdrantVectorStore = field(default_factory=lambda: QdrantVectorStore(
        host=os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", "6333")),
        vector_size=get_embedding_config().dimensions or 4096,
    ))
    video_repository: SQLiteVideoRepository = field(default_factory=SQLiteVideoRepository)
    conversation_repository: SQLiteConversationRepository = field(
        default_factory=SQLiteConversationRepository
    )
    # 会话的键是userid:session_id
    conversations: dict[str, list[ChatTurn]] = field(default_factory=dict)
    transcript_store: TranscriptStore = field(default_factory=TranscriptStore)

    '''
    初始化三个agent，分别是视频总结agent、问答助手agent、图agent
    '''
    def __post_init__(self) -> None:
        self.video_summarizer = VideoSummarizer(self.llm_client)
        self.video_qa = VideoQA(self.llm_client)
        self.agent_graph = AgentGraphRunner(self)

    '''
    对话函数
    '''
    def chat(self, user_id: str, session_id: str, message: str) -> dict:
        conversation_key = f"{user_id}:{session_id}"
        '''
        载入记忆
        '''
        history = self._get_or_load_history(
            conversation_key=conversation_key,
            user_id=user_id,
            session_id=session_id,
        )

        '''
        把message内容包装成一个完整的带role和content的对话类
        '''
        user_turn = ChatTurn(role="user", content=message)
        history.append(user_turn)
        self.conversation_repository.add_turn(user_id, session_id, user_turn)

        '''
        模拟一次对话
        '''
        answer = self._generate_answer(user_id=user_id, message=message, history=history)
        assistant_turn = ChatTurn(role="assistant", content=answer)


        history.append(assistant_turn)
        self.conversation_repository.add_turn(user_id, session_id, assistant_turn)

        return {
            "user_id": user_id,
            "session_id": session_id,
            "answer": answer,
            "message_count": len(history),
        }

    # 存transcript，返回video_id,title,segment的长度
    def add_video_transcript(
        self,
        video_id: str,
        title: str,
        transcript_text: str,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> dict:
        result = self.transcript_store.add_video_transcript(
            video_id=video_id,
            title=title,
            transcript_text=transcript_text,
            owner_user_id=owner_user_id,
        )
        transcript = self.transcript_store.get_transcript(video_id, owner_user_id=owner_user_id)
        self.video_repository.save_transcript(
            transcript=transcript,
            owner_user_id=owner_user_id,
        )
        return result

    # 从字幕文件读取transcript，后面前后端接入时可以把文件路径传进来
    def add_video_transcript_from_file(
        self,
        video_id: str,
        title: str,
        file_path: str | Path,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> dict:
        transcript_text = Path(file_path).read_text(encoding="utf-8")
        return self.add_video_transcript(
            video_id=video_id,
            title=title,
            transcript_text=transcript_text,
            owner_user_id=owner_user_id,
        )

    def build_video_chunks(
        self,
        video_id: str,
        max_chars: int = 800,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> dict:
        resolved_owner_user_id = self._ensure_video_loaded(
            video_id=video_id,
            owner_user_id=owner_user_id,
        )
        result = self.transcript_store.build_video_chunks(
            video_id=video_id,
            max_chars=max_chars,
            owner_user_id=resolved_owner_user_id,
        )
        chunks = self.transcript_store.get_or_build_chunks(
            video_id=video_id,
            max_chars=max_chars,
            owner_user_id=resolved_owner_user_id,
        )
        self.video_repository.save_chunks(
            video_id=video_id,
            chunks=chunks,
            owner_user_id=resolved_owner_user_id,
        )
        indexed_count = self.index_video_chunks(
            video_id=video_id,
            owner_user_id=resolved_owner_user_id,
            chunks=chunks,
        )
        return {**result, "indexed_count": indexed_count}

    def index_video_chunks(
        self,
        video_id: str,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
        chunks: list[TranscriptChunk] | None = None,
    ) -> int:
        resolved_owner_user_id = self._ensure_video_loaded(
            video_id=video_id,
            owner_user_id=owner_user_id,
        )
        chunks = chunks or self.transcript_store.get_or_build_chunks(
            video_id=video_id,
            owner_user_id=resolved_owner_user_id,
        )
        vectors = self.embedding_client.embed_many([chunk.text for chunk in chunks])
        return self.vector_store.upsert_chunks(
            chunks=chunks,
            vectors=vectors,
            owner_user_id=resolved_owner_user_id,
        )

    def summarize_video(
        self,
        video_id: str,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> dict:
        '''
        进行视频总结，调用/services/video_summarizer
        :param video_id:
        :param owner_user_id:
        :return:
        '''
        resolved_owner_user_id = self._ensure_video_loaded(
            video_id=video_id,
            owner_user_id=owner_user_id,
        )
        transcript = self.transcript_store.get_transcript(
            video_id,
            owner_user_id=resolved_owner_user_id,
        )
        chunks = self.transcript_store.get_or_build_chunks(
            video_id,
            owner_user_id=resolved_owner_user_id,
        )
        answer = self.video_summarizer.summarize(transcript=transcript, chunks=chunks)

        return {
            "video_id": video_id,
            "title": transcript.title,
            "summary": answer,
        }


    def ask_video(self, user_id: str, session_id: str, video_id: str, question: str) -> dict:
        return self.run_agent(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
            message=question,
        )

    def run_agent(self, user_id: str, session_id: str, video_id: str, message: str) -> dict:
        result = self.agent_graph.run(
            {
                "user_id": user_id,
                "session_id": session_id,
                "video_id": video_id,
                "message": message,
            }
        )
        history = result.get("history", [])

        return {
            "user_id": user_id,
            "session_id": session_id,
            "video_id": video_id,
            "answer": result["answer"],
            "message_count": len(history),
            "route": result.get("route", "video_qa"),
            "sources": [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                }
                for chunk in result.get("retrieved_chunks", [])
            ],
        }

    def find_relevant_video_chunks(
        self,
        user_id: str,
        video_id: str,
        question: str,
        limit: int = 3,
        transcript_owner_user_id: str | None = None,
    ) -> list[TranscriptChunk]:
        print(f"[DEBUG] find_relevant_video_chunks: user_id={user_id}, video_id={video_id}, question={question[:30]}")
        try:
            query_vector = self.embedding_client.embed(question)
            search_results = None

            for owner in (user_id, DEFAULT_OWNER_USER_ID, None):
                try:
                    results = self.vector_store.search(
                        query_vector=query_vector,
                        owner_user_id=owner,
                        video_id=video_id,
                        limit=limit,
                    )
                    print(f"[DEBUG] Qdrant search owner={owner!r} returned {len(results)} results")
                    if results:
                        search_results = results
                        break
                except Exception as error:
                    print(f"[WARN] Qdrant search owner={owner!r} failed: {error}")
                    continue

            if search_results:
                return [result.chunk for result in search_results]
        except Exception as error:
            print(f"[WARN] embedding 或 Qdrant 检索失败，回退到 SQLite keyword 搜索: {error}")

        return self.transcript_store.find_relevant_chunks(
            video_id=video_id,
            question=question,
            limit=limit,
            owner_user_id=transcript_owner_user_id or user_id,
        )

    # 加载到内存中
    def _ensure_video_loaded(self, video_id: str, owner_user_id: str) -> str:
        # 1. 先检查内存缓存（如果 transcript_store 存在）
        if hasattr(self.transcript_store, 'has_video') and \
           self.transcript_store.has_video(video_id, owner_user_id=owner_user_id):
            return owner_user_id

        # 2. 从 SQLite 加载（video_repository 支持时间戳）
        transcript = self.video_repository.load_transcript(video_id, owner_user_id=owner_user_id)
        chunks = self.video_repository.load_chunks(video_id, owner_user_id=owner_user_id)

        if transcript is None and owner_user_id != DEFAULT_OWNER_USER_ID:
            resolved_owner_user_id = DEFAULT_OWNER_USER_ID
            transcript = self.video_repository.load_transcript(video_id, resolved_owner_user_id)
            chunks = self.video_repository.load_chunks(video_id, resolved_owner_user_id)
        else:
            resolved_owner_user_id = owner_user_id

        if transcript is None:
            raise ValueError(f"Video transcript not found: {video_id}")

        # 3. 加载到内存缓存（如果 transcript_store 存在）
        if hasattr(self.transcript_store, 'restore_video'):
            self.transcript_store.restore_video(
                transcript=transcript, chunks=chunks, owner_user_id=resolved_owner_user_id
            )

        return resolved_owner_user_id

    def video_conversation_key(self, user_id: str, session_id: str, video_id: str) -> str:
        return f"{user_id}:{session_id}:{video_id}"

    def _get_or_load_history(
        self,
        conversation_key: str,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
    ) -> list[ChatTurn]:

        '''
        如果短期记忆库里找不到key，则新建一个session作为短期记忆
        否则返回原有的记忆
        :param conversation_key:
        :param user_id:
        :param session_id:
        :param video_id:
        :return:
        '''
        if conversation_key not in self.conversations:
            self.conversations[conversation_key] = self.conversation_repository.recent_turns(
                user_id=user_id,
                session_id=session_id,
                video_id=video_id,
            )
        return self.conversations[conversation_key]

    '''
    纯文字对话时的系统提示词，没有视频以及字幕检索，单纯满足上下文要求
    '''
    def _generate_answer(self, user_id: str, message: str, history: list[ChatTurn]) -> str:
        messages = [
            {
                "role": "system",
                "content": (
                    "You are VideoMind, an AI video learning assistant. "
                    "Answer in Chinese. Be concise and helpful."
                ),
            }
        ]

        for turn in history[-8:]:
            messages.append({"role": turn.role, "content": turn.content})

        return self.llm_client.generate(messages)

    def add_video_transcript_with_segments(
                self,
                video_id: str,
                title: str,
                segments: list[dict],
                owner_user_id: str = DEFAULT_OWNER_USER_ID,
        ) -> dict:
        """直接接收带时间戳的 segments，绕过纯文本切分，保留时间戳"""
        # 1. 构造 VideoTranscript（保留 start_time / end_time）
        transcript_segments = [
            TranscriptSegment(
                text=s.get("text", ""),
                start_time=s.get("start_time"),
                end_time=s.get("end_time"),
            )
            for s in segments
        ]
        transcript = VideoTranscript(
            video_id=video_id,
            title=title,
            segments=transcript_segments,
        )

        # 2. 持久化到 SQLite（video_repository 支持时间戳）
        self.video_repository.save_transcript(transcript, owner_user_id=owner_user_id)

        # 3. 切分 chunks（关键：带时间戳）
        chunks = self._build_chunks_from_segments(transcript, max_chars=300)

        # ===== 加日志确认 =====
        for c in chunks:
            print(f"[DEBUG] built chunk: id={c.chunk_id}, start={c.start_time}, end={c.end_time}")
        # =====================

        # 4. 保存 chunks（video_repository 支持时间戳）
        self.video_repository.save_chunks(video_id, chunks, owner_user_id=owner_user_id)

        # 5. 向量索引（vector_store 也支持时间戳）
        self.index_video_chunks(video_id=video_id, owner_user_id=owner_user_id, chunks=chunks)

        # 6. 尝试加载到内存缓存（如果 transcript_store 存在）
        if hasattr(self.transcript_store, 'restore_video'):
            self.transcript_store.restore_video(
                transcript=transcript, chunks=chunks, owner_user_id=owner_user_id
            )

        return {
            "video_id": video_id,
            "title": title,
            "segments_count": len(transcript_segments),
            "chunks_count": len(chunks),
        }


    def _build_chunks_from_segments(self, transcript: VideoTranscript, max_chars: int = 800) -> list[TranscriptChunk]:
        """按 max_chars 切分，chunk 的 start/end 取第一个和最后一个 segment 的时间戳"""
        chunks = []
        current_segments = []
        current_length = 0
        chunk_index = 0

        for segment in transcript.segments:
            seg_len = len(segment.text)
            # 超过阈值且已有内容，则截断创建新 chunk
            if current_length + seg_len > max_chars and current_segments:
                '''
                把每条字幕的时间戳放在字幕前面，例如
                [42.1s] 我爱VideoMind
                [43.4s] 我是麦
                '''
                chunk_text = "\n".join(
                    f"[{seg.start_time:.1f}s] {seg.text}"
                    for seg in current_segments
                )
                chunk = TranscriptChunk(
                    chunk_id=f"{transcript.video_id}_chunk_{chunk_index}",
                    video_id=transcript.video_id,
                    text=chunk_text,
                    start_time=current_segments[0].start_time,
                    end_time=current_segments[-1].end_time,
                )
                chunks.append(chunk)
                chunk_index += 1
                current_segments = [segment]
                current_length = seg_len
            else:
                current_segments.append(segment)
                current_length += seg_len

        # 最后一个 chunk
        if current_segments:
            chunk_text = "\n".join(
                f"[{seg.start_time:.1f}s] {seg.text}"
                for seg in current_segments
            )
            chunk = TranscriptChunk(
                chunk_id=f"{transcript.video_id}_chunk_{chunk_index}",
                video_id=transcript.video_id,
                text=chunk_text,
                start_time=current_segments[0].start_time,
                end_time=current_segments[-1].end_time,
            )
            chunks.append(chunk)

        return chunks
