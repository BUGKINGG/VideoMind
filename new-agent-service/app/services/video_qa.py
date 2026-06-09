from dataclasses import dataclass

from app.llm.client import LLMClient
from app.models import ChatTurn, TranscriptChunk, VideoTranscript


@dataclass
class VideoQA:
    llm_client: LLMClient

    def answer(
        self,
        transcript: VideoTranscript,
        question: str,
        relevant_chunks: list[TranscriptChunk],
        history: list[ChatTurn],
    ) -> str:
        prompt = self.build_prompt(
            transcript=transcript,
            question=question,
            relevant_chunks=relevant_chunks,
            history=history,
        )
        return self.llm_client.generate([{"role": "user", "content": prompt}])

    def build_prompt(
        self,
        transcript: VideoTranscript,
        question: str,
        relevant_chunks: list[TranscriptChunk],
        history: list[ChatTurn],
    ) -> str:
        relevant_context = "\n\n".join(chunk.text for chunk in relevant_chunks)
        history_context = "\n".join(
            f"{turn.role}: {turn.content}"
            for turn in history[-6:]
        )

        return (
            "你是 VideoMind 的视频学习助手。请根据给定的视频字幕和最近的对话回答问题。\n"
            "如果字幕里没有答案，请明确说没有在字幕中找到依据。\n\n"
            f"视频标题：{transcript.title}\n"
            f"最近对话：\n{history_context or '暂无'}\n\n"
            f"相关字幕：\n{relevant_context or '没有找到相关字幕'}\n\n"
            f"用户问题：{question}"
        )
