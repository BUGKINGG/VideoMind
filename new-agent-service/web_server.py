from __future__ import annotations

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from app.agent.service import SimpleAgentService


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
HOST = "127.0.0.1"
PORT = 8765

agent = SimpleAgentService()


class AgentWebHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        # 后台运行测试服务时不输出每次请求的访问日志
        return

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path == "/api/health":
                self._send_json({"status": "ok"})
                return

            if path == "/api/videos":
                self._send_json({"videos": agent.video_repository.list_videos()})
                return

            super().do_GET()
        except Exception as error:
            self._send_json(
                {"error": f"Unexpected server error: {error}"},
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            body = self._read_json()
            if path == "/api/chat":
                self._handle_chat(body)
                return
            if path == "/api/summary":
                self._handle_summary(body)
                return
            if path == "/api/process":
                self._handle_process(body)
                return
            self._send_json({"error": "API route not found"}, status=HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError) as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except RuntimeError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_GATEWAY)
        except Exception as error:
            self._send_json({"error": f"Unexpected server error: {error}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def _handle_chat(self, body: dict) -> None:
        user_id = self._required(body, "user_id")
        session_id = self._required(body, "session_id")
        video_id = self._required(body, "video_id")
        question = self._required(body, "question")

        result = agent.run_agent(
            user_id=user_id,
            session_id=session_id,
            video_id=video_id,
            message=question,
        )
        self._send_json(result)

    def _handle_summary(self, body: dict) -> None:
        video_id = self._required(body, "video_id")
        owner_user_id = body.get("user_id") or "__shared__"
        self._send_json(agent.summarize_video(video_id, owner_user_id=owner_user_id))

    def _handle_process(self, body: dict) -> None:
        """
        一体化接口：接收字幕文本 → 存储 → 切块 → 索引 → 总结 → 返回结果
        供 Java 后端调用
        """
        print(f"[DEBUG] /api/process body keys: {list(body.keys())}")
        video_id = self._required(body, "video_id")
        title = self._required(body, "title")
        transcript_text = self._required(body, "transcript_text")
        user_id = body.get("user_id") or "__shared__"
        segments = body.get("segments")

        print(f"[DEBUG] /api/process: video_id={video_id}, title={title[:30] if title else 'EMPTY'}, user_id={user_id}, text_len={len(transcript_text)}")

        # 1. 存储字幕（优先用结构化 segments，否则 fallback 纯文本）
        if segments is not None and len(segments) > 0:
            print(f"[DEBUG] 使用 segments 路径，共 {len(segments)} 条")
            agent.add_video_transcript_with_segments(
                video_id=video_id,
                title=title,
                segments=segments,
                owner_user_id=user_id,
            )
        else:
            print(f"[DEBUG] 使用纯文本路径")
            agent.add_video_transcript(
                video_id=video_id,
                title=title,
                transcript_text=transcript_text,
                owner_user_id=user_id,
            )

        # 3. 生成总结
        result = agent.summarize_video(video_id=video_id, owner_user_id=user_id)

        self._send_json({
            "code": 200,
            "video_id": result["video_id"],
            "title": result["title"],
            "summary": result["summary"],
        })

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            print(f"[WARN] Content-Length is 0 or missing, headers={dict(self.headers)}")
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        print(f"[DEBUG] Received body: {raw[:500]}")
        return json.loads(raw)

    def _required(self, body: dict, key: str) -> str:
        value = str(body.get(key, "")).strip()
        if not value:
            raise ValueError(f"{key} is required")
        return value

    def _send_json(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), AgentWebHandler)
    print(f"VideoMind test UI: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
