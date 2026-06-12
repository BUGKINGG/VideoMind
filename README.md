# VideoMind 项目文档

AI 视频分析助手。用户提交 Bilibili/YouTube 视频链接后，系统自动下载字幕、生成总结，并支持基于视频内容的对话问答。

---

## 项目结构

```text
VideoMind/
├── backend/                              # Java + Spring Boot 后端（端口 8080）
│   ├── src/main/java/com/example/backend/
│   │   ├── common/
│   │   │   ├── JwtUtils.java             # JWT 生成/解析
│   │   │   ├── Result.java               # 统一响应封装
│   │   │   ├── BaseContext.java          # ThreadLocal 当前用户
│   │   │   ├── BilibiliUrlUtils.java     # Bilibili URL/分 P 解析
│   │   │   └── RedisLockUtil.java        # Redis 分布式锁
│   │   ├── config/
│   │   │   └── WebMvcConfigure.java      # CORS、拦截器注册
│   │   ├── controller/
│   │   │   ├── AgentController.java      # /agent/* 总结与对话接口
│   │   │   └── UserController.java       # /user/* 登录、注册、历史记录
│   │   ├── dto/
│   │   │   ├── ChatDTO.java              # 对话请求参数
│   │   │   ├── SummaryDTO.java           # 总结请求参数
│   │   │   ├── LoginDTO.java             # 登录请求参数
│   │   │   └── RegisterDTO.java          # 注册请求参数
│   │   ├── entity/
│   │   │   ├── User.java                 # 用户表
│   │   │   ├── Video.java                # 视频表
│   │   │   ├── Conversation.java         # 会话表
│   │   │   ├── Message.java              # 消息表
│   │   │   └── Subtitle.java             # 字幕表
│   │   ├── interceptor/
│   │   │   └── JwtTokenInterceptor.java  # Token 校验
│   │   ├── mapper/
│   │   │   ├── UserMapper.java
│   │   │   ├── VideoMapper.java
│   │   │   ├── ConversationMapper.java
│   │   │   ├── MessageMapper.java
│   │   │   └── SubtitleMapper.java       # 含批量插入字幕
│   │   ├── service/ + serviceImpl/
│   │   │   ├── AgentService.java         # 总结/对话服务接口
│   │   │   ├── AgentServiceImpl.java     # 核心异步+SSE实现
│   │   │   ├── UserService.java          # 用户服务接口
│   │   │   └── UserServiceImpl.java      # 用户CRUD实现
│   │   └── vo/
│   │       ├── ChatResult.java           # 对话响应
│   │       ├── SummaryResult.java        # 总结响应
│   │       ├── MessageVO.java            # 会话消息详情
│   │       └── LoginVO.java              # 登录响应
│   ├── src/main/resources/
│   │   ├── mapper/SubtitleMapper.xml     # 批量插入字幕 SQL
│   │   └── application.yml               # 数据源、JWT、Redis 配置
│   └── pom.xml                           # Maven 依赖
│
├── frontend/                             # Vue 3 + Vite 前端（端口 5173）
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue                  # 主页面：上传/总结/对话/设置
│   │   │   └── Login.vue                 # 登录/注册页面
│   │   ├── stores/
│   │   │   └── user.ts                   # Pinia 用户状态（token/cookie）
│   │   ├── utils/
│   │   │   └── request.ts                # Axios 封装（自动带 token）
│   │   ├── router/
│   │   │   └── index.ts                  # 路由 + 登录守卫
│   │   ├── App.vue                       # 根组件
│   │   └── main.ts                       # 入口
│   ├── .env                              # API 基地址
│   ├── vite.config.ts                    # 代理配置
│   └── package.json
│
└── new-agent-service/                    # Python AI Agent 服务（端口 8765）
    ├── web_server.py                     # HTTP 服务入口（/api/chat/stream、/api/process/stream）
    ├── fetch_video.py                    # Bilibili 视频解析服务（端口 8001）
    ├── app/
    │   ├── agent/
    │   │   ├── service.py                # SimpleAgentService 业务编排
    │   │   └── graph.py                  # LangGraph 意图路由图
    │   ├── services/
    │   │   ├── video_summarizer.py       # 视频总结生成
    │   │   ├── video_qa.py               # 视频问答生成
    │   │   └── intent_classifier.py      # 意图分类
    │   ├── llm/
    │   │   ├── client.py                 # LLM 调用客户端
    │   │   └── embedding.py              # Embedding 调用客户端
    │   ├── repositories/
    │   │   ├── video_repository.py       # video_store.db 操作
    │   │   ├── vector_store.py           # vector_store.db 操作
    │   │   └── conversation_repository.py # conversation_store.db 操作
    │   ├── transcripts/
    │   │   └── store.py                  # 字幕内存缓存与分块
    │   ├── models.py                     # 数据模型
    │   └── core/config.py                # 配置（LLM/Embedding/数据路径）
    ├── data/
    │   ├── video_store.db                # 视频、字幕、chunk 元数据
    │   ├── vector_store.db               # 向量检索库
    │   └── conversation_store.db         # 对话历史
    └── requirements.txt
```

