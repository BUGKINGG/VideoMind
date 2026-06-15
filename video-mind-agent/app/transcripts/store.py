from pathlib import Path

from app.models import TranscriptChunk, TranscriptSegment, VideoTranscript


class TranscriptStore:
    def __init__(self) -> None:
        # 这里存两个东西：1、视频的完全字幕；2、视频的完全字幕的切块

        # 一个视频的所有字幕，键是(owner_user_id, video_id)，值是VideoTranscript
        self.transcripts: dict[tuple[str, str], VideoTranscript] = {}
        # 一个视频的所有字幕，键是(owner_user_id, video_id)，值是字幕块组成的列表
        self.chunks: dict[tuple[str, str], list[TranscriptChunk]] = {}

    def restore_video(
        self,
        transcript: VideoTranscript,
        chunks: list[TranscriptChunk] | None = None,
        owner_user_id: str = "__shared__",
    ) -> None:
        key = self._key(owner_user_id, transcript.video_id)
        self.transcripts[key] = transcript
        if chunks:
            self.chunks[key] = chunks

    # 存transcript，返回video_id,title,segment的长度
    def add_video_transcript(
        self,
        video_id: str,
        title: str,
        transcript_text: str,
        owner_user_id: str = "__shared__",
    ) -> dict:
        segments = [
            TranscriptSegment(text=line.strip())
            for line in transcript_text.splitlines()
            if line.strip()
        ]
        key = self._key(owner_user_id, video_id)
        self.transcripts[key] = VideoTranscript(
            video_id=video_id,
            title=title,
            segments=segments,
        )
        # 删除旧的切块
        self.chunks.pop(key, None)
        return {
            "video_id": video_id,
            "title": title,
            "segment_count": len(segments),
        }

    # 从字幕文件读取transcript，再复用上面的add_video_transcript
    def add_video_transcript_from_file(
        self,
        video_id: str,
        title: str,
        file_path: str | Path,
        encoding: str = "utf-8",
        owner_user_id: str = "__shared__",
    ) -> dict:
        transcript_text = Path(file_path).read_text(encoding=encoding)
        return self.add_video_transcript(
            video_id=video_id,
            title=title,
            transcript_text=transcript_text,
            owner_user_id=owner_user_id,
        )

    def get_transcript(self, video_id: str, owner_user_id: str = "__shared__") -> VideoTranscript:
        key = self._key(owner_user_id, video_id)
        if key not in self.transcripts:
            raise ValueError(f"Video transcript not found: {video_id}")
        return self.transcripts[key]

    def build_video_chunks(
        self,
        video_id: str,
        max_chars: int = 800,
        owner_user_id: str = "__shared__",
    ) -> dict:
        transcript = self.get_transcript(video_id, owner_user_id=owner_user_id)
        chunks: list[TranscriptChunk] = []
        current_texts: list[str] = []
        current_length = 0

        for segment in transcript.segments:
            segment_text = segment.text.strip()
            if not segment_text:
                continue

            # 如果目前current_texts里面有文本，并且目前块的文本长度加新一句字幕超出了一块的范围
            should_start_new_chunk = current_texts and current_length + len(segment_text) > max_chars
            if should_start_new_chunk:
                chunks.append(
                    TranscriptChunk(
                        chunk_id=f"{video_id}-chunk-{len(chunks) + 1}",
                        video_id=video_id,
                        text="\n".join(current_texts),
                    )
                )
                current_texts = []
                current_length = 0

            current_texts.append(segment_text)
            current_length += len(segment_text)

        if current_texts:
            chunks.append(
                TranscriptChunk(
                    chunk_id=f"{video_id}-chunk-{len(chunks) + 1}",
                    video_id=video_id,
                    text="\n".join(current_texts),
                )
            )

        self.chunks[self._key(owner_user_id, video_id)] = chunks

        return {
            "video_id": video_id,
            "chunk_count": len(chunks),
            "max_chars": max_chars,
        }

    def get_or_build_chunks(
        self,
        video_id: str,
        max_chars: int = 800,
        owner_user_id: str = "__shared__",
    ) -> list[TranscriptChunk]:
        key = self._key(owner_user_id, video_id)
        if key not in self.chunks:
            self.build_video_chunks(
                video_id=video_id,
                max_chars=max_chars,
                owner_user_id=owner_user_id,
            )
        return self.chunks[key]

    def find_relevant_chunks(
        self,
        video_id: str,
        question: str,
        limit: int = 3,
        owner_user_id: str = "__shared__",
    ) -> list[TranscriptChunk]:
        chunks = self.get_or_build_chunks(video_id, owner_user_id=owner_user_id)
        keywords = [word for word in question.lower().split() if len(word) >= 2]
        scored_chunks = []

        for chunk in chunks:
            lower_text = chunk.text.lower()
            score = sum(1 for keyword in keywords if keyword in lower_text)
            if score > 0:
                scored_chunks.append((score, chunk))

        if not scored_chunks:
            return chunks[:limit]

        scored_chunks.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored_chunks[:limit]]

    def has_video(self, video_id: str, owner_user_id: str = "__shared__") -> bool:
        return self._key(owner_user_id, video_id) in self.transcripts

    def _key(self, owner_user_id: str, video_id: str) -> tuple[str, str]:
        return owner_user_id, video_id
