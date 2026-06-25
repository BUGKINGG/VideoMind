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
        if any(marker in message for marker in summary_markers):
            return True

        # 用户可能在追问刚才总结的内容，而不是重新总结
        follow_up_markers = (
            "刚才讲了什么",
            "刚才说了什么",
            "前面讲了什么",
            "之前讲了什么",
            "刚才总结",
            "前面总结",
            "之前总结",
            "你刚才",
            "你前面",
            "你之前",
        )
        return any(marker in message for marker in follow_up_markers)
