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

    def _read_json(self) -> dict:
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            return {}
        return json.loads(self.rfile.read(content_length).decode("utf-8"))

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