---

## 优先级说明

| 优先级 | 业务 | 说明 |
|--------|------|------|
| **P0（核心）** | 视频总结 | 用户上传视频后生成 AI 总结，是产品主流程 |
| **P0（核心）** | 视频对话问答 | 基于视频内容进行流式对话 |
| **P1（支撑）** | 用户登录/注册/Cookie | 身份认证与 Bilibili Cookie 管理 |
| **P1（支撑）** | 会话历史 | 查询历史对话列表与详情 |

---

# P0 业务一：视频总结

## 整体时序

```text
用户粘贴 URL → 前端 POST /agent/summary → 后端立即返回 sessionId
                                     ↓
                              前端 GET /agent/summary/stream?sid=xxx
                                     ↓
                              后端异步调用 Python 处理并 SSE 推流
                                     ↓
                              前端接收 chunk/done，渲染总结内容
```

## 前端流程

**文件：** `frontend/src/views/Home.vue`

| 函数 | 主要行为 | 调用后端接口 |
|------|----------|--------------|
| `startSummary()` | 校验 URL 与 Cookie，进入加载状态 | `POST /agent/summary` |
| 同函数内 SSE 读取 | 用 `fetch + ReadableStream` 连接 SSE，逐段解析 `processSseChunk()` | `GET /agent/summary/stream?sid=` |
| `processSseChunk()` | 解析 SSE 事件：`connect` / `chunk` / `done` / `error` | - |
| `loadHistory()` | 刷新左侧历史列表 | `GET /user/conversation/list` |

## 后端流程

### 1. 提交总结任务

**接口：** `POST /agent/summary`

**链路：**
```
AgentController.summary(SummaryDTO)
  ↓
AgentServiceImpl.submitSummary(SummaryDTO)
```

**`submitSummary()` 关键步骤与 CRUD：**

| 步骤 | 操作 | 说明 |
|------|------|------|
| 限流 | `Redis SET videomind:limit:{userId}` | 10 秒内只能提交一次总结 |
| 缓存查询 | `videoMapper.selectOne(url=? AND part=? AND status=1)` | 命中则直接返回缓存，不走 SSE |
| 分布式锁 | `RedisLockUtil.tryLock(videomind:lock:video:{baseUrl}:{part})` | 防止并发处理同一视频 |
| 锁内二次缓存检查 | 同上 | 等锁期间可能已被别人完成 |
| 检查处理中记录 | `videoMapper.selectOne(url=? AND part=? AND status=0)` | 若正在处理，共享等待 |
| 新建视频记录 | `videoMapper.insert(Video)` | `status=0`（处理中），`user_id` 写入 |
| 绑定 SSE Session | `Redis SET videomind:sse:summary:{sid} -> videoId` | TTL 10 分钟 |
| 异步执行 | `CompletableFuture.runAsync(() -> doProcess(...))` | 后台处理 |
| 返回 | `SummaryResult(sessionId=sid, status=0, videoId=...)` | 前端凭 sid 连 SSE |

### 2. SSE 连接

**接口：** `GET /agent/summary/stream?sid=xxx`

**链路：**
```
AgentController.stream(sid)
  ↓
AgentServiceImpl.connectSse(sid)
```

**`connectSse()` 关键步骤：**

| 步骤 | 操作 |
|------|------|
| 校验 sid | `Redis GET videomind:sse:summary:{sid}` |
| 已完成 | 若 `video.status=1`，立即 `pushDone()` 并关闭连接 |
| 处理中 | 创建 `SseEmitter`（5 分钟超时），存入内存 `emitters` Map，发送 `connect` 事件 |

### 3. 后台处理核心

**链路：**
```
AgentServiceImpl.doProcess(videoId, baseUrl, part, userId, cookie, sid)
```

**`doProcess()` 关键步骤与 CRUD：**

