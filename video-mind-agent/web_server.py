from __future__ import annotations

import threading
import time
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
    """
    VideoMind 的 HTTP 请求处理器。

    提供以下端点：
    - GET  /api/health          健康检查
    - GET  /api/videos          列出已知视频
    - POST /api/chat/stream     视频问答 SSE 流式接口（带心跳保活）
    - POST /api/process/stream  视频处理 SSE 流式接口（字幕索引 + 流式总结）
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        """后台运行测试服务时不输出每次请求的访问日志"""
        return

    def do_GET(self) -> None:
        try:
            path = urlparse(self.path).path
            if path == "/api/health":
                try:
                    self._send_json({"status": "ok"})
                except:
                    self._send_json({"status": "error"}, status=HTTPStatus.SERVICE_UNAVAILABLE)
                    return

            elif path == "/api/videos":
                self._send_json({"videos": agent.video_repository.list_videos()})
                return
            else:
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
        """读取请求体中的 JSON 数据"""
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length <= 0:
            print(f"[WARN] Content-Length is 0 or missing, headers={dict(self.headers)}")
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        print(f"[DEBUG] Received body: {raw[:500]}")
        return json.loads(raw)

    def _required(self, body: dict, key: str) -> str:
        """从请求体中获取必要参数，缺失则抛出异常"""
        value = str(body.get(key, "")).strip()
        if not value:
            raise ValueError(f"{key} is required")
        return value

    def _send_json(self, data: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        """发送 JSON 响应"""
        payload = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


    def _handle_chat_stream(self, body: dict) -> None:
        """
        对话流式接口：边生成边推送 SSE 事件。

        流程：
        1. 加载多层记忆（短期、长期摘要、用户画像、相关历史记忆）
        2. 检索相关视频字幕块
        3. 流式生成回答（SSE 推送逐 token）
        4. 保存对话并触发记忆后处理

        SSE 事件格式：
        - data: {"type":"chunk","content":"..."}   增量 token
        - data: :ping                               心跳保活（每 5 秒）
        - data: {"type":"done","answer":"...",...}  完成信号
        - data: {"type":"error","message":"..."}    错误
        """
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

        # 用于停止 ping 线程的事件和线程安全的写锁
        stop_event = threading.Event()
        write_lock = threading.Lock()

        def ping_worker():
            """
            独立线程：每 5 秒发送 SSE 保活注释 `:ping`。
            防止反向代理/客户端因长时间无数据而断开连接。
            检测到连接断开（BrokenPipeError 等）时自动退出。
            """
            while not stop_event.is_set():
                try:
                    time.sleep(5)
                    if stop_event.is_set():
                        break
                    with write_lock:
                        self.wfile.write(b"data: :ping\n\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    # 连接已断开，退出线程
                    break
                except Exception:
                    # 其他异常，继续尝试
                    pass

        # 启动保活线程
        ping_thread = threading.Thread(target=ping_worker, daemon=True)
        ping_thread.start()

        try:
            # ===== 1. 加载多层记忆上下文 =====
            print(f"[DEBUG] /api/chat/stream received: user_id={user_id}, session_id={session_id}, video_id={video_id}, question={question[:30]}")
            resolved_owner = agent._ensure_video_loaded(video_id, user_id)
            print(f"[DEBUG] resolved_owner={resolved_owner}")

            transcript = agent.transcript_store.get_transcript(video_id, resolved_owner)

            # 检索相关视频字幕块（RAG）
            chunks = agent.find_relevant_video_chunks(
                user_id=user_id,
                video_id=video_id,
                question=question,
                transcript_owner_user_id=resolved_owner,
            )
            print(f"[DEBUG] retrieved {len(chunks)} chunks")

            # 短期记忆
            conversation_key = f"{user_id}:{session_id}:{video_id}"
            history = agent._get_or_load_history(
                conversation_key,
                user_id=user_id,
                session_id=session_id,
                video_id=video_id,
            )

            # 长期记忆摘要
            memory_summary = agent._get_or_load_memory_summary(
                conversation_key,
                user_id=user_id,
                session_id=session_id,
                video_id=video_id,
            )

            # 用户画像
            user_profile = agent._get_or_load_user_profile(user_id)

            # 相关历史对话记忆（向量检索 + Rerank）
            memories = agent.find_relevant_conversation_memories(
                user_id=user_id,
                video_id=video_id,
                question=question,
            )

            # 视频总结
            summary = agent.video_repository.load_summary(video_id, resolved_owner)

            # ===== 2. 流式生成 =====
            full_answer = []
            for token in agent.video_qa.answer_stream(
                transcript, question, chunks, history,
                summary=summary,
                memory_summary=memory_summary,
                user_profile=user_profile,
                relevant_memories=memories,
            ):
                full_answer.append(token)
                payload = json.dumps({
                    "type": "chunk",
                    "content": token,
                }, ensure_ascii=False)
                with write_lock:
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()

            # ===== 3. 保存对话并触发所有记忆后处理 =====
            answer = "".join(full_answer)
            agent.record_conversation_turns(
                user_id=user_id,
                session_id=session_id,
                history=history,
                user_content=question,
                assistant_content=answer,
                video_id=video_id,
            )

            # ===== 4. 推送 done 事件 =====
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
                "memories": [
                    {
                        "memory_id": memory.memory_id,
                        "session_id": memory.session_id,
                        "video_id": memory.video_id,
                        "content": memory.content,
                    }
                    for memory in memories
                ],
            }, ensure_ascii=False)
            with write_lock:
                self.wfile.write(f"data: {done_payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                self.close_connection = True

        except Exception as e:
            self._send_sse_error(str(e))
        finally:
            # 关键：无论成功还是异常，停止 ping 线程
            stop_event.set()
            ping_thread.join(timeout=2)

    def _handle_process_stream(self, body: dict) -> None:
        """
        视频处理流式接口：存字幕 → 向量索引 → 流式总结。

        SSE 事件格式：
        - data: {"type":"chunk","content":"..."}   增量 token
        - data: :ping                               心跳保活（每 5 秒）
        - data: {"type":"done","video_id":"...",...} 完成信号（含完整总结）
        - data: {"type":"error","message":"..."}    错误
        """
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

        # 用于停止 ping 线程的事件和线程安全的写锁
        stop_event = threading.Event()
        write_lock = threading.Lock()

        def ping_worker():
            """
            独立线程：每 5 秒发送 SSE 保活注释 `:ping`。
            防止反向代理/客户端因长时间无数据而断开连接。
            检测到连接断开（BrokenPipeError 等）时自动退出。
            """
            while not stop_event.is_set():
                try:
                    time.sleep(5)
                    if stop_event.is_set():
                        break
                    with write_lock:
                        self.wfile.write(b"data: :ping\n\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    break
                except Exception:
                    pass

        # 启动保活线程
        ping_thread = threading.Thread(target=ping_worker, daemon=True)
        ping_thread.start()

        try:
            # 1. 存字幕（支持带时间戳的 segments 和纯文本两种模式）
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
                with write_lock:
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()

            # 4. 保存总结，供后续问答使用
            summary = "".join(full_summary)
            agent.video_repository.save_summary(
                video_id=video_id, summary=summary, owner_user_id=user_id
            )
            # 同时写入对话历史，让 Agent 记得"刚才总结过什么"
            summary_session_id = str(body.get("session_id", video_id))
            user_turn = ChatTurn(role="user", content="请总结这个视频")
            assistant_turn = ChatTurn(role="assistant", content=summary)
            agent.conversation_repository.add_turn(
                user_id, summary_session_id, user_turn, video_id=video_id
            )
            agent.conversation_repository.add_turn(
                user_id, summary_session_id, assistant_turn, video_id=video_id
            )

            done_payload = json.dumps({
                "type": "done",
                "video_id": video_id,
                "title": title,
                "summary": summary,
            }, ensure_ascii=False)
            with write_lock:
                self.wfile.write(f"data: {done_payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                self.close_connection = True

        except Exception as e:
            self._send_sse_error(str(e))
        finally:
            # 关键：无论成功还是异常，停止 ping 线程
            stop_event.set()
            ping_thread.join(timeout=2)

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
