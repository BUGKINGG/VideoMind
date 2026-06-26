from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from langgraph.graph import END, START, StateGraph

from app.models import ChatTurn, ConversationMemory, TranscriptChunk
from app.services.intent_classifier import VIDEO_QA, VIDEO_SUMMARY, IntentClassifier

if TYPE_CHECKING:
    from app.agent.service import SimpleAgentService


class AgentGraphState(TypedDict, total=False):
    """
    LangGraph 状态图中流转的状态字典。

    包含多层记忆的完整上下文：
    - history:            短期记忆（最近 12 条对话）
    - memory_summary:     长期记忆摘要（LLM 定期压缩的对话历史）
    - user_profile:       用户画像（偏好与身份信息）
    - retrieved_memories: 检索到的相关历史对话记忆
    - retrieved_chunks:   检索到的相关视频字幕块
    """
    user_id: str
    session_id: str
    video_id: str
    message: str

    intent: str
    resolved_owner_user_id: str
    history: list[ChatTurn]
    memory_summary: str
    user_profile: str
    retrieved_memories: list[ConversationMemory]
    retrieved_chunks: list[TranscriptChunk]
    answer: str
    route: str


class AgentGraphRunner:
    """
    基于 LangGraph 的视频对话编排器。

    状态流程图：
        START -> load_context -> classify_intent
                              /              \\
                     video_summary       video_qa
                              \\              /
                               save_conversation
                                      |
                                     END

    load_context 节点负责加载所有记忆层：
    视频数据 + 短期记忆 + 长期摘要 + 用户画像
    """

    def __init__(self, service: "SimpleAgentService") -> None:
        self.service = service

        # 基于关键词匹配判断意图：总结 or 问答
        self.intent_classifier = IntentClassifier()
        self.graph = self._build_graph()

    def run(self, state: AgentGraphState) -> AgentGraphState:
        """
        运行 LangGraph 状态图，返回最终状态（包含 answer 等）
        """
        return self.graph.invoke(state)

    def _build_graph(self):
        """
        构建并编译 LangGraph 状态图
        """
        graph = StateGraph(AgentGraphState)
        graph.add_node("load_context", self.load_context)
        graph.add_node("classify_intent", self.classify_intent)
        graph.add_node("video_qa", self.video_qa)
        graph.add_node("video_summary", self.video_summary)
        graph.add_node("save_conversation", self.save_conversation)

        graph.add_edge(START, "load_context")
        graph.add_edge("load_context", "classify_intent")
        graph.add_conditional_edges(
            "classify_intent",
            self.route_by_intent,
            {
                VIDEO_QA: "video_qa",
                VIDEO_SUMMARY: "video_summary",
            },
        )
        graph.add_edge("video_qa", "save_conversation")
        graph.add_edge("video_summary", "save_conversation")
        graph.add_edge("save_conversation", END)
        return graph.compile()

    def load_context(self, state: AgentGraphState) -> AgentGraphState:
        """
        加载上下文节点：从 SQLite / 内存缓存恢复所有记忆层。

        加载内容：
        - 视频数据（字幕 + 切块）
        - 短期记忆（对话历史，最近 12 条）
        - 长期记忆摘要
        - 用户画像
        """
        resolved_owner_user_id = self.service._ensure_video_loaded(
            video_id=state["video_id"],
            owner_user_id=state["user_id"],
        )
        conversation_key = self.service.video_conversation_key(
            user_id=state["user_id"],
            session_id=state["session_id"],
            video_id=state["video_id"],
        )
        # 短期记忆（最近 12 条对话记录）
        history = self.service._get_or_load_history(
            conversation_key=conversation_key,
            user_id=state["user_id"],
            session_id=state["session_id"],
            video_id=state["video_id"],
        )
        # 长期记忆摘要
        memory_summary = self.service._get_or_load_memory_summary(
            conversation_key=conversation_key,
            user_id=state["user_id"],
            session_id=state["session_id"],
            video_id=state["video_id"],
        )
        # 用户画像
        user_profile = self.service._get_or_load_user_profile(state["user_id"])
        return {
            **state,
            "resolved_owner_user_id": resolved_owner_user_id,
            "memory_summary": memory_summary,
            "user_profile": user_profile,
            "history": history,
        }

    def classify_intent(self, state: AgentGraphState) -> AgentGraphState:
        """
        意图分类节点：判断用户是想做视频总结还是视频问答
        """
        intent = self.intent_classifier.classify(state["message"])
        return {**state, "intent": intent, "route": intent}

    def route_by_intent(self, state: AgentGraphState) -> str:
        """根据意图路由到不同子图"""
        return state.get("intent", VIDEO_QA)

    def video_qa(self, state: AgentGraphState) -> AgentGraphState:
        """
        视频问答节点：RAG 检索 + 多层记忆上下文 + LLM 生成回答。

        检索流程：
        1. 从 Qdrant 检索相关视频字幕块
        2. 从 Qdrant 检索相关历史对话记忆
        3. 从 SQLite 加载视频总结
        4. 将所有记忆层注入 VideoQA.build_prompt()
        """
        transcript = self.service.transcript_store.get_transcript(
            state["video_id"],
            owner_user_id=state["resolved_owner_user_id"],
        )

        # 在 Qdrant 中检索相关视频字幕块
        retrieved_chunks = self.service.find_relevant_video_chunks(
            user_id=state["user_id"],
            video_id=state["video_id"],
            question=state["message"],
            transcript_owner_user_id=state["resolved_owner_user_id"],
        )

        # 在 Qdrant 中检索相关历史对话记忆
        retrieved_memories = self.service.find_relevant_conversation_memories(
            user_id=state["user_id"],
            video_id=state["video_id"],
            question=state["message"],
        )

        # 加载已有的视频总结
        summary = self.service.video_repository.load_summary(
            state["video_id"],
            owner_user_id=state["resolved_owner_user_id"],
        )

        # 生成回答（注入全部记忆层）
        answer = self.service.video_qa.answer(
            transcript=transcript,
            question=state["message"],
            relevant_chunks=retrieved_chunks,
            history=state.get("history", []),
            summary=summary,
            memory_summary=state.get("memory_summary", ""),
            user_profile=state.get("user_profile", ""),
            relevant_memories=retrieved_memories,
        )
        return {
            **state,
            "answer": answer,
            "retrieved_chunks": retrieved_chunks,
            "retrieved_memories": retrieved_memories,
        }

    def video_summary(self, state: AgentGraphState) -> AgentGraphState:
        """
        视频总结节点：生成视频的结构化摘要并持久化。

        持久化后问答节点可以加载并引用该总结。
        """
        summary_result = self.service.summarize_video(
            video_id=state["video_id"],
            owner_user_id=state["resolved_owner_user_id"],
        )
        summary = summary_result["summary"]

        # 持久化总结，便于后续问答引用
        self.service.video_repository.save_summary(
            video_id=state["video_id"],
            summary=summary,
            owner_user_id=state["resolved_owner_user_id"],
        )

        return {**state, "answer": summary, "retrieved_chunks": [], "retrieved_memories": []}

    def save_conversation(self, state: AgentGraphState) -> AgentGraphState:
        """
        保存对话节点：统一调用 record_conversation_turns 保存对话，
        并自动触发记忆索引、摘要更新、画像更新。
        """
        history = state.get("history", [])
        history = self.service.record_conversation_turns(
            user_id=state["user_id"],
            session_id=state["session_id"],
            history=history,
            user_content=state["message"],
            assistant_content=state["answer"],
            video_id=state["video_id"],
        )
        return {**state, "history": history}
