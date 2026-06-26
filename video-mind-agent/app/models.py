from dataclasses import dataclass


@dataclass
class ChatTurn:
    """单轮对话记录"""
    role: str       # "user" 或 "assistant"
    content: str    # 对话文本内容


# 单句字幕
@dataclass
class TranscriptSegment:
    """视频字幕的单个片段（单条字幕）"""
    text: str
    start_time: float | None = None   # 字幕开始时间（秒）
    end_time: float | None = None     # 字幕结束时间（秒）


# 完整字幕的切块部分
@dataclass
class TranscriptChunk:
    """将完整字幕按 max_chars 切分后的一个文本块"""
    chunk_id: str                     # 唯一标识，格式: {video_id}_chunk_{index}
    video_id: str
    text: str
    start_time: float | None = None   # 该块第一条字幕的开始时间
    end_time: float | None = None     # 该块最后一条字幕的结束时间


# 向量检索返回的字幕块
@dataclass
class VectorSearchResult:
    """视频字幕块的向量检索结果"""
    chunk: TranscriptChunk
    score: float                      # 余弦相似度分数


# 视频的完整字幕
@dataclass
class VideoTranscript:
    """一个视频的完整字幕数据"""
    video_id: str
    title: str
    # 这是一个视频的所有字幕组成的list
    segments: list[TranscriptSegment]

    def full_text(self) -> str:
        """返回所有字幕拼接后的纯文本"""
        return "\n".join(segment.text for segment in self.segments)


# ======================== 对话记忆相关模型（来自朋友版本的整合） ========================

@dataclass
class ConversationMemory:
    """
    一条被向量化的对话记忆记录。
    每次对话结束后，将"用户问题 + 助手回答"打包成一条记忆，
    向量化后存入 Qdrant 的 conversation_memories collection，
    用于后续的历史记忆检索。
    """
    memory_id: str                    # 唯一标识，格式: conversation:{user_message_id}:{assistant_message_id}
    user_id: str
    session_id: str
    video_id: str
    content: str                      # 记忆文本内容（用户问题 + 助手回答的拼接）
    message_start_id: int | None = None   # 对应 conversation_messages 表中用户消息的 id
    message_end_id: int | None = None     # 对应 conversation_messages 表中助手消息的 id


@dataclass
class MemorySearchResult:
    """历史对话记忆的向量检索结果"""
    memory: ConversationMemory
    score: float                      # 余弦相似度分数
