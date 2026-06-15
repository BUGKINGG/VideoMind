from dataclasses import dataclass


VIDEO_QA = "video_qa"
VIDEO_SUMMARY = "video_summary"


@dataclass
class IntentClassifier:
    def classify(self, message: str) -> str:
        normalized = message.strip().lower()

        if self._looks_like_summary_request(normalized):
            return VIDEO_SUMMARY

        return VIDEO_QA

    def _looks_like_summary_request(self, message: str) -> bool:
        summary_markers = (
            "总结",
            "概括",
            "摘要",
            "梳理",
            "summary",
            "summarize",
        )
        return any(marker in message for marker in summary_markers)
