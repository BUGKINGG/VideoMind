from dataclasses import dataclass, field
from pathlib import Path

from app.agent.graph import AgentGraphRunner
from app.llm.client import AnthropicLLMClient, LLMClient
from app.llm.embedding import EmbeddingClient, get_default_embedding_client
from app.models import ChatTurn, TranscriptChunk
from app.repositories.conversation_repository import SQLiteConversationRepository
from app.repositories.vector_store import DEFAULT_OWNER_USER_ID, SQLiteVectorStore
from app.repositories.video_repository import SQLiteVideoRepository
from app.services.video_qa import VideoQA
from app.services.video_summarizer import VideoSummarizer
from app.transcripts.store import TranscriptStore


@dataclass
class SimpleAgentService:
    
    llm_client: LLMClient = field(default_factory=AnthropicLLMClient.from_env)
    embedding_client: EmbeddingClient = field(default_factory=get_default_embedding_client)
    vector_store: SQLiteVectorStore = field(default_factory=SQLiteVectorStore)
    video_repository: SQLiteVideoRepository = field(default_factory=SQLiteVideoRepository)
    conversation_repository: SQLiteConversationRepository = field(
        default_factory=SQLiteConversationRepository
    )
    # 会话的键是userid:session_id
    conversations: dict[str, list[ChatTurn]] = field(default_factory=dict)
    transcript_store: TranscriptStore = field(default_factory=TranscriptStore)

    def __post_init__(self) -> None:
        self.video_summarizer = VideoSummarizer(self.llm_client)
        self.video_qa = VideoQA(self.llm_client)
        self.agent_graph = AgentGraphRunner(self)

    def chat(self, user_id: str, session_id: str, message: str) -> dict:
        conversation_key = f"{user_id}:{session_id}"
        history = self._get_or_load_history(
            conversation_key=conversation_key,
            user_id=user_id,
            session_id=session_id,
        )

        user_turn = ChatTurn(role="user", content=message)
        history.append(user_turn)
        self.conversation_repository.add_turn(user_id, session_id, user_turn)

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
        query_vector = self.embedding_client.embed(question)
        search_results = self.vector_store.search(
            query_vector=query_vector,
            owner_user_id=user_id,
            video_id=video_id,
            limit=limit,
        )

        if not search_results:
            search_results = self.vector_store.search(
                query_vector=query_vector,
                owner_user_id=DEFAULT_OWNER_USER_ID,
                video_id=video_id,
                limit=limit,
            )

        if search_results:
            return [result.chunk for result in search_results]

        return self.transcript_store.find_relevant_chunks(
            video_id=video_id,
            question=question,
            limit=limit,
            owner_user_id=transcript_owner_user_id or user_id,
        )

    # 加载到内存中
    def _ensure_video_loaded(self, video_id: str, owner_user_id: str) -> str:
        if self.transcript_store.has_video(video_id, owner_user_id=owner_user_id):
            return owner_user_id

        transcript = self.video_repository.load_transcript(
            video_id=video_id,
            owner_user_id=owner_user_id,
        )
        chunks = self.video_repository.load_chunks(
            video_id=video_id,
            owner_user_id=owner_user_id,
        )

        if transcript is None and owner_user_id != DEFAULT_OWNER_USER_ID:
            resolved_owner_user_id = DEFAULT_OWNER_USER_ID
            transcript = self.video_repository.load_transcript(
                video_id=video_id,
                owner_user_id=resolved_owner_user_id,
            )
            chunks = self.video_repository.load_chunks(
                video_id=video_id,
                owner_user_id=resolved_owner_user_id,
            )
        else:
            resolved_owner_user_id = owner_user_id

        if transcript is None:
            raise ValueError(f"Video transcript not found: {video_id}")

        self.transcript_store.restore_video(
            transcript=transcript,
            chunks=chunks,
            owner_user_id=resolved_owner_user_id,
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
        if conversation_key not in self.conversations:
            self.conversations[conversation_key] = self.conversation_repository.recent_turns(
                user_id=user_id,
                session_id=session_id,
                video_id=video_id,
            )
        return self.conversations[conversation_key]

    def _generate_answer(self, user_id: str, message: str, history: list[ChatTurn]) -> str:
        messages = [
            {
                "role": "user",
                "content": (
                    "You are VideoMind, an AI video learning assistant. "
                    "Answer in Chinese. Be concise and helpful."
                ),
            }
        ]

        for turn in history[-8:]:
            messages.append({"role": turn.role, "content": turn.content})

        return self.llm_client.generate(messages)