| 步骤 | 操作 | 外部调用 / CRUD |
|------|------|-----------------|
| 解析视频 | `POST http://localhost:8001/parse` | 调用 `fetch_video.py`；返回标题、bvid、字幕列表 |
| 批量写入字幕 | `subtitleMapper.insertBatch(subList)` | 向 `subtitle` 表批量 INSERT |
| 构造 agentVideoId | `Redis SET videomind:video:agent_id:{videoId} -> {bvid}_p{part}` | 后续对话复用 |
| 流式总结 | `POST {agentServiceUrl}/api/process/stream` | 调用 Python Agent SSE |
| 读取 Python SSE | 逐行读取 `chunk`/`done`/`error` | 累计总结文本，并 `pushChunk()` 给前端 |
| 更新视频状态 | `videoMapper.updateById(Video)` | `status=1`，写入 `title`、`summary`、`subtitle_count` |
| 创建会话 | `conversationMapper.insert(Conversation)` | 生成 conversationId，绑定 videoId |
| 插入 AI 总结消息 | `messageMapper.insert(Message)` | `role='ai'`，`content=summary` |
| 推送完成 | `pushDone()` | SSE `type=done` 事件 |
| 异常处理 | `videoMapper.updateById(Video)` | `status=2`，`summary='处理失败: ...'`，`pushError()` |

### 4. SSE 推送辅助方法

| 方法 | 事件名 | 用途 |
|------|--------|------|
| `pushChunk(sid, content)` | `message` / `type=chunk` | 推送流式片段 |
| `pushDone(sid, ...)` | `message` / `type=done` | 推送最终结果 |
| `pushError(sid, message)` | `error` | 推送错误信息 |

## Python Agent 流程

**接口：** `POST /api/process/stream`

**文件：** `new-agent-service/web_server.py` → `_handle_process_stream()`

```text
接收 {video_id, title, transcript_text, segments, user_id}
  ↓
SimpleAgentService.add_video_transcript_with_segments()
  ├─ video_repository.save_transcript()        # INSERT/UPDATE videos + transcript_segments
  ├─ _build_chunks_from_segments()             # 按时间戳分块
  ├─ video_repository.save_chunks()            # DELETE/INSERT transcript_chunks
  ├─ index_video_chunks()
  │   ├─ embedding.embed_many()                # 调用 Embedding API
  │   └─ vector_store.upsert_chunks()          # DELETE 旧向量 + INSERT/UPDATE video_chunk_vectors
  └─ _ensure_video_loaded()                    # 载入内存缓存
  ↓
VideoSummarizer.summarize_stream()
  ├─ summarize_chunk() × N                     # 每个 chunk 同步调 LLM 生成小结
  └─ llm_client.generate_stream()              # 最终总结流式生成
  ↓
SSE 输出 chunk → 最终 done 事件
```

---

# P0 业务二：视频对话问答

## 整体时序

```text
用户在聊天页输入问题 → 前端 POST /agent/chat → 后端立即返回 sessionId
                                              ↓
                                       前端 GET /agent/chat/stream?sid=xxx
                                              ↓
                                       后端异步调用 Python 问答并 SSE 推流
                                              ↓
                                       前端接收 chunk/done，更新 AI 消息
```

## 前端流程

**文件：** `frontend/src/views/Home.vue`

| 函数 | 主要行为 | 调用后端接口 |
|------|----------|--------------|
| `sendMessage()` | 将用户消息和 "思考中..." 占位加入列表 | `POST /agent/chat` |
| 同函数内 SSE 读取 | `fetch + ReadableStream` 连接 SSE | `GET /agent/chat/stream?sid=` |
| `processChatChunk()` | 解析 `chunk` / `done` / `error`，用 `splice` 更新 AI 消息 | - |
| `loadHistory()` | 对话完成后刷新历史 | `GET /user/conversation/list` |

## 后端流程

### 1. 提交对话任务

**接口：** `POST /agent/chat`

**链路：**
```
AgentController.chat(ChatDTO)
  ↓
AgentServiceImpl.submitChat(ChatDTO)
```

**`submitChat()` 关键步骤与 CRUD：**

| 步骤 | 操作 | 说明 |
|------|------|------|
| 保存用户消息 | `messageMapper.insert(Message)` | `role='user'`，`content=message` |
| 生成 sessionId | `UUID.randomUUID()` | - |
| 绑定 SSE Session | `Redis SET videomind:sse:chat:{sid} -> {conversationId}:{userMessageId}` | TTL 10 分钟；userMessageId 用于精确识别本次请求的 AI 回复 |
| 异步执行 | `CompletableFuture.runAsync(() -> doChatProcess(...))` | - |
| 返回 | `ChatResult(sessionId=sid, status=0)` | - |

### 2. SSE 连接

