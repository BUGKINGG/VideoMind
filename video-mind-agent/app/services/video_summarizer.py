from dataclasses import dataclass
from app.llm.client import LLMClient
from app.models import TranscriptChunk, VideoTranscript

@dataclass
class VideoSummarizer:
    llm_client: LLMClient

    def summarize(self, transcript: VideoTranscript, chunks: list[TranscriptChunk]) -> str:
        '''
        进行总结
        1.先把视频字幕分段总结append进数组，然后在对数组里的内容进行再一次总结
        :param transcript:
        :param chunks:
        :return:
        '''

        '''
        获得一串一串（chunk）的总结内容，组成数组
        '''
        chunk_summaries = [
            self.summarize_chunk(transcript.title, chunk.text)
            for chunk in chunks
        ]

        '''
        最终总结的提示词
        '''
        final_prompt = self.build_final_summary_prompt(
            title=transcript.title,
            chunk_summaries=chunk_summaries,
        )
        return self.llm_client.generate([{"role": "user", "content": final_prompt}])

    '''
    一串一串的总结内容
    '''
    def summarize_chunk(self, title: str, chunk_text: str) -> str:
        prompt = self.build_chunk_summary_prompt(title=title, chunk_text=chunk_text)
        return self.llm_client.generate([{"role": "user", "content": prompt}])


    '''
    返回chunk总结的提示词
    '''
    def build_chunk_summary_prompt(self, title: str, chunk_text: str) -> str:
        return (
            "你正在处理一段视频字幕的分片。请总结这段内容，要求：\n"
            "1. 保留关键事实、核心观点；\n"
            "2. 对于论述性内容（观点、建议、判断），必须同时保留：结论 和 支撑该结论的理由/依据/数据；\n"
            "3. 用简洁中文输出，不要过度发散。\n\n"
            f"视频标题：{title}\n"
            f"字幕片段：\n{chunk_text}"
        )

    '''
    返回最终总结的提示词
    '''
    def build_final_summary_prompt(self, title: str, chunk_summaries: list[str]) -> str:
        chunks_text = "\n\n---\n\n".join(
            f"【第{i+1}段总结】\n{s}" for i, s in enumerate(chunk_summaries)
        )

        return (
            "你是一位擅长结构化总结的视频学习助手。请基于以下分段总结，"
            "输出一份完整、有深度的视频学习总结，直接给出你的回答即可，不用回复“好的”等内容。\n\n"
            "输出要求：\n"
            "- 使用 Markdown 格式；\n"
            "- 语言自然、专业，适合学习者阅读；\n"
            "- 对于每个核心观点，必须说明其背后的原因、依据或逻辑，避免只给结论；\n"
            "- 互动提问要具体、有针对性，能引导用户结合视频内容深入思考或实践。\n\n"
            "请严格按以下四个板块输出：\n\n"
            "## 1. 一句话总结\n"
            "用 1-2 句话概括视频核心主旨。\n\n"
            "## 2. 核心要点\n"
            "列出 3-6 个关键要点。每个要点使用如下格式：\n"
            "- **要点标题**：结论/观点概述\n"
            "  - **理由/依据**：支撑该结论的关键论据、数据、逻辑或背景（必须写，不能省略）\n\n"
            "## 3. 适合学习者复习的笔记\n"
            "按主题或时间线整理结构化笔记，保留关键概念、步骤、数据、结论。使用层级列表（- 或 1. 2. 3.）。\n\n"
            "## 4. 互动提问\n"
            "基于视频内容，提出 3 个引导性问题。要求：\n"
            "- 问题不能泛泛而谈（如'你学到了什么'），必须紧扣视频具体观点、方法或案例；\n"
            "- 可以引导用户反思、对比、实践或延伸思考；\n"
            "- 每个问题单独一行。\n\n"
            f"视频标题：{title}\n\n"
            f"分段总结：\n\n{chunks_text}"
        )

    def summarize_stream(self, transcript: VideoTranscript, chunks: list[TranscriptChunk]):
        """
        流式总结：chunk summary 阶段同步（必须等所有 chunk 总结完），
        final summary 阶段流式输出
        """
        # 1. 同步阶段：逐 chunk 总结（这部分无法流式，必须等全部完成）
        chunk_summaries = [
            self.summarize_chunk(transcript.title, chunk.text)
            for chunk in chunks
        ]

        # 2. 流式阶段：final summary 逐 token 产出
        final_prompt = self.build_final_summary_prompt(
            title=transcript.title,
            chunk_summaries=chunk_summaries,
        )
        for token in self.llm_client.generate_stream([{"role": "user", "content": final_prompt}]):
            yield token
