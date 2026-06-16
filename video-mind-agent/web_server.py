from __future__ import annotations

from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from urllib.parse import urlparse

from app.agent.service import SimpleAgentService
from app.models import ChatTurn

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
HOST = "0.0.0.0"
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
            if path == "/api/chat/stream":
                self._handle_chat_stream(body)
                return
            if path == "/api/process/stream":
                self._handle_process_stream(body)
                return
            self._send_json({"error": "API route not found"}, status=HTTPStatus.NOT_FOUND)
        except (ValueError, KeyError) as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_REQUEST)
        except RuntimeError as error:
            self._send_json({"error": str(error)}, status=HTTPStatus.BAD_GATEWAY)
        except Exception as error:
            self._send_json({"error": f"Unexpected server error: {error}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


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


    def _handle_chat_stream(self, body: dict) -> None:
        """对话流式接口：边生成边推 SSE"""
        user_id = str(body.get("user_id", "__shared__"))
        session_id = str(body.get("session_id", "default"))
        video_id = body.get("video_id")
        question = body.get("question")

        if not video_id or not question:
            self._send_sse_error("video_id and question are required")
            return

        # 设置 SSE 响应头
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            # 加载上下文
            print(f"[DEBUG] /api/chat/stream received: user_id={user_id}, session_id={session_id}, video_id={video_id}, question={question[:30]}")
            resolved_owner = agent._ensure_video_loaded(video_id, user_id)
            print(f"[DEBUG] resolved_owner={resolved_owner}")
            transcript = agent.transcript_store.get_transcript(video_id, resolved_owner)
            chunks = agent.find_relevant_video_chunks(
                user_id=user_id,
                video_id=video_id,
                question=question,
                transcript_owner_user_id=resolved_owner,
            )
            print(f"[DEBUG] retrieved {len(chunks)} chunks")
            history = agent._get_or_load_history(
                f"{user_id}:{session_id}:{video_id}",
                user_id=user_id,
                session_id=session_id,
                video_id=video_id,
            )

            # 流式生成
            full_answer = []
            for token in agent.video_qa.answer_stream(transcript, question, chunks, history):
                full_answer.append(token)
                payload = json.dumps({
                    "type": "chunk",
                    "content": token,
                }, ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()

            # 保存对话（流结束后）
            answer = "".join(full_answer)
            user_turn = ChatTurn(role="user", content=question)
            assistant_turn = ChatTurn(role="assistant", content=answer)
            history.append(user_turn)
            history.append(assistant_turn)
            agent.conversation_repository.add_turn(user_id, session_id, user_turn, video_id=video_id)
            agent.conversation_repository.add_turn(user_id, session_id, assistant_turn, video_id=video_id)

            # 推 done
            done_payload = json.dumps({
                "type": "done",
                "answer": answer,
                "sources": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "start_time": chunk.start_time,
                        "end_time": chunk.end_time,
                    }
                    for chunk in chunks
                ],
            }, ensure_ascii=False)
            self.wfile.write(f"data: {done_payload}\n\n".encode("utf-8"))
            self.wfile.flush()
            self.close_connection = True

        except Exception as e:
            self._send_sse_error(str(e))

    def _handle_process_stream(self, body: dict) -> None:
        """视频处理流式接口：存字幕 → 索引 → 流式总结"""
        video_id = self._required(body, "video_id")
        title = self._required(body, "title")
        transcript_text = self._required(body, "transcript_text")
        user_id = body.get("user_id") or "__shared__"
        segments = body.get("segments")

        # 设置 SSE 头
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        try:
            # 1. 存字幕
            if segments is not None and len(segments) > 0:
                agent.add_video_transcript_with_segments(
                    video_id=video_id, title=title, segments=segments, owner_user_id=user_id
                )
            else:
                agent.add_video_transcript(
                    video_id=video_id, title=title, transcript_text=transcript_text, owner_user_id=user_id
                )
                agent.build_video_chunks(video_id=video_id, owner_user_id=user_id)

            resolved_owner = agent._ensure_video_loaded(video_id, user_id)

            # 2. 准备总结（用 resolved_owner，确保内存里有数据）
            transcript = agent.transcript_store.get_transcript(video_id, owner_user_id=resolved_owner)
            chunks = agent.transcript_store.get_or_build_chunks(video_id, owner_user_id=resolved_owner)

            # 3. 流式总结
            full_summary = []
            for token in agent.video_summarizer.summarize_stream(transcript=transcript, chunks=chunks):
                full_summary.append(token)
                payload = json.dumps({
                    "type": "chunk",
                    "content": token,
                }, ensure_ascii=False)
                self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()

            # 4. 推 done
            summary = "".join(full_summary)
            done_payload = json.dumps({
                "type": "done",
                "video_id": video_id,
                "title": title,
                "summary": summary,
            }, ensure_ascii=False)
            self.wfile.write(f"data: {done_payload}\n\n".encode("utf-8"))
            self.wfile.flush()
            self.close_connection = True

        except Exception as e:
            self._send_sse_error(str(e))

    def _send_sse_error(self, message: str) -> None:
        """在 SSE 流中发送错误事件"""
        try:
            payload = json.dumps({"type": "error", "message": message}, ensure_ascii=False)
            self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
            self.wfile.flush()
        except Exception:
            pass


def main() -> None:
    server = ThreadingHTTPServer((HOST, PORT), AgentWebHandler)
    print(f"VideoMind test UI: http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