**接口：** `GET /agent/chat/stream?sid=xxx`

**链路：**
```
AgentController.chatStream(sid)
  ↓
AgentServiceImpl.connectChatSse(sid)
```

**`connectChatSse()` 关键步骤：**

| 步骤 | 操作 |
|------|------|
| 解析 Redis | `GET videomind:sse:chat:{sid}`，解析出 `conversationId` 与 `userMessageId` |
| 完成检查 | `messageMapper.selectOne(conversationId=? AND role='ai' AND id > userMessageId ORDER BY id DESC LIMIT 1)` |
| 已生成 | 立即 `pushChatDone()` 并关闭连接 |
| 处理中 | 创建 `SseEmitter`（2 分钟超时），存入 `emitters` Map，发送 `connect` 事件 |

### 3. 后台处理核心

**链路：**
```
AgentServiceImpl.doChatProcess(sid, conversationId, userId, message)
```

**`doChatProcess()` 关键步骤与 CRUD：**

| 步骤 | 操作 | 外部调用 / CRUD |
|------|------|-----------------|
| 查询会话 | `conversationMapper.selectById(conversationId)` | 获取 `videoId` |
| 查询视频 | `videoMapper.selectById(videoId)` | 获取 URL 等信息 |
| 构造 agentVideoId | `Redis GET videomind:video:agent_id:{videoId}` | 未命中则从 URL 提取 bvid |
| 流式问答 | `POST {agentServiceUrl}/api/chat/stream` | 调用 Python Agent SSE |
| 读取 Python SSE | 逐行读取 `chunk`/`done`/`error` | 累计答案，并 `pushChunk()` 给前端 |
| 保存 AI 回复 | `messageMapper.insert(Message)` | `role='ai'`，`content=answer` |
| 更新会话时间 | `conversationMapper.updateById(Conversation)` | 更新 `updated_at` |
| 推送完成 | `pushChatDone()` | SSE `type=done` 事件 |

## Python Agent 流程

**接口：** `POST /api/chat/stream`

**文件：** `new-agent-service/web_server.py` → `_handle_chat_stream()`

```text
接收 {user_id, session_id, video_id, question}
  ↓
SimpleAgentService._ensure_video_loaded()           # SQLite → 内存缓存
  ↓
SimpleAgentService.find_relevant_video_chunks()
  ├─ embedding.embed(question)                      # 问题向量化
  └─ vector_store.search()                          # 余弦相似度检索相关片段
  ↓
SimpleAgentService._get_or_load_history()
  └─ conversation_repository.recent_turns()         # 查询最近 12 轮对话
  ↓
VideoQA.answer_stream()
  └─ llm_client.generate_stream()                   # 流式生成回答
  ↓
保存本轮对话
  ├─ conversation_repository.add_turn(user)         # INSERT user 消息
  └─ conversation_repository.add_turn(assistant)    # INSERT assistant 消息
  ↓
SSE 输出 chunk → 最终 done 事件（带 source chunks）
```

---

# P1 业务三：用户认证与管理

## 1. 登录

**接口：** `POST /user/login`

**链路：**
```
UserController.login(LoginDTO)
  ↓
UserServiceImpl.login(LoginDTO)
  ├─ userMapper.selectOne(phone = loginDTO.account)
  ├─ BCryptPasswordEncoder.matches(password, passwordHash)
  └─ 返回 User
  ↓
UserController 生成 JWT
  ├─ JwtUtils.generateToken(userId)
  └─ 返回 {token, username, cookie}
```

## 2. 注册

**接口：** `POST /user/register`

**链路：**
```
UserController.register(RegisterDTO)
  ↓
UserServiceImpl.register(RegisterDTO)
  ├─ this.count(phone = registerDTO.account)        # 查重
  └─ userMapper.insert(User)                        # BCrypt 加密密码后 INSERT
```

## 3. 更新 Cookie

**接口：** `POST /user/cookie`

**链路：**
```
UserController.updateCookie(CookieDTO)
  ↓
UserServiceImpl.updateCookie(String cookie)
  ├─ 从 BaseContext 取 userId
  └─ userMapper.update(null, LambdaUpdateWrapper)   # 更新 user.cookie
```

## 4. 查询会话历史列表

**接口：** `GET /user/conversation/list`

**链路：**
```
UserController.conversationList()
  ↓
UserServiceImpl.getList()
  └─ conversationMapper.selectList(
       userId = currentUser AND status = 1
       ORDER BY updated_at DESC
     )
```

## 5. 查询会话消息详情

**接口：** `GET /user/conversation/{id}`

