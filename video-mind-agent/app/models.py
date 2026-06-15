from dataclasses import dataclass


@dataclass
class ChatTurn:
    role: str
    content: str


# 单句字幕
@dataclass
class TranscriptSegment:
    text: str
    start_time: float | None = None
    end_time: float | None = None

# 完整字幕的切块部分
@dataclass
class TranscriptChunk:
    chunk_id: str
    video_id: str
    text: str
    start_time: float | None = None
    end_time: float | None = None


# 向量检索返回的字幕块
@dataclass
class VectorSearchResult:
    chunk: TranscriptChunk
    score: float

# 视频的完整字幕
@dataclass
class VideoTranscript:
    video_id: str
    title: str

    # 这是一个视频的所有字幕组成的list
    segments: list[TranscriptSegment]

    def full_text(self) -> str:
        return "\n".join(segment.text for segment in self.segments)
