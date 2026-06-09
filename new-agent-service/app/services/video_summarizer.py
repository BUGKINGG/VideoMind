from dataclasses import dataclass
from app.llm.client import LLMClient
from app.models import TranscriptChunk, VideoTranscript

@dataclass
class VideoSummarizer:
    llm_client: LLMClient

    def summarize(self, transcript: VideoTranscript, chunks: list[TranscriptChunk]) -> str:
        chunk_summaries = [
            self.summarize_chunk(transcript.title, chunk.text)
            for chunk in chunks
        ]
        final_prompt = self.build_final_summary_prompt(
            title=transcript.title,
            chunk_summaries=chunk_summaries,
        )
        return self.llm_client.generate([{"role": "user", "content": final_prompt}])

    def summarize_chunk(self, title: str, chunk_text: str) -> str:
        prompt = self.build_chunk_summary_prompt(title=title, chunk_text=chunk_text)
        return self.llm_client.generate([{"role": "user", "content": prompt}])

    def build_chunk_summary_prompt(self, title: str, chunk_text: str) -> str:
        return (
            "请总结下面这段视频字幕，只保留重要信息。\n\n"
            f"视频标题：{title}\n"
            f"字幕片段：\n{chunk_text}"
        )

    def build_final_summary_prompt(self, title: str, chunk_summaries: list[str]) -> str:
        return (
            "下面是一个视频按字幕分段得到的多个小总结。"
            "请把它们合并成一个完整的视频总结。\n"
            "请输出：\n"
            "1. 一句话总结\n"
            "2. 核心要点\n"
            "3. 适合学习者复习的笔记\n\n"
            f"视频标题：{title}\n"
            f"分段总结：\n{chr(10).join(chunk_summaries)}"
        )