**链路：**
```
UserController.showMessage(@PathVariable id)
  ↓
UserServiceImpl.getMessages(id)
  ├─ conversationMapper.selectById(id)
  ├─ messageMapper.selectList(
  │     conversationId = id
  │     ORDER BY created_at ASC
  │   )
  └─ 封装 MessageVO 返回
```

---

# 公共基础设施

## JWT 认证

| 组件 | 文件 | 职责 |
|------|------|------|
| 生成/解析 Token | `common/JwtUtils.java` | `generateToken(userId)` 2 小时有效期；`parseToken(token)` 提取 userId |
| 请求拦截 | `interceptor/JwtTokenInterceptor.java` | 除 `/user/login`、`/user/register`、OPTIONS 外，均校验 `token` Header；合法则将 userId 写入 `BaseContext.threadLocal` |
| 拦截器注册 | `config/WebMvcConfigure.java` | 注册 `JwtTokenInterceptor`，配置 CORS |

## Redis 用途

| Key 模式 | 值 | TTL | 用途 |
|----------|-----|-----|------|
| `videomind:limit:{userId}` | `1` | 10 秒 | 总结限流 |
| `videomind:lock:video:{baseUrl}:{part}` | lockValue | 30 秒 | 分布式锁，防止同一视频并发处理 |
| `videomind:sse:summary:{sid}` | `videoId` | 10 分钟 | 绑定总结 SSE 会话 |
| `videomind:sse:chat:{sid}` | `conversationId:userMessageId` | 10 分钟 | 绑定对话 SSE 会话，并精确识别本轮 AI 回复 |
| `videomind:video:agent_id:{videoId}` | `{bvid}_p{part}` | 无 | videoId 与 Python 侧 video_id 映射 |

## 数据库

### MySQL（后端主库）

| 表 | 主要字段 | 说明 |
|----|----------|------|
| `user` | id, username, phone, password_hash, cookie, created_at, updated_at | 用户 |
| `video` | id, url, user_id, title, status, part, summary, subtitle_count, created_at | 视频；status: 0 处理中 / 1 完成 / 2 失败 |
| `subtitle` | id, video_id, content, start_at, end_at | 字幕片段 |
| `conversation` | id, user_id, video_id, title, status, subtitle_count, created_at, updated_at | 会话 |
| `message` | id, conversation_id, role, content, created_at | 消息；role: `user` / `ai` |

### SQLite（Python Agent 本地）

| 数据库文件 | 表 | 说明 |
|------------|-----|------|
| `data/video_store.db` | `videos`、`transcript_segments`、`transcript_chunks` | 视频元数据、字幕、文本块 |
| `data/vector_store.db` | `video_chunk_vectors` | 文本块向量，支持余弦相似度检索 |
| `data/conversation_store.db` | `conversation_messages` | 对话历史，按 `(user_id, session_id, video_id)` 隔离 |

## SSE 机制

前后端均使用 **两步式 SSE**：
1. 前端先 POST 提交任务，后端立即返回 `sessionId`。
2. 前端再用 `fetch + ReadableStream` 连接 `GET /.../stream?sid=xxx`。
3. 后端异步任务通过内存中的 `emitters` Map 找到 `SseEmitter` 推送事件。
4. 若任务在 SSE 连接前已完成，后端直接查库补发 `done` 事件。

---

# 附录：Python 分块与向量检索

## 文本分块

- 带时间轴的分块：`[start_time]s 字幕文本`，按句子/字数切分后写入 `transcript_chunks`。
- 最终存储到 `video_chunk_vectors` 时附带 `start_time`、`end_time`，方便问答时引用时间戳。

## 向量检索

1. 对问题调用 Embedding API 得到向量。
2. 从 `video_chunk_vectors` 加载该视频全部候选块。
3. 计算问题向量与候选块向量的余弦相似度。
4. 返回 Top-N 相关块作为 LLM 上下文。
5. 未配置 Embedding API 时降级为基于哈希的向量（`HashEmbeddingClient`）。

---

# 已知注意点

1. `AgentServiceImpl.chat(ChatDTO)` 是旧的同步对话方法，调用 Python `/api/chat`，**当前控制器已不再使用**；生产流式对话走 `submitChat()` + `doChatProcess()`。
2. `AgentServiceImpl.doProcess()` 中 `http://localhost:8001/parse` 是硬编码地址，部署时需确保 `fetch_video.py` 服务可达。
3. 前端文件上传功能目前仅设置文件名，尚未实现实际上传。
4. 前端 `user.ts` 的 `hasCookie` computed 缺少 `return` 关键字。
