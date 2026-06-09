# VideoMind Agent Service

这是 VideoMind 项目的 Agent 原型服务，主要负责围绕视频字幕进行问答和总结。

当前它不是正式后端，而是一个可以独立运行的 Python Agent 服务。前端/后端后续可以通过 HTTP 接口调用它。

## 现在能做什么

- 读取视频字幕文本
- 将字幕切成 chunks
- 为 chunks 建立 embedding 向量索引
- 根据用户问题检索相关字幕片段
- 调用 LLM 基于字幕回答问题
- 对整个视频生成总结
- 保存用户在某个视频下的对话历史
- 用 LangGraph 编排 Agent 流程
- 提供一个本地网页测试页面

## 快速运行

在 PowerShell 中执行：

```powershell
cd "C:\Users\Spider Man\Desktop\lastyear\VideoMind\new-agent-service"
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe web_server.py
```

然后打开：

```text
http://127.0.0.1:8765
```

如果端口 `8765` 被占用，说明之前的测试服务还在运行。可以关闭旧终端，或者手动结束占用该端口的 Python 进程。

## 推荐阅读顺序

第一次看代码时，建议按这个顺序读：

1. `app/agent/service.py`
2. `app/agent/graph.py`
3. `app/services/intent_classifier.py`
4. `app/services/video_qa.py`
5. `app/services/video_summarizer.py`
6. `app/repositories/video_repository.py`
7. `app/repositories/vector_store.py`
8. `app/repositories/conversation_repository.py`
9. `app/llm/client.py`
10. `app/llm/embedding.py`

## 目录结构

```text
new-agent-service/
│
├── app/
│   ├── agent/
│   │   ├── service.py              Agent 对外入口
│   │   └── graph.py                LangGraph 编排流程
│   │
│   ├── services/
│   │   ├── intent_classifier.py    判断用户是问答还是总结
│   │   ├── video_qa.py             视频问答 prompt 和 LLM 调用
│   │   └── video_summarizer.py     视频总结逻辑
│   │
│   ├── repositories/
│   │   ├── video_repository.py     视频、字幕、chunks 持久化
│   │   ├── vector_store.py         本地向量库
│   │   └── conversation_repository.py  对话历史持久化
│   │
│   ├── llm/
│   │   ├── client.py               LLM 调用客户端
│   │   └── embedding.py            Embedding 客户端
│   │
│   ├── transcripts/
│   │   └── store.py                字幕内存缓存和切块
│   │
│   ├── core/
│   │   └── config.py               配置和项目路径
│   │
│   └── models.py                   公共数据结构
│
├── data/                           本地 SQLite 数据库
├── resources/transcripts/          开发用字幕样本
├── web/                            本地测试页面
├── web_server.py                   本地测试 HTTP 服务
└── README.md
```

## Agent 运行流程

用户在网页中输入问题后，会走下面的流程：

```text
用户输入
    |
    v
web_server.py
    |
    v
SimpleAgentService.run_agent()
    |
    v
LangGraph
    |
    v
load_context
加载视频、字幕 chunks、最近对话历史
    |
    v
classify_intent
判断是视频问答还是视频总结
    |
    +-------------------+
    |                   |
    v                   v
video_qa          video_summary
视频问答           视频总结
    |                   |
    +-------------------+
    |
    v
save_conversation
保存本轮用户问题和 Agent 回答
    |
    v
返回答案
```

目前只有两条主要路线：

- `video_qa`：大多数问题都会走这里
- `video_summary`：用户明显要求“总结、概括、摘要”时走这里

对话历史不会单独作为一个回答类型，而是作为 `video_qa` 的上下文一起传给 LLM。

## 视频问答的 RAG 流程

视频问答不是把完整字幕直接丢给模型，而是先检索相关字幕片段。

```text
【视频入库阶段】

字幕文本
    |
    v
切成 chunks
    |
    v
生成 embedding
    |
    v
保存到 vector_store.db


【用户提问阶段】

用户问题
    |
    v
问题生成 embedding
    |
    v
和 chunk 向量做相似度匹配
    |
    v
取最相关的几个 chunks
    |
    v
把 chunks + 最近对话 + 用户问题交给 LLM
    |
    v
生成回答
```

## 数据存在哪里

本地数据都保存在 `data/` 目录下。

```text
data/
│
├── video_store.db
│   ├── 视频 ID
│   ├── 视频标题
│   ├── 完整字幕
│   └── 字幕 chunks
│
├── vector_store.db
│   ├── chunk_id
│   ├── chunk 文本
│   └── chunk embedding 向量
│
└── conversation_store.db
    ├── user_id
    ├── session_id
    ├── video_id
    ├── 用户问题
    └── Agent 回答
```

运行时还会有一层内存缓存：

```text
内存
├── 当前已加载的视频字幕
├── 当前已加载的 chunks
└── 当前会话的最近聊天历史
```

数据库负责长期保存，内存负责当前运行时快速使用。

## 配置 LLM

`.env` 用来保存本地私密配置，不要提交到 Git。

当前 LLM 配置项：

```env
ANTHROPIC_AUTH_TOKEN=
ANTHROPIC_BASE_URL=
ANTHROPIC_MODEL=
```

如果没有配置完整，LLM 客户端会返回提示信息，而不是正常调用模型。

## 配置 Embedding

如果配置了下面三个值，系统会调用 OpenAI-compatible embedding API：

```env
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=
```

如果没有配置完整，系统会使用本地 `HashEmbeddingClient`。

`HashEmbeddingClient` 只适合开发测试。正式效果要换成真正的语义 embedding 模型，例如阿里云百炼 `text-embedding-v4`。

## 重要概念

**Transcript**

完整视频字幕。

**Chunk**

字幕切出来的小块。RAG 检索时不会检索整篇字幕，而是检索 chunks。

**Embedding**

文本向量。问题和字幕 chunks 都会变成向量，然后通过相似度找到相关片段。

**Vector Store**

当前用 SQLite 实现的本地向量存储，文件是 `data/vector_store.db`。

**Conversation History**

用户围绕某个视频的问答记录，保存在 `data/conversation_store.db`。

**LangGraph**

用于组织 Agent 流程。当前图在 `app/agent/graph.py` 中。

## 当前代码边界

当前项目还不是最终形态。

现在已经完成：

- 字幕持久化
- 字幕切块
- 向量检索
- 视频问答
- 视频总结
- 对话历史保存
- LangGraph 编排
- 本地测试网页

后续可以继续做：

- 接入正式前后端登录用户
- 增加长期视频学习记忆
- 增加复习题、知识点卡片、时间戳定位
- 将 SQLite 替换为正式数据库或向量数据库
- 将 `web_server.py` 替换为 FastAPI 或由 Spring Boot 统一转发
