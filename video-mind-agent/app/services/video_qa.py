from dataclasses import dataclass

from app.llm.client import LLMClient
from app.models import ChatTurn, ConversationMemory, TranscriptChunk, VideoTranscript


@dataclass
class VideoQA:
    """
    视频问答服务：构建包含多层记忆上下文的提示词，调用 LLM 生成回答。

    提示词中注入的记忆层次：
    1. 用户画像（长期偏好）
    2. 长期会话摘要（压缩的对话历史）
    3. 相关历史记忆（向量检索 + Rerank 的相关过往对话）
    4. 短期记忆（最近对话轮次）
    5. 视频字幕相关片段（RAG 检索）
    """
    llm_client: LLMClient

    def answer(
        self,
        transcript: VideoTranscript,
        question: str,
        relevant_chunks: list[TranscriptChunk],
        history: list[ChatTurn],
        summary: str | None = None,
        memory_summary: str = "",
        user_profile: str = "",
        relevant_memories: list[ConversationMemory] | None = None,
    ) -> str:
        """
        非流式生成回答
        """
        prompt = self.build_prompt(
            transcript=transcript,
            question=question,
            relevant_chunks=relevant_chunks,
            history=history,
            summary=summary,
            memory_summary=memory_summary,
            user_profile=user_profile,
            relevant_memories=relevant_memories or [],
        )
        return self.llm_client.generate([{"role": "user", "content": prompt}])

    def build_prompt(
        self,
        transcript: VideoTranscript,
        question: str,
        relevant_chunks: list[TranscriptChunk],
        history: list[ChatTurn],
        summary: str | None = None,
        memory_summary: str = "",
        user_profile: str = "",
        relevant_memories: list[ConversationMemory] | None = None,
    ) -> str:
        """
        构建包含所有记忆层次的问答提示词。

        记忆优先级：
        视频总结 > 视频字幕片段 > 相关历史记忆 > 长期摘要 > 短期对话 > 用户画像
        """
        for i, c in enumerate(relevant_chunks):
            print(f"[DEBUG] chunk[{i}] start={c.start_time} end={c.end_time} text={c.text[:30]}")

        def fmt_chunk(chunk):
            """格式化字幕块，保留时间戳信息"""
            # 如果 text 已经包含逐条时间戳，直接返回
            if chunk.text and "[0." in chunk.text or "[1" in chunk.text or "[2" in chunk.text:
                return chunk.text
            # 兜底：旧数据或没有时间戳的情况
            if chunk.start_time is not None and chunk.end_time is not None:
                return f"[{chunk.start_time:.1f}s - {chunk.end_time:.1f}s] {chunk.text}"
            return chunk.text

        relevant_context = "\n\n".join(
            fmt_chunk(chunk) for chunk in relevant_chunks
        )
        history_context = "\n".join(
            f"{turn.role}: {turn.content}"
            for turn in history[-8:]
        )
        summary_context = summary.strip() if summary else ""
        memory_context = "\n\n".join(
            memory.content
            for memory in relevant_memories or []
        )

        # 构建分段 prompt，按记忆层次组织
        parts = []
        # 用户画像
        parts.append(f"用户画像：\n{user_profile or '暂无'}\n")
        # 长期会话摘要
        parts.append(f"长期会话摘要：\n{memory_summary or '暂无'}\n")
        # 相关历史记忆
        parts.append(f"相关历史记忆：\n{memory_context or '暂无'}\n")

        # 系统指令
        parts.append(
            "你是 VideoMind 的视频学习助手。你的唯一知识来源是以下视频内容（包括视频总结和相关字幕片段）。\n"
            "你必须严格遵守以下规则：\n"
            "1. 回答问题时优先参考「视频总结」，因为总结已经提炼了视频的核心事实、观点和逻辑；\n"
            "2. 如果总结或字幕中包含答案，请基于视频内容详细回答，并尽可能引用相关时间点；\n"
            "3. 如果视频内容中没有相关信息，你必须明确回答：\"根据该视频的内容，没有找到相关信息。\"；\n"
            "4. 在规则 3 的前提下，你可以根据自己的知识进行合理推断，但需明确说明这是你自己的知识；\n"
            "5. 用户说过的话也同样重要，需要记住，因为用户可能会继续追问；\n"
            "6. 不要暴露出自己是根据视频字幕知道的，如果用户问到视频内容，你回答是根据视频内容知道的；\n"
            "7. 保持友好、专业的对话语气。\n"
        )

        # 视频信息
        parts.append(f"视频标题：{transcript.title}")
        if summary_context:
            parts.append(f"视频总结：\n{summary_context}\n")

        # 上下文
        parts.append(f"最近对话：\n{history_context or '暂无'}\n")
        parts.append(f"相关字幕片段：\n{relevant_context or '没有找到相关字幕'}\n")
        parts.append(f"用户问题：{question}\n")

        return "\n".join(parts)

    def answer_stream(
                self,
                transcript: VideoTranscript,
                question: str,
                relevant_chunks: list[TranscriptChunk],
                history: list[ChatTurn],
                summary: str | None = None,
                memory_summary: str = "",
                user_profile: str = "",
                relevant_memories: list[ConversationMemory] | None = None,
        ):
        """
        流式回答，逐 token yield。
        参数与 answer() 一致，只是通过 generate_stream 返回生成器。
        """
        prompt = self.build_prompt(
            transcript=transcript,
            question=question,
            relevant_chunks=relevant_chunks,
            history=history,
            summary=summary,
            memory_summary=memory_summary,
            user_profile=user_profile,
            relevant_memories=relevant_memories or [],
        )
        for token in self.llm_client.generate_stream([{"role": "user", "content": prompt}]):
            yield token
