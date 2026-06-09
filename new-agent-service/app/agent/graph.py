from __future__ import annotations

from typing import TYPE_CHECKING, TypedDict

from langgraph.graph import END, START, StateGraph

from app.models import ChatTurn, TranscriptChunk
from app.services.intent_classifier import VIDEO_QA, VIDEO_SUMMARY, IntentClassifier

if TYPE_CHECKING:
    from app.agent.service import SimpleAgentService


class AgentGraphState(TypedDict, total=False):
    user_id: str
    session_id: str
    video_id: str
    message: str
    intent: str
    resolved_owner_user_id: str
    history: list[ChatTurn]
    retrieved_chunks: list[TranscriptChunk]
    answer: str
    route: str


class AgentGraphRunner:
    def __init__(self, service: "SimpleAgentService") -> None:
        self.service = service

        # 就是靠匹配有没有“总结”这些字符出现，以此判断是总结还是视频问答
        self.intent_classifier = IntentClassifier()
        self.graph = self._build_graph()

    def run(self, state: AgentGraphState) -> AgentGraphState:
        return self.graph.invoke(state)

    def _build_graph(self):
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
        resolved_owner_user_id = self.service._ensure_video_loaded(
            video_id=state["video_id"],
            owner_user_id=state["user_id"],
        )
        conversation_key = self.service.video_conversation_key(
            user_id=state["user_id"],
            session_id=state["session_id"],
            video_id=state["video_id"],
        )
        history = self.service._get_or_load_history(
            conversation_key=conversation_key,
            user_id=state["user_id"],
            session_id=state["session_id"],
            video_id=state["video_id"],
        )
        return {
            **state,
            "resolved_owner_user_id": resolved_owner_user_id,
            "history": history,
        }

    def classify_intent(self, state: AgentGraphState) -> AgentGraphState:
        intent = self.intent_classifier.classify(state["message"])
        return {**state, "intent": intent, "route": intent}

    def route_by_intent(self, state: AgentGraphState) -> str:
        return state.get("intent", VIDEO_QA)

    def video_qa(self, state: AgentGraphState) -> AgentGraphState:
        transcript = self.service.transcript_store.get_transcript(
            state["video_id"],
            owner_user_id=state["resolved_owner_user_id"],
        )
        retrieved_chunks = self.service.find_relevant_video_chunks(
            user_id=state["user_id"],
            video_id=state["video_id"],
            question=state["message"],
            transcript_owner_user_id=state["resolved_owner_user_id"],
        )
        answer = self.service.video_qa.answer(
            transcript=transcript,
            question=state["message"],
            relevant_chunks=retrieved_chunks,
            history=state.get("history", []),
        )
        return {**state, "answer": answer, "retrieved_chunks": retrieved_chunks}

    def video_summary(self, state: AgentGraphState) -> AgentGraphState:
        summary = self.service.summarize_video(
            video_id=state["video_id"],
            owner_user_id=state["resolved_owner_user_id"],
        )
        return {**state, "answer": summary["summary"], "retrieved_chunks": []}

    def save_conversation(self, state: AgentGraphState) -> AgentGraphState:
        history = state.get("history", [])
        user_turn = ChatTurn(role="user", content=state["message"])
        assistant_turn = ChatTurn(role="assistant", content=state["answer"])

        history.append(user_turn)
        history.append(assistant_turn)
        self.service.conversation_repository.add_turn(
            state["user_id"],
            state["session_id"],
            user_turn,
            video_id=state["video_id"],
        )
        self.service.conversation_repository.add_turn(
            state["user_id"],
            state["session_id"],
            assistant_turn,
            video_id=state["video_id"],
        )
        return {**state, "history": history}
