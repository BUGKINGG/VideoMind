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
        for i, c in enumerate(relevant_chunks):
            print(f"[DEBUG] chunk[{i}] start={c.start_time} end={c.end_time} text={c.text[:30]}")

        def fmt_chunk(chunk):
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
            for turn in history[-6:]
        )

        return (
            "你是 VideoMind 的视频学习助手。你的唯一知识来源是以下视频字幕内容。\n"
            "你必须严格遵守以下规则：\n"
            "1. 如果用户需要专业知识问答时，只根据提供的视频字幕内容回答问题\n"
            "2. 如果字幕中包含答案，请基于字幕内容详细回答，并尽可能引用相关时间点\n"
            "3. 如果字幕中没有相关信息，你必须明确回答：\"根据该视频的内容，没有找到相关信息。\"\n"
            "4. 如果字幕中没有相关信息，你可以根据自己的知识进行推断，但需明确这是你自己的知识。\n"
            "5. 用户说过的话也同样重要，需要记住，因为用户可能会继续追问等。\n"
            "6. 不要暴露出自己是根据视频字幕知道的，如果用户问到视频内容，你回答是根据视频内容知道的。\n"
            "7. 保持友好、专业的对话语气\n\n"
            f"视频标题：{transcript.title}\n"
            f"最近对话：\n{history_context or '暂无'}\n\n"
            f"相关字幕片段：\n{relevant_context or '没有找到相关字幕'}\n\n"
            f"用户问题：{question}\n\n"
        )
