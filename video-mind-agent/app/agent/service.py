import os
from dataclasses import dataclass, field
from pathlib import Path

from app.agent.graph import AgentGraphRunner
from app.core.config import get_embedding_config
from app.llm.client import AnthropicLLMClient, LLMClient
from app.llm.embedding import EmbeddingClient, get_default_embedding_client
from app.models import ChatTurn, ConversationMemory, TranscriptChunk, VideoTranscript, TranscriptSegment
from app.repositories.conversation_repository import SQLiteConversationRepository
from app.repositories.qdrant_vector_store import QdrantVectorStore
from app.repositories.video_repository import SQLiteVideoRepository
from app.constants import DEFAULT_OWNER_USER_ID
from app.services.reranker import LocalReranker
from app.services.video_qa import VideoQA
from app.services.video_summarizer import VideoSummarizer
from app.transcripts.store import TranscriptStore


@dataclass
class SimpleAgentService:
    """
    VideoMind Agent 的核心服务编排类。

    负责协调所有组件，管理多层记忆系统：
    1. 短期记忆（最近 12 条对话轮次）—— 内存 + SQLite conversation_messages
    2. 长期记忆摘要（每 8 轮触发 LLM 总结）—— 内存 + SQLite conversation_summaries
    3. 用户画像记忆（检测信号词后 LLM 提取偏好）—— 内存 + SQLite user_profiles
    4. 历史记忆检索（对话向量化索引到 Qdrant，提问时检索+Rerank）—— Qdrant conversation_memories
    """
    # ======================== 基础设施 ========================
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
    reranker: LocalReranker = field(default_factory=LocalReranker)

    # ======================== 内存缓存 ========================
    # 短期记忆：{user_id:session_id:video_id → [ChatTurn, ...]}
    conversations: dict[str, list[ChatTurn]] = field(default_factory=dict)
    # 长期记忆摘要：{user_id:session_id:video_id → summary_str}
    conversation_summaries: dict[str, str] = field(default_factory=dict)
    # 用户画像：{user_id → profile_str}
    user_profiles: dict[str, str] = field(default_factory=dict)

    # 长期记忆摘要的触发阈值
    memory_summary_min_turns: int = 8       # 至少积累 8 条消息才开始生成摘要
    memory_summary_update_every_turns: int = 8  # 每新增 8 条消息触发一次增量更新

    # 视频字幕的内存缓存
    transcript_store: TranscriptStore = field(default_factory=TranscriptStore)

    def __post_init__(self) -> None:
        """
        初始化三个子服务：视频总结、问答助手、LangGraph 图执行器
        """
        self.video_summarizer = VideoSummarizer(self.llm_client)
        self.video_qa = VideoQA(self.llm_client)
        self.agent_graph = AgentGraphRunner(self)

    # ======================== 纯文本对话 ========================

    def chat(self, user_id: str, session_id: str, message: str) -> dict:
        """
        纯文本对话（无视频上下文），使用多层记忆系统
        """
        conversation_key = f"{user_id}:{session_id}"

        # 载入多层记忆
        history = self._get_or_load_history(
            conversation_key=conversation_key,
            user_id=user_id,
            session_id=session_id,
        )
        # 长期总结记忆
        memory_summary = self._get_or_load_memory_summary(
            conversation_key=conversation_key,
            user_id=user_id,
            session_id=session_id,
        )
        # 用户偏好记忆
        user_profile = self._get_or_load_user_profile(user_id)
        # 与问题相关的历史对话记忆（向量检索 + Rerank）
        relevant_memories = self.find_relevant_conversation_memories(
            user_id=user_id,
            question=message,
        )

        # 包装消息
        history_for_prompt = [*history, ChatTurn(role="user", content=message)]

        # 生成回答
        answer = self._generate_answer(
            user_id=user_id,
            message=message,
            history=history_for_prompt,
            memory_summary=memory_summary,
            user_profile=user_profile,
            relevant_memories=relevant_memories,
        )

        # 统一保存对话并触发所有记忆的后处理
        history = self.record_conversation_turns(
            user_id=user_id,
            session_id=session_id,
            history=history,
            user_content=message,
            assistant_content=answer,
        )

        return {
            "user_id": user_id,
            "session_id": session_id,
            "answer": answer,
            "message_count": len(history),
        }

    # ======================== 视频字幕管理 ========================

    def add_video_transcript(
        self,
        video_id: str,
        title: str,
        transcript_text: str,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> dict:
        """
        存入视频纯文本字幕（无时间戳），持久化到 SQLite
        """
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

    def add_video_transcript_from_file(
        self,
        video_id: str,
        title: str,
        file_path: str | Path,
        owner_user_id: str = DEFAULT_OWNER_USER_ID,
    ) -> dict:
        """
        从字幕文件读取并存入视频字幕
        """
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
        """
        将视频字幕文本切分成块并向量化索引到 Qdrant
        """
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
        """
        将视频字幕块向量化后索引到 Qdrant video_chunks collection
        """
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
        """
        对视频进行两级摘要（先逐块再合并为结构化输出）
        """
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
        """
        视频上下文问答入口，委托给 LangGraph AgentGraphRunner
        """
        return self.run_agent(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
            message=question,
        )

    def run_agent(self, user_id: str, session_id: str, video_id: str, message: str) -> dict:
        """
        通过 LangGraph 状态图执行视频问答流程：
        load_context → classify_intent → video_qa/video_summary → save_conversation
        """
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
            "user_profile": result.get("user_profile", ""),
            "sources": [
                {
                    "chunk_id": chunk.chunk_id,
                    "text": chunk.text,
                    "start_time": chunk.start_time,
                    "end_time": chunk.end_time,
                }
                for chunk in result.get("retrieved_chunks", [])
            ],
            "memories": [
                {
                    "memory_id": memory.memory_id,
                    "session_id": memory.session_id,
                    "video_id": memory.video_id,
                    "content": memory.content,
                }
                for memory in result.get("retrieved_memories", [])
            ],
        }

    # ======================== 视频字幕检索 ========================

    def find_relevant_video_chunks(
        self,
        user_id: str,
        video_id: str,
        question: str,
        limit: int = 3,
        transcript_owner_user_id: str | None = None,
    ) -> list[TranscriptChunk]:
        """
        检索与问题相关的视频字幕块。

        流程：Qdrant 向量检索（先按用户过滤，失败则用默认用户，最后回退到 SQLite 关键词匹配）
        → Reranker 精排 → 返回 top-K
        """
        candidate_limit = max(limit * 4, limit)
        print(f"[DEBUG] find_relevant_video_chunks: user_id={user_id}, video_id={video_id}, question={question[:30]}")
        try:
            query_vector = self.embedding_client.embed(question)
            search_results = None

            # 尝试按当前用户、默认用户依次搜索
            for owner in (user_id, DEFAULT_OWNER_USER_ID, None):
                try:
                    results = self.vector_store.search(
                        query_vector=query_vector,
                        owner_user_id=owner,
                        video_id=video_id,
                        limit=candidate_limit,
                    )
                    print(f"[DEBUG] Qdrant search owner={owner!r} returned {len(results)} results")
                    if results:
                        search_results = results
                        break
                except Exception as error:
                    print(f"[WARN] Qdrant search owner={owner!r} failed: {error}")
                    continue

            if search_results:
                chunks = [result.chunk for result in search_results]
                # Reranker 精排
                return self.reranker.rerank(
                    query=question,
                    items=chunks,
                    text_getter=lambda chunk: chunk.text,
                    limit=limit,
                )
        except Exception as error:
            print(f"[WARN] embedding 或 Qdrant 检索失败，回退到 SQLite keyword 搜索: {error}")

        # 最终回退：SQLite 关键词匹配
        chunks = self.transcript_store.find_relevant_chunks(
            video_id=video_id,
            question=question,
            limit=candidate_limit,
            owner_user_id=transcript_owner_user_id or user_id,
        )
        return self.reranker.rerank(
            query=question,
            items=chunks,
            text_getter=lambda chunk: chunk.text,
            limit=limit,
        )

    # ======================== 短期记忆（对话历史） ========================

    def _ensure_video_loaded(self, video_id: str, owner_user_id: str) -> str:
        """
        确保视频数据已加载到内存缓存中。
        查找顺序：内存缓存 → SQLite（用户数据 → 默认用户数据）→ 报错
        """
        # 1. 先检查内存缓存
        if hasattr(self.transcript_store, 'has_video') and \
           self.transcript_store.has_video(video_id, owner_user_id=owner_user_id):
            return owner_user_id

        # 2. 从 SQLite 加载
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

        # 3. 加载到内存缓存
        if hasattr(self.transcript_store, 'restore_video'):
            self.transcript_store.restore_video(
                transcript=transcript, chunks=chunks, owner_user_id=resolved_owner_user_id
            )

        return resolved_owner_user_id

    def video_conversation_key(self, user_id: str, session_id: str, video_id: str) -> str:
        """生成视频上下文会话的唯一键"""
        return f"{user_id}:{session_id}:{video_id}"

    def _conversation_key(
        self,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
    ) -> str:
        """生成会话键（兼容有/无 video_id 两种场景）"""
        if video_id:
            return self.video_conversation_key(user_id, session_id, video_id)
        return f"{user_id}:{session_id}"

    def _get_or_load_history(
        self,
        conversation_key: str,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
    ) -> list[ChatTurn]:
        """
        获取短期对话记忆。
        优先从内存缓存读取，未命中则从 SQLite 加载最近 12 条。
        """
        if conversation_key not in self.conversations:
            self.conversations[conversation_key] = self.conversation_repository.recent_turns(
                user_id=user_id,
                session_id=session_id,
                video_id=video_id,
            )
        return self.conversations[conversation_key]

    # ======================== 长期记忆摘要 ========================

    def _get_or_load_memory_summary(
        self,
        conversation_key: str,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
    ) -> str:
        """
        获取长期记忆摘要。
        优先从内存缓存读取，未命中则从 SQLite conversation_summaries 表加载。
        """
        if conversation_key not in self.conversation_summaries:
            self.conversation_summaries[conversation_key] = self.conversation_repository.get_summary(
                user_id=user_id,
                session_id=session_id,
                video_id=video_id,
            )
        return self.conversation_summaries[conversation_key]

    def _maybe_update_memory_summary(
        self,
        user_id: str,
        session_id: str,
        video_id: str | None = None,
    ) -> str:
        """
        条件触发长期记忆摘要的增量更新。

        触发条件：
        1. 会话消息数 ≥ memory_summary_min_turns（默认 8 条）
        2. 尚无摘要，或消息数是 memory_summary_update_every_turns 的整数倍

        防止：低质量对话（如只有寒暄）也因为消息数达标而触发摘要。
        如果最近 5 条消息中用户消息平均长度 < 10 字符，则延迟摘要（不触发）。
        """
        turn_count = self.conversation_repository.count_turns(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
        )
        if turn_count < self.memory_summary_min_turns:
            return ""

        conversation_key = self._conversation_key(user_id, session_id, video_id)
        previous_summary = self._get_or_load_memory_summary(
            conversation_key=conversation_key,
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
        )
        should_update = (
            not previous_summary
            or turn_count % self.memory_summary_update_every_turns == 0
        )
        if not should_update:
            return previous_summary

        # 质量检查：最近若干条消息中，用户消息太短则延迟摘要
        recent_turns_for_check = self.conversation_repository.recent_turns(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
            limit=10,
        )
        user_msgs = [
            t.content.strip()
            for t in recent_turns_for_check
            if t.role == "user"
        ]
        if user_msgs and sum(len(m) for m in user_msgs) / len(user_msgs) < 10:
            # 平均用户消息长度过短（寒暄为主），暂不触发摘要
            return previous_summary

        recent_turns = self.conversation_repository.recent_turns(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
            limit=10,
        )
        try:
            new_summary = self._summarize_conversation_memory(
                previous_summary=previous_summary,
                recent_turns=recent_turns,
            )
        except Exception as error:
            print(f"[WARN] Failed to update conversation memory summary: {error}")
            return previous_summary

        if not new_summary or "LLM is not configured" in new_summary:
            return previous_summary

        # 持久化 + 更新内存缓存
        self.conversation_repository.upsert_summary(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
            summary=new_summary,
            message_count=turn_count,
        )
        self.conversation_summaries[conversation_key] = new_summary
        return new_summary

    def _summarize_conversation_memory(
        self,
        previous_summary: str,
        recent_turns: list[ChatTurn],
    ) -> str:
        """
        调用 LLM 将已有长期摘要与最近对话合并，生成新的增量摘要。

        要求 LLM 输出 300 字以内的简洁中文摘要，只保留：
        - 用户已确认的信息
        - 重要结论
        - 未解决问题
        - 视频内容的相关线索
        """
        recent_context = "\n".join(
            f"{turn.role}: {turn.content}"
            for turn in recent_turns
        )
        prompt = (
            "你是 VideoMind 的长期记忆整理器。请把已有长期摘要和最近对话合并成一段稳定记忆。\n"
            "要求：\n"
            "1. 保留用户已经问过的问题、已经确认的信息、重要结论和未解决问题。\n"
            "2. 如果对话围绕某个视频字幕展开，要保留用户关注的视频内容线索。\n"
            "3. 不要编造对话中没有出现的信息。\n"
            "4. 用简洁中文输出，控制在 300 字以内。\n\n"
            f"已有长期摘要：\n{previous_summary or '暂无'}\n\n"
            f"最近对话：\n{recent_context or '暂无'}\n\n"
            "新的长期摘要："
        )
        return self.llm_client.generate([{"role": "user", "content": prompt}])

    # ======================== 用户画像记忆 ========================

    def _get_or_load_user_profile(self, user_id: str) -> str:
        """
        获取用户画像。
        优先从内存缓存读取，未命中则从 SQLite user_profiles 表加载。
        """
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = self.conversation_repository.get_user_profile(user_id)
        return self.user_profiles[user_id]

    def _maybe_update_user_profile(
        self,
        user_id: str,
        user_content: str,
        assistant_content: str,
    ) -> str:
        """
        条件触发用户画像更新。

        触发条件：
        1. 用户消息中包含个人描述信号词（如"我叫"、"我喜欢"、"记住"等）
        2. 助手回答没有错误标记
        3. 用户消息不是记忆自查类问题
        """
        if not self._should_update_user_profile(
            user_content=user_content,
            assistant_content=assistant_content,
        ):
            return self._get_or_load_user_profile(user_id)

        current_profile = self._get_or_load_user_profile(user_id)
        try:
            new_profile = self._merge_user_profile(
                current_profile=current_profile,
                user_content=user_content,
                assistant_content=assistant_content,
            )
        except Exception as error:
            print(f"[WARN] Failed to update user profile: {error}")
            return current_profile

        if not new_profile or "LLM is not configured" in new_profile:
            return current_profile

        # 持久化 + 更新内存缓存
        self.conversation_repository.upsert_user_profile(
            user_id=user_id,
            profile=new_profile,
        )
        self.user_profiles[user_id] = new_profile
        return new_profile

    def _should_update_user_profile(
        self,
        user_content: str,
        assistant_content: str,
    ) -> bool:
        """
        判断当前对话是否应该触发用户画像更新。

        排除条件：
        - 空消息
        - 助手回答包含错误标记
        - 用户消息是记忆自查类问题（如"我叫什么"）
        - 用户消息不包含任何个人描述信号词
        """
        user_text = user_content.strip()
        assistant_text = assistant_content.strip()
        if not user_text or not assistant_text:
            return False

        # 排除错误回答
        error_markers = [
            "LLM is not configured",
            "Cannot connect to the LLM API",
            "Cannot connect to the embedding API",
            "[生成错误",
        ]
        if any(marker in assistant_text for marker in error_markers):
            return False

        # 排除记忆自查问题（用户只是在回忆，不是在提供新信息）
        question_like_markers = [
            "我叫什么",
            "我有没有",
            "我之前",
            "我刚才",
            "记得我",
        ]
        if any(marker in user_text for marker in question_like_markers):
            return False

        # 检测个人描述信号词
        profile_signals = [
            "我叫",
            "我的名字",
            "我是",
            "我在",
            "我喜欢",
            "我不喜欢",
            "我希望",
            "我想要",
            "我正在",
            "我主要",
            "我更喜欢",
            "以后回答",
            "以后你",
            "记住",
            "帮我记住",
        ]
        return any(signal in user_text for signal in profile_signals)

    def _merge_user_profile(
        self,
        current_profile: str,
        user_content: str,
        assistant_content: str,
    ) -> str:
        """
        调用 LLM 将新的对话信息合并到现有用户画像中。

        LLM 指令：
        - 只保留长期稳定、跨会话有用的信息（姓名、身份、学习目标、偏好等）
        - 不保存一次性临时问题、无意义寒暄、未经确认的猜测
        - 无新信息时原样返回
        - 输出 300 字以内中文
        """
        prompt = (
            "你是 VideoMind 的用户画像整理器。请根据当前用户画像和最新一轮对话，更新用户画像。\n"
            "用户画像只保存长期稳定、跨会话有用的信息，例如：姓名、身份、学习目标、内容偏好、回答风格偏好、长期关注领域。\n"
            "不要保存一次性的临时问题、无意义寒暄、模型自己的回答错误、未经用户确认的猜测。\n"
            "如果新对话没有值得进入用户画像的信息，请原样返回当前画像。\n"
            "用简洁中文输出，控制在 300 字以内。\n\n"
            f"当前用户画像：\n{current_profile or '暂无'}\n\n"
            f"用户最新消息：\n{user_content}\n\n"
            f"助手最新回答：\n{assistant_content}\n\n"
            "更新后的用户画像："
        )
        return self.llm_client.generate([{"role": "user", "content": prompt}])

    # ======================== 历史记忆检索 ========================

    def find_relevant_conversation_memories(
        self,
        user_id: str,
        question: str,
        video_id: str | None = None,
        limit: int = 4,
    ) -> list[ConversationMemory]:
        """
        检索与当前问题相关的历史对话记忆。

        流程：
        1. 将问题向量化
        2. 在 Qdrant conversation_memories collection 中搜索（先按 video_id 过滤，若无结果则跨视频搜索）
        3. Reranker 精排
        4. 返回 top-K（默认 4 条）
        """
        try:
            candidate_limit = max(limit * 4, limit)
            query_vector = self.embedding_client.embed(question)
            search_results = self.vector_store.search_conversation_memories(
                query_vector=query_vector,
                user_id=user_id,
                video_id=video_id,
                limit=candidate_limit,
            )
            # 如果按 video_id 过滤没结果，尝试跨所有视频搜索
            if not search_results and video_id:
                search_results = self.vector_store.search_conversation_memories(
                    query_vector=query_vector,
                    user_id=user_id,
                    limit=candidate_limit,
                )
        except Exception as error:
            print(f"[WARN] Failed to search conversation memories: {error}")
            return []

        memories = [result.memory for result in search_results]
        return self.reranker.rerank(
            query=question,
            items=memories,
            text_getter=lambda memory: memory.content,
            limit=limit,
        )

    def _index_conversation_memory(
        self,
        user_id: str,
        session_id: str,
        video_id: str | None,
        user_content: str,
        assistant_content: str,
        user_message_id: int,
        assistant_message_id: int,
    ) -> None:
        """
        将一条对话轮次向量化后索引到 Qdrant conversation_memories collection。

        会先通过 _should_index_conversation_memory 做质量拦截，
        只对高质量的对话进行索引。
        """
        if not self._should_index_conversation_memory(
            user_content=user_content,
            assistant_content=assistant_content,
        ):
            return

        memory_content = self._build_conversation_memory_content(
            user_content=user_content,
            assistant_content=assistant_content,
        )
        if not memory_content.strip():
            return

        memory = ConversationMemory(
            memory_id=f"conversation:{user_message_id}:{assistant_message_id}",
            user_id=user_id,
            session_id=session_id,
            video_id=video_id or "",
            content=memory_content,
            message_start_id=user_message_id,
            message_end_id=assistant_message_id,
        )

        try:
            vector = self.embedding_client.embed(memory.content)
            self.vector_store.upsert_conversation_memory(memory=memory, vector=vector)
        except Exception as error:
            print(f"[WARN] Failed to index conversation memory: {error}")

    def _should_index_conversation_memory(
        self,
        user_content: str,
        assistant_content: str,
    ) -> bool:
        """
        检查一条对话是否值得被索引到长期记忆。

        以下情况不会索引（视为低质量或噪声）：
        - 空消息
        - 轻量寒暄（"ok"、"好的"、"谢谢"、"你好"等），且助手回答 < 80 字符
        - 助手回答包含错误标记
        - 用户消息是记忆自查类问题（如"我有没有问过"）
        - 用户消息很短（< 20 字符）且助手回答包含低价值标记（"没有找到"、"无法确认"等）
        - 用户消息 < 4 字符且助手消息 < 80 字符
        """
        user_text = user_content.strip()
        assistant_text = assistant_content.strip()
        if not user_text or not assistant_text:
            return False

        lowered_user = user_text.lower()
        lightweight_messages = {
            "ok",
            "好的",
            "好",
            "嗯",
            "谢谢",
            "谢谢你",
            "你好",
            "hi",
            "hello",
        }
        if lowered_user in lightweight_messages and len(assistant_text) < 80:
            return False

        # 排除 LLM 错误
        error_markers = [
            "LLM is not configured",
            "Cannot connect to the LLM API",
            "Cannot connect to the embedding API",
            "[生成错误",
        ]
        if any(marker in assistant_text for marker in error_markers):
            return False

        # 排除记忆自查问题（避免循环：用记忆查记忆）
        memory_lookup_questions = [
            "我有没有问过",
            "我刚才问",
            "我之前问",
            "我叫什么",
            "你记得我",
        ]
        if any(marker in user_text for marker in memory_lookup_questions):
            return False

        # 排除低价值回答（用户消息短 + 助手说没找到/无法判断）
        low_value_answer_markers = [
            "没有找到相关信息",
            "无法确认",
            "无法判断",
            "没有提到",
        ]
        if len(user_text) < 20 and any(marker in assistant_text for marker in low_value_answer_markers):
            return False

        return len(user_text) >= 4 or len(assistant_text) >= 80

    def _build_conversation_memory_content(
        self,
        user_content: str,
        assistant_content: str,
        max_chars: int = 2000,
    ) -> str:
        """
        构建待索引的对话记忆文本（用户消息 + 助手回答），超过最大长度截断
        """
        content = f"用户：{user_content}\n助手：{assistant_content}"
        if len(content) <= max_chars:
            return content
        return content[:max_chars] + "\n..."

    # ======================== 统一对话保存入口 ========================

    def record_conversation_turns(
        self,
        user_id: str,
        session_id: str,
        history: list[ChatTurn],
        user_content: str,
        assistant_content: str,
        video_id: str | None = None,
    ) -> list[ChatTurn]:
        """
        统一保存对话轮次，并触发所有记忆的后处理。

        这是对话保存的唯一入口，依次执行：
        1. 将用户和助手的消息写入 SQLite conversation_messages 表
        2. 更新内存中的短期记忆缓存
        3. 向量化并索引到 Qdrant（带质量拦截）
        4. 检查是否需要更新长期记忆摘要
        5. 检查是否需要更新用户画像
        """
        user_turn = ChatTurn(role="user", content=user_content)
        assistant_turn = ChatTurn(role="assistant", content=assistant_content)

        history.append(user_turn)
        history.append(assistant_turn)

        # 持久化对话轮次
        user_message_id = self.conversation_repository.add_turn(
            user_id, session_id, user_turn, video_id=video_id,
        )
        assistant_message_id = self.conversation_repository.add_turn(
            user_id, session_id, assistant_turn, video_id=video_id,
        )

        # 向量化并索引对话记忆（带质量拦截）
        self._index_conversation_memory(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
            user_content=user_content,
            assistant_content=assistant_content,
            user_message_id=user_message_id,
            assistant_message_id=assistant_message_id,
        )

        # 条件触发长期摘要更新
        self._maybe_update_memory_summary(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
        )

        # 条件触发用户画像更新
        self._maybe_update_user_profile(
            user_id=user_id,
            user_content=user_content,
            assistant_content=assistant_content,
        )

        return history

    # ======================== 纯文本问答生成 ========================

    def _generate_answer(
        self,
        user_id: str,
        message: str,
        history: list[ChatTurn],
        memory_summary: str = "",
        user_profile: str = "",
        relevant_memories: list[ConversationMemory] | None = None,
    ) -> str:
        """
        纯文字对话时生成回答（无视频上下文）。

        系统提示词中注入：
        - 用户画像
        - 长期记忆摘要
        - 相关历史记忆
        - 最近 8 轮对话
        """
        memory_context = "\n\n".join(
            memory.content
            for memory in relevant_memories or []
        )
        messages = [
            {
                "role": "system",
                "content": (
                    "You are VideoMind, an AI video learning assistant. "
                    "Answer in Chinese. Be concise and helpful.\n"
                    f"User profile:\n{user_profile or 'None'}\n\n"
                    f"Long-term conversation memory:\n{memory_summary or 'None'}\n\n"
                    f"Relevant conversation memories:\n{memory_context or 'None'}"
                ),
            }
        ]

        for turn in history[-8:]:
            messages.append({"role": turn.role, "content": turn.content})

        return self.llm_client.generate(messages)

    # ======================== 带时间戳的字幕处理 ========================

    def add_video_transcript_with_segments(
                self,
                video_id: str,
                title: str,
                segments: list[dict],
                owner_user_id: str = DEFAULT_OWNER_USER_ID,
        ) -> dict:
        """
        直接接收带时间戳的 segments，绕过纯文本切分，保留时间戳。

        用于前端传入逐条字幕的精确时间戳场景。
        """
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

        # 3. 切分 chunks（带时间戳）
        chunks = self._build_chunks_from_segments(transcript, max_chars=300)

        # 日志确认
        for c in chunks:
            print(f"[DEBUG] built chunk: id={c.chunk_id}, start={c.start_time}, end={c.end_time}")

        # 4. 保存 chunks（video_repository 支持时间戳）
        self.video_repository.save_chunks(video_id, chunks, owner_user_id=owner_user_id)

        # 5. 向量索引到 Qdrant
        self.index_video_chunks(video_id=video_id, owner_user_id=owner_user_id, chunks=chunks)

        # 6. 加载到内存缓存
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
        """
        按 max_chars 切分带时间戳的字幕 segments。
        每个 chunk 的 start/end 取第一个和最后一个 segment 的时间戳。
        """
        chunks = []
        current_segments = []
        current_length = 0
        chunk_index = 0

        for segment in transcript.segments:
            seg_len = len(segment.text)
            # 超过阈值且已有内容，则截断创建新 chunk
            if current_length + seg_len > max_chars and current_segments:
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
