# VideoMind 项目文档

AI 视频分析助手。用户提交 Bilibili/YouTube 视频链接后，系统自动下载字幕、生成总结，并支持基于视频内容的对话问答。

---

## 项目结构

```text
VideoMind/
├── video-mind-java/                        # Java + Spring Boot 后端（端口 8080）
│   ├── src/main/java/com/example/backend/
│   │   ├── common/
│   │   │   ├── JwtUtils.java               # JWT 生成/解析
│   │   │   ├── Result.java                 # 统一响应封装
│   │   │   ├── BaseContext.java            # ThreadLocal 当前用户
│   │   │   ├── BilibiliUrlUtils.java       # Bilibili URL/分P 解析
│   │   │   └── RedisLockUtil.java          # Redis 分布式锁
│   │   ├── config/
│   │   │   └── WebMvcConfigure.java        # CORS、拦截器注册
│   │   ├── controller/
│   │   │   ├── AgentController.java        # /agent/* 总结与对话接口
│   │   │   ├── SseInternalController.java  # 实例间 SSE 事件转发
│   │   │   └── UserController.java         # /user/* 登录、注册、历史记录
│   │   ├── dto/
│   │   │   ├── ChatDTO.java                # 对话请求参数
│   │   │   ├── SummaryDTO.java             # 总结请求参数
│   │   │   ├── LoginDTO.java               # 登录请求参数
│   │   │   └── RegisterDTO.java            # 注册请求参数
│   │   ├── entity/
│   │   │   ├── User.java                   # 用户表
│   │   │   ├── Video.java                  # 视频表
│   │   │   ├── Conversation.java           # 会话表
│   │   │   ├── Message.java                # 消息表
│   │   │   ├── Subtitle.java               # 字幕表
│   │   │   ├── ParseTask.java              # RabbitMQ 解析任务
│   │   │   └── ChatTask.java               # RabbitMQ 对话任务
│   │   ├── interceptor/
│   │   │   └── JwtTokenInterceptor.java    # Token 校验
│   │   ├── mapper/
│   │   │   ├── UserMapper.java
│   │   │   ├── VideoMapper.java
│   │   │   ├── ConversationMapper.java
│   │   │   ├── MessageMapper.java
│   │   │   └── SubtitleMapper.java         # 含批量插入字幕
│   │   ├── service/ + serviceImpl/
│   │   │   ├── AgentService.java           # 总结/对话服务接口
│   │   │   ├── AgentServiceImpl.java       # 核心：RabbitMQ 消费 + SSE 推送 + 多实例路由
│   │   │   ├── AgentHealthChecker.java     # Agent 心跳健康检查
│   │   │   ├── UserService.java            # 用户服务接口
│   │   │   └── UserServiceImpl.java        # 用户 CRUD 实现
│   │   └── vo/
│   │       ├── ChatResult.java             # 对话响应
│   │       ├── SummaryResult.java          # 总结响应
│   │       ├── MessageVO.java              # 会话消息详情
│   │       └── LoginVO.java                # 登录响应
│   ├── src/main/resources/
│   │   ├── mapper/SubtitleMapper.xml       # 批量插入字幕 SQL
│   │   └── application.yml                 # 数据源、JWT、Redis、RabbitMQ 配置
│   └── pom.xml                             # Maven 依赖
│
├── video-mind-web/                          # Vue 3 + Vite 前端（端口 5173）
│   ├── src/
│   │   ├── views/
│   │   │   ├── Home.vue                    # 主页面：上传/总结/对话/设置，含 SSE 重连逻辑
│   │   │   └── Login.vue                   # 登录/注册页面
│   │   ├── composables/
│   │   │   ├── useSummary.ts               # 总结 SSE 流程 + 指数退避重连
│   │   │   ├── useChat.ts                  # 对话 SSE 流程 + 重连
│   │   │   ├── useHistory.ts               # 历史记录 + LRU 缓存
│   │   │   ├── useAuth.ts                  # 登录/注册逻辑
│   │   │   ├── usePlaceholder.ts           # 占位符动画
│   │   │   └── sseSession.ts               # SSE 会话 sessionStorage 持久化
│   │   ├── stores/
│   │   │   └── user.ts                     # Pinia 用户状态（token/cookie）
│   │   ├── utils/
│   │   │   ├── request.ts                  # Axios 封装（自动带 token）
│   │   │   ├── markdown.ts                 # Markdown 渲染
│   │   │   └── sseParser.ts               # SSE 事件解析
│   │   ├── router/
│   │   │   └── index.ts                    # 路由 + 登录守卫
│   │   ├── types/
│   │   │   └── message.ts                  # 消息类型定义
│   │   ├── App.vue                         # 根组件
│   │   └── main.ts                         # 入口
│   ├── .env                                # API 基地址
│   ├── vite.config.ts                      # 代理配置
│   └── package.json
│
└── video-mind-agent/                        # Python AI Agent 服务（端口 8765）
    ├── web_server.py                       # HTTP 服务入口（/api/chat/stream、/api/process/stream）
    ├── fetch_video.py                      # Bilibili 视频解析服务（端口 8001）
    ├── app/
    │   ├── agent/
    │   │   ├── service.py                  # SimpleAgentService 业务编排
    │   │   └── graph.py                    # LangGraph 意图路由图
    │   ├── services/
    │   │   ├── video_summarizer.py         # 视频总结生成
    │   │   ├── video_qa.py                 # 视频问答生成
    │   │   ├── intent_classifier.py        # 意图分类
    │   │   └── reranker.py                 # 本地轻量重排序器
    │   ├── llm/
    │   │   ├── client.py                   # LLM 调用客户端
    │   │   └── embedding.py                # Embedding 调用客户端
    │   ├── repositories/
    │   │   ├── video_repository.py         # video_store.db 操作
    │   │   ├── vector_store.py             # Qdrant 向量检索
    │   │   └── conversation_repository.py  # conversation_store.db 操作
    │   ├── transcripts/
    │   │   └── store.py                    # 字幕内存缓存与分块
    │   ├── models.py                       # 数据模型
    │   └── core/config.py                  # 配置（LLM/Embedding/数据路径）
    ├── data/
    │   ├── video_store.db                  # 视频、字幕、chunk 元数据
    │   ├── vector_store.db                 # 向量检索库（可切换 Qdrant）
    │   └── conversation_store.db           # 对话历史
    └── requirements.txt
```

## How to use

1. 把项目 clone 下来：
```shell
git clone https://github.com/BUGKINGG/VideoMind
```

2. 在 IDEA 中以 Maven 项目打开，compile 安装依赖。

3. 前端启动（`video-mind-web` 目录）：
```shell
npm install
npm run dev
```

4. 配置后端环境变量，在 `video-mind-java/src/main/resources/application.yml` 中配置 MySQL、Redis、RabbitMQ 连接信息。

5. 配置 AI API，在 `video-mind-agent` 目录下新建 `.env` 文件：
```text
ANTHROPIC_AUTH_TOKEN=sk-xxx
ANTHROPIC_BASE_URL=https://api.deepseek.com
ANTHROPIC_MODEL=deepseek-v4-flash
```

6. Docker Compose 一键部署（推荐）：
```shell
# 开发环境
docker compose up -d

# 生产环境
docker compose -f docker-compose-prod.yml up -d
```

7. 若不用 Docker，需手动启动：
   - `Application.java` — Java 后端
   - `fetch_video.py` — 视频解析服务
   - `web_server.py` — Agent 后端
   - `init.sql` — MySQL 建表

---

## 架构总览

### 整体拓扑

```text
浏览器 ──HTTP──▶ Nginx ──▶ video-mind-java (Spring Boot, 可多实例)
                              │
           ┌──────────────────┼──────────────────┐
           ▼                  ▼                  ▼
       MySQL              Redis             RabbitMQ
     (业务数据)      (缓存/锁/SSE路由)    (异步任务队列)
                                              │
                           ┌──────────────────┘
                           ▼
                     video-mind-agent (Python)
                           │
                    ┌──────┴──────┐
                    ▼              ▼
                LLM API      Qdrant (向量库)
```

### 核心设计决策：为什么用 RabbitMQ 替代 CompletableFuture？

| 对比维度 | 旧方案（CompletableFuture） | 新方案（RabbitMQ） |
|----------|---------------------------|-------------------|
| 任务持久化 | ❌ JVM 崩溃任务丢失 | ✅ 消息持久化到磁盘 |
| 负载均衡 | ❌ 单实例处理 | ✅ 多实例竞争消费 |
| 幂等性 | ❌ 无保证 | ✅ 消费者查库跳过已完成/失败任务 |
| 优雅关闭 | ❌ Future 可能被中断 | ✅ Manual ACK，处理完再确认 |
| 故障恢复 | ❌ 丢失后不可恢复 | ✅ Nack 后可重新入队 |

**解决的问题：**
- 用户提交总结后若 JVM 崩溃（OOM、kill -9），任务永久丢失 → RabbitMQ 消息持久化保证不丢
- 高并发时所有任务堆积在同一个 JVM 的 ForkJoinPool 中 → 多实例竞争消费，水平扩展
- 服务重启时正在处理的任务被强制中断 → Manual ACK 确保处理完成才确认

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

## 整体时序（RabbitMQ 异步架构）

```text
用户粘贴 URL → 前端 POST /agent/summary → 后端 submitSummary()
                                              │
                                    ┌─────────┴──────────┐
                                    │ 缓存命中？直接返回    │
                                    │ 缓存未命中：          │
                                    │ 1. Redis 分布式锁     │
                                    │ 2. INSERT video(0)   │
                                    │ 3. 生成 sid          │
                                    │ 4. 发送 RabbitMQ ──┐ │
                                    │ 5. 返回 sid         │ │
                                    └────────────────────┘ │
                                              │            │
                              前端 GET /agent/summary/stream?sid=xxx
                                              │            │
                                    connectSse() 建立长连接  │
                                              │            │
                                              ▼            ▼
                                    ┌──── RabbitMQ Consumer ────┐
                                    │  onParseTask() → doProcess()│
                                    │  ├─ 调用 Python 解析字幕    │
                                    │  ├─ 批量入库 subtitle       │
                                    │  ├─ 推送 metadata 事件      │
                                    │  ├─ 调用 Agent SSE 流式总结 │
                                    │  ├─ 逐 chunk 推送前端       │
                                    │  ├─ 更新 video status=1    │
                                    │  ├─ 创建 conversation       │
                                    │  └─ 推送 done 事件         │
                                    └────────────────────────────┘
```

## 后端流程

### 1. 提交总结任务

**接口：** `POST /agent/summary`

**链路：**
```
AgentController.summary(SummaryDTO)
  ↓
AgentServiceImpl.submitSummary(SummaryDTO)
```

**`submitSummary()` 关键步骤：**

| 步骤 | 操作 | 说明 |
|------|------|------|
| 限流 | `Redis SET videomind:limit:{userId}` | 10 秒内只能提交一次 |
| Redis 缓存查询 | `GET videomind:video:cache:{baseUrl}:{part}` | 命中直接返回 summary（24h TTL） |
| 数据库缓存查询 | `videoMapper.selectOne(url=? AND part=? AND status=1)` | Redis 未命中则查库 |
| 分布式锁 + 看门狗 | `RedisLockUtil.tryLock()` + `startWatchdog()` | 防并发处理同一视频；看门狗线程自动续期 |
| 双重检查 | 同上 | 等锁期间可能已被别人完成 |
| 检查处理中记录 | `videoMapper.selectOne(url=? AND part=? AND status=0)` | 若正在处理，共享等待（添加到 waiting set） |
| 新建视频记录 | `videoMapper.insert(Video)` | `status=0`（处理中） |
| 绑定 SSE Session | `Redis SET videomind:sse:summary:{sid} -> videoId` | TTL 10 分钟 |
| **发送 RabbitMQ** | `rabbitTemplate.convertAndSend("videomind.parse.exchange", "parse", task)` | **关键变更：将耗时逻辑异步化到消息队列** |
| 返回 | `SummaryResult(sessionId=sid, status=0)` | 前端凭 sid 连 SSE |

### 2. RabbitMQ 消费（替代旧 CompletableFuture）

**队列：** `videomind.parse.queue`

**消费者：** `AgentServiceImpl.onParseTask()`

```text
RabbitMQ 投递 ParseTask
  ↓
onParseTask(ParseTask, Message, Channel)
  ├─ 幂等检查：video.status==1 → ACK 丢弃
  ├─ 失败检查：video.status==2 → ACK 丢弃
  ├─ 执行 doProcess(...)
  └─ 结果判断：
      ├─ status==1 → basicAck（确认消费）
      ├─ status==2 → basicAck（失败也确认，不无限重试）
      └─ status==0 → basicNack（重新入队）
```

**为什么把 doProcess 交给 RabbitMQ 而不是 CompletableFuture：**
1. **持久化**：消息写入磁盘，JVM 崩溃不丢任务
2. **手动确认**：只有处理成功才 ACK，失败可 Nack 重试
3. **水平扩展**：多实例竞争消费，自动负载均衡
4. **解耦**：Controller 线程立即返回，不占用 Tomcat 线程池

### 3. SSE 连接

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
| 墓碑检查 | `Redis GET videomind:sse:dead:{sid}` — 若实例已死，返回错误让前端重新提交 |
| 校验 sid | `Redis GET videomind:sse:summary:{sid}` |
| 已完成 (status=1) | 立即 `pushDone()` 并关闭连接 |
| 失败 (status=2) | 返回错误（cookie 过期 / 无字幕） |
| 处理中 (status=0) | 清理旧 emitter（重连场景），创建新 `SseEmitter`（5 分钟超时），版本号防竞态 |
| 注册 owner | `Redis SET videomind:sse:owner:{sid} -> instanceId`，多实例路由依据 |
| 发送 connect | `type=connect` 事件通知前端连接成功 |

### 4. 后台处理核心

**链路：**
```
RabbitMQ Consumer → onParseTask() → doProcess(videoId, baseUrl, part, userId, cookie, sid)
```

**`doProcess()` 关键步骤（与原版差异）：**

| 步骤 | 操作 | 外部调用 / CRUD |
|------|------|-----------------|
| 健康检查 | `healthChecker.isHealthy()` | 若 Agent 不可用，直接标记失败 |
| 预加载等待队列 | `Redis SMEMBERS videomind:waiting:{videoId}` | 让所有等待用户也收到 chunk |
| 解析视频 | `POST {parserServiceUrl}/parse` | 调用 `fetch_video.py` |
| 批量写入字幕 | `subtitleMapper.insertBatch(subList)` | |
| **提前创建 Conversation** | `conversationMapper.insert(status=0)` | 前端历史记录立即可见（处理中状态） |
| **推送 metadata** | `pushMetadata()` → SSE `type=metadata` | 前端提前显示标题、字幕数、BV 号 |
| 构造 agentVideoId | `Redis SET videomind:video:agent_id:{videoId}` | |
| 流式总结 | `agentWebClient.post(/api/process/stream)` | WebClient 非阻塞调用 Python |
| 注册断线续传缓冲区 | `registerContentBuffer(sid, summaryBuilder)` | **新增：支持断线重连 catchup** |
| 读取 Python SSE | 逐行 parse，保活检测（30s 超时） | `:ping` 心跳 + 25s 业务假死检测 |
| 逐 chunk 推送 | `pushChunk(sid, token)` | 同时推送给 waiting set |
| 更新视频状态 | `videoMapper.updateById` status=1 | |
| 更新 Conversation | status=1, updated_at | |
| 插入 AI 总结消息 | `messageMapper.insert(role='ai')` | |
| 推送完成 | `pushDone()` | 同时推送给 waiting set，清理 Redis |
| **写入 Redis 缓存** | `SET videomind:video:cache:{url}:{part}` | 24h TTL，下次请求直接命中 |
| 异常处理 | status=2，pushError() | 同时更新提前创建的 Conversation 为失败 |

### 5. SSE 推送方法（多实例感知）

所有 push 方法（`pushChunk` / `pushMetadata` / `pushDone` / `pushError`）现在遵循**三层路由**：

```
pushXxx(sid, ...)
  ├─ 1. 本地 emitter 存在？
  │     ├─ 是 → 检查 pendingCatchup → 补发 catchup → 推送事件
  │     └─ 否 → 进入 Redis 路由
  ├─ 2. Redis 查 sid 所属实例
  │     ├─ 墓碑 key 存在 → 丢弃
  │     ├─ owner 不存在 → 标记 pendingCatchup（等待前端重连）
  │     └─ owner 存在 → 下一步
  ├─ 3. 目标实例存活检查
  │     └─ 心跳缺失 → 写墓碑，丢弃
  └─ 4. HTTP POST 转发到目标实例 /internal/sse/push
        └─ SseInternalController.push() → 本地 emitter.send()
```

**解决的问题：**
- 前端可能连实例 A，但 RabbitMQ Consumer 在实例 B 上运行
- 通过 Redis 记录 sid→instance 映射，Consumer 将 chunk 转发到正确实例
- 实例死亡时前端收到明确错误提示，而非无限等待

---

# P0 业务二：视频对话问答

## 整体时序（同 RabbitMQ 异步）

```text
用户输入问题 → 前端 POST /agent/chat → 后端 submitChat()
                                          │
                                   ┌──────┴───────┐
                                   │ INSERT 用户消息 │
                                   │ 生成 sid       │
                                   │ 设置 pending 标记│
                                   │ 发送 RabbitMQ ─┐│
                                   │ 返回 sid       ││
                                   └───────────────┘│
                                          │          │
                          前端 GET /agent/chat/stream?sid=xxx
                                          │          │
                                connectChatSse()     │
                                          │          │
                                          ▼          ▼
                                ┌── RabbitMQ Consumer ──┐
                                │ onChatTask()          │
                                │  → doChatProcess()    │
                                │   ├─ 查询 video/conv  │
                                │   ├─ 调用 Agent SSE   │
                                │   ├─ pushChunk 逐 token│
                                │   ├─ INSERT AI 回复   │
                                │   └─ pushChatDone()   │
                                └───────────────────────┘
```

## 后端流程

### 1. 提交对话任务

**接口：** `POST /agent/chat`

**`submitChat()` 关键步骤：**

| 步骤 | 操作 | 说明 |
|------|------|------|
| 保存用户消息 | `messageMapper.insert(role='user')` | |
| 生成 sessionId | `UUID.randomUUID()` | |
| 绑定 SSE Session | `Redis SET videomind:sse:chat:{sid} -> {conversationId}:{userMessageId}` | 精确识别本轮 AI 回复 |
| **标记进行中** | `Redis SET videomind:sse:chat_pending:{conversationId} -> sid` | **新增：前端切换回来时据此重连** |
| 发送 RabbitMQ | `rabbitTemplate.convertAndSend("videomind.chat.exchange", "chat", task)` | |
| 返回 | `ChatResult(sessionId=sid, status=0)` | |

### 2. SSE 连接

**接口：** `GET /agent/chat/stream?sid=xxx`

**`connectChatSse()` 关键步骤：**

| 步骤 | 操作 |
|------|------|
| 墓碑检查 | 同总结 |
| 双重检查 | 查 message 表，AI 回复可能已生成（userMessageId 精确定位） |
| 已生成 | 立即 `pushChatDone()` 关闭连接 |
| 处理中 | 清理旧 emitter（重连场景），创建 `SseEmitter`（2 分钟超时），版本号防竞态 |

### 3. 后台处理核心

**链路：**
```
RabbitMQ Consumer → onChatTask() → doChatProcess(sid, conversationId, userId, message)
```

**`doChatProcess()` 关键步骤：**

| 步骤 | 操作 | 说明 |
|------|------|------|
| 查询会话/视频 | `conversationMapper` / `videoMapper` | |
| 构造 agentVideoId | `Redis GET videomind:video:agent_id:{videoId}` | 未命中则从 URL 提取 bvid |
| 流式问答 | `agentWebClient.post(/api/chat/stream)` | 含保活检测 + 假死检测 |
| 注册缓冲区 | `registerContentBuffer(sid, answerBuilder)` | **新增：支持断线重连** |
| 逐 chunk 推送 | `pushChunk(sid, token)` | |
| 保存 AI 回复 | `messageMapper.insert(role='ai')` | |
| 更新会话时间 | `conversationMapper.updateById(updated_at)` | |
| 推送完成 | `pushChatDone()` | 清理 pending 标记 |

---

# SSE 断线重连机制（核心新增）

## 问题场景

1. **页面刷新**：用户在等待总结/对话时刷新了浏览器
2. **切换历史记录**：用户切换到另一个历史对话再切回来
3. **网络波动**：SSE 连接意外断开
4. **多实例部署**：前端连实例 A，后台处理在实例 B

## 后端机制

### 断线续传（Catchup）

```
doProcess/doChatProcess 启动
  └─ registerContentBuffer(sid, StringBuilder)  ← 注册共享缓冲区
       │
       ▼ 每个 chunk 到来
   summaryBuilder.append(token)                  ← 写入缓冲区
   pushChunk(sid, token)                         ← 尝试推送给前端
       │
       ├─ emitter 在线 → 正常推送
       └─ emitter 离线 → pendingCatchup.add(sid) ← 标记需补发
            │
            ▼ 前端重连后
       connectSse(sid) 创建新 emitter
            │
            ▼ 下一个 chunk 到来
       pushChunk(sid, token)
         → 检测到 pendingCatchup 标记
         → sendCatchupAndClean(emitter, sid)     ← 先推送 catchup 事件（全部累积内容）
         → 然后正常推送当前 chunk
```

### 关键数据结构

| 数据结构 | 类型 | 作用 |
|----------|------|------|
| `contentBuffers` | `Map<sid, StringBuilder>` | 与 doProcess/doChatProcess 共享，累积所有已生成的文本 |
| `pendingCatchup` | `Set<sid>` | emitter 离线标记，下次推送时触发 catchup |
| `catchupMetas` | `Map<sid, JSON>` | 缓存元数据（标题、字幕数、conversationId），重连时一并补发 |
| `emitterVersions` | `Map<sid, Long>` | 版本号，防止旧 emitter 的异步回调误删新 emitter |

### 多实例路由

```
实例 A (持有 emitter)           Redis                实例 B (执行 doProcess)
     │                           │                         │
     ├─ connectSse(sid)          │                         │
     ├─ registerSseOwner(sid) ──▶│ SET owner:{sid}=A       │
     │                           │                         │
     │                           │                         ├─ pushChunk(sid, token)
     │                           │                         │   emitter.get(sid) → null!
     │                           │  GET owner:{sid} ◀──────┤
     │                           │  return "A" ───────────▶│
     │                           │                         │
     │◀── HTTP POST /internal/sse/push ────────────────────┤
     │    emitter.send(chunk)     │                         │
```

### 实例发现与死亡检测

| 机制 | 实现 | 说明 |
|------|------|------|
| 心跳注册 | `@Scheduled(fixedRate=10s)` → `SET videomind:instance:alive:{id}` (TTL 30s) | 每 10s 刷新 |
| 地址注册 | `SET videomind:instance:address:{id} = host:port` (TTL 30s) | 供其他实例 HTTP 调用 |
| 存活判断 | `isInstanceAlive()` 检查心跳时间差 < 25s | |
| 墓碑标记 | `SET videomind:sse:dead:{sid}` (TTL 30s) | 实例死亡后，前端重连时收到明确错误 |
| 优雅下线 | `@PreDestroy` → 删除 alive/address/owner 映射 | |

## 前端机制

### sessionStorage 持久化

**文件：** `video-mind-web/src/composables/sseSession.ts`

```text
提交总结/对话 → saveSseState({ sid, type, conversationId })
                              │
                              ▼
                   sessionStorage['vm-sse-state']
                              │
              页面刷新 / 重新打开标签页
                              │
                              ▼
         onMounted() → loadSseState() → 根据 type 调用重连
             ├─ type='summary' → summary.reconnect(sid, token)
             └─ type='chat'    → chat.reconnect(sid, token, aiIndex)
```

### 重连流程（Home.vue `onMounted`）

```text
页面加载
  ↓
loadSseState() → 有未完成会话？
  ↓ 是
根据 type 恢复：
  ├─ summary 重连：
  │   1. 设置 isLoading=true, confirmText='重连中...'
  │   2. 创建占位符消息
  │   3. runSSE(sid, token) → fetch /agent/summary/stream
  │   4. 后端 connectSse() 发现 video 还在处理中 → 建立新 emitter
  │   5. 下一个 chunk → 检测 pendingCatchup → 推送 catchup（全部已有内容）
  │   6. 收到 catchup → 替换占位符为累积内容，继续流式
  │
  └─ chat 重连：
      1. 先 loadDetail(conversationId) 恢复历史消息
      2. 创建 AI 占位符
      3. runSSE(sid, token) → 同上 catchup 流程
      4. 收到 chunk → 更新占位符
      5. 收到 done → 完成
```

### 切换历史记录重连

```text
用户点击历史列表中的"处理中"对话
  ↓
handleSelectHistory(id)
  ├─ abort() 旧 SSE 连接（AbortController）
  ├─ clearSseState()
  ├─ loadDetail(id) → 返回 data.status=0, data.sid=xxx
  ├─ summary.reconnect(data.sid, token)
  └─ 后端 cleanSid() 已标记 pendingCatchup
       → 新 emitter 建立后
       → 下一个 chunk 触发 catchup 补发
```

### 指数退避自动重连

前端 SSE 读取封装了 3 次自动重连（`useSummary.ts` / `useChat.ts`）：

```typescript
const MAX_RETRIES = 3
const delays = [1000, 2000, 4000]  // 指数退避

// SSE 流异常终止且未收到 done/error → 自动重试
// AbortError（用户主动切换）→ 静默处理，不重试
```

### 对话进行中标记（pendingChatSid）

**后端：** `GET /user/conversation/{id}` 返回时附加检查：

```
Redis EXISTS videomind:sse:chat_pending:{conversationId}
  → 若有 → response.pendingChatSid = sid
  → 前端据此创建占位符并重连 SSE
```

---

# P1 业务三：用户认证与管理

（与原版一致，略）

---

# 公共基础设施

## JWT 认证

| 组件 | 文件 | 职责 |
|------|------|------|
| 生成/解析 Token | `common/JwtUtils.java` | `generateToken(userId)` 2 小时有效期 |
| 请求拦截 | `interceptor/JwtTokenInterceptor.java` | 除 `/user/login`、`/user/register`、OPTIONS 外均校验 |
| 拦截器注册 | `config/WebMvcConfigure.java` | 注册拦截器，配置 CORS |

## Redis 用途（完整）

| Key 模式 | 值 | TTL | 用途 |
|----------|-----|-----|------|
| `videomind:limit:{userId}` | `1` | 10s | 总结限流 |
| `videomind:lock:video:{baseUrl}:{part}` | lockValue | 30s + 看门狗续期 | 分布式锁 |
| `videomind:video:cache:{baseUrl}:{part}` | Video JSON | 24h | 总结结果缓存 |
| `videomind:sse:summary:{sid}` | `videoId` | 10min | 绑定总结 SSE 会话 |
| `videomind:sse:chat:{sid}` | `conversationId:userMessageId` | 10min | 绑定对话 SSE 会话 |
| `videomind:sse:chat_pending:{convId}` | `sid` | 10min | 标记对话进行中，前端据此重连 |
| `videomind:sse:conv:{convId}` | `sid` | 10min | conversationId→sid 映射 |
| `videomind:sse:owner:{sid}` | `instanceId` | 10min | sid 所属实例，跨实例路由 |
| `videomind:sse:dead:{sid}` | `HEARTBEAT_LOST/CALLBACK_FAILED` | 30s | 墓碑标记 |
| `videomind:instance:alive:{id}` | `timestamp` | 30s | 实例心跳 |
| `videomind:instance:address:{id}` | `host:port` | 30s | 实例地址 |
| `videomind:video:agent_id:{videoId}` | `{bvid}_p{part}` | 无 | videoId 与 Python 侧 video_id 映射 |
| `videomind:waiting:{videoId}` | `Set<sid>` | — | 等待同一视频的其他用户 |

## RabbitMQ 架构

| 组件 | 名称 | 说明 |
|------|------|------|
| Parse Exchange | `videomind.parse.exchange` | 解析任务交换机 |
| Parse Queue | `videomind.parse.queue` | 解析任务队列 |
| Chat Exchange | `videomind.chat.exchange` | 对话任务交换机 |
| Chat Queue | `videomind.chat.queue` | 对话任务队列 |
| 消息实体 | `ParseTask` / `ChatTask` | 序列化为 JSON 投递 |
| 确认模式 | Manual ACK | 处理成功才确认，失败可 Nack |

## SSE 实例间通信

**文件：** `SseInternalController.java`

| 接口 | 方法 | 用途 |
|------|------|------|
| `/internal/sse/push` | POST | 接收其他实例转发的 SSE 事件 |

支持的事件类型：`chunk`、`catchup`、`metadata`、`done`、`chat_done`、`error`

使用 `@Async` + `CompletableFuture` 在虚拟线程上执行，不阻塞 Tomcat 线程。

## 数据库

### MySQL（后端主库）

| 表 | 主要字段 | 说明 |
|----|----------|------|
| `user` | id, username, phone, password_hash, cookie, created_at, updated_at | 用户 |
| `video` | id, url, user_id, title, status, part, summary, subtitle_count, created_at | status: 0=处理中 / 1=完成 / 2=失败 |
| `subtitle` | id, video_id, content, start_at, end_at | 字幕片段 |
| `conversation` | id, user_id, video_id, title, status, subtitle_count, created_at, updated_at | 会话，status=0 表示处理中 |
| `message` | id, conversation_id, role, content, created_at | role: user / ai |

### SQLite / Qdrant（Python Agent 本地）

| 存储 | 表/集合 | 说明 |
|------|---------|------|
| `data/video_store.db` | `videos`, `transcript_segments`, `transcript_chunks` | 视频元数据、字幕、文本块 |
| Qdrant / `data/vector_store.db` | `video_chunk_vectors` | 文本块向量，余弦相似度检索 |
| `data/conversation_store.db` | `conversation_messages` | 对话历史 |

---

# Python Agent 新增：本地重排序器

**文件：** `video-mind-agent/app/services/reranker.py`

在向量粗召回之后，使用 `LocalReranker` 进行术语匹配精排：

| 阶段 | 算法 | 说明 |
|------|------|------|
| 粗召回 | 余弦相似度 | 从 Qdrant/vector_store 取 Top-N 候选 |
| 精排 | 术语匹配 | 计算 recall（候选覆盖查询术语的比例）× 0.8 + density（匹配词密度）× 0.2 |
| 双元组 | 中文 bigram | 中文按相邻两字切词，提升短查询匹配精度 |

设计为可替换接口，生产环境可接入 Cross-Encoder（如 bge-reranker、Cohere Rerank）。

---

# 流式保活与假死检测

| 层级 | 机制 | 超时 |
|------|------|------|
| Python → Java SSE | `:ping` 保活注释（heartbeat 行） | 30s 内无任何行则超时 |
| Java 业务假死 | 只有 ping 无 chunk 超 25s → 抛异常终止 | 区分"网络存活"与"Agent 卡死" |
| Java SSE (WebClient) | `responseTimeout(5min)` + `blockLast(5min)` | 总超时兜底 |
| 实例心跳 | `@Scheduled(10s)` → Redis TTL 30s | 25s 无心跳判死 |
| 前端指数退避 | delays [1s, 2s, 4s] × 3 次重试 | 共约 7s 内自动恢复 |

---

# 优缺点分析

## 优点

| 方面 | 说明 |
|------|------|
| **任务不丢失** | RabbitMQ 持久化 + Manual ACK，JVM 崩溃后重启可继续消费 |
| **水平扩展** | Java 多实例通过 RabbitMQ 竞争消费；Redis 实现 SSE 路由，chunk 自动转发到正确实例 |
| **优雅下线** | `@PreDestroy` 清理 Redis 注册信息，不影响其他实例 |
| **断线重连** | 页面刷新/切换历史后自动恢复流式输出，无需重新提交 |
| **提前可见** | metadata 事件让标题/BV 号在解析完成后立即可见，Conversation 提前入库让历史列表即时刷新 |
| **假死检测** | 多层超时 + ping 保活，区分网络断开和 Agent 卡死 |
| **分布式锁 + 看门狗** | Lua 原子操作续期，防死锁；共享等待机制，多人请求同一视频不重复处理 |
| **本地重排序** | 向量检索后术语精排，提升问答相关性；可插拔设计 |
| **幂等消费** | RabbitMQ 消费者查库跳过已完成/失败任务，不重复处理 |

## 缺点与注意点

| 方面 | 说明 |
|------|------|
| **基础设施依赖重** | 需要 MySQL + Redis + RabbitMQ + Qdrant 四个中间件，单机部署资源占用高 |
| **Redis 单点** | SSE 路由和实例发现都依赖 Redis，Redis 宕机则多实例路由失效 |
| **会话 TTL 限制** | SSE session TTL 10 分钟，超长视频的总结生成可能超时 |
| **无消息顺序保证** | RabbitMQ 竞争消费模式下，同一队列的消息可能乱序处理（当前业务不敏感） |
| **catchup 内存占用** | 超长字幕文本缓存在 `contentBuffers` 中，大量并发可能 OOM |
| **前端 sessionStorage** | 会话状态仅在当前标签页有效，关闭标签页后无法恢复 |
| **硬编码地址** | `fetch_video.py` 中 Bilibili 爬取配置硬编码（FIXME 标注） |
| **单 Agent 实例** | Python Agent 目前无多实例支持，若 Agent 挂了全部任务失败 |

---

# 已知注意点

1. RabbitMQ 消费走 `onParseTask()` / `onChatTask()`，旧的同步 `chat(ChatDTO)` 方法已废弃。
2. `doProcess()` 中 `parserServiceUrl` 通过配置注入，默认 `http://localhost:8001`，Docker Compose 中自动指向 `vm-parser`。
3. 前端文件上传功能目前仅设置文件名，尚未实现实际上传。
4. 生产环境 `docker-compose-prod.yml` 引入了 Nacos 服务发现（端口 8848），开发环境 `docker-compose.yml` 不使用。
5. 多实例部署时需确保 `INSTANCE_ID` 环境变量唯一，否则 Redis 路由冲突。
6. Python Agent 的 Qdrant 支持通过环境变量 `QDRANT_HOST` / `QDRANT_PORT` 配置，未配置时降级为 SQLite 向量存储。

---

# 附录：Python 分块与向量检索

## 文本分块

- 带时间轴的分块：`[start_time]s 字幕文本`，按句子/字数切分后写入 `transcript_chunks`。
- 最终存储到向量库时附带 `start_time`、`end_time`，方便问答时引用时间戳。

## 向量检索 + 重排序

1. 对问题调用 Embedding API 得到向量。
2. 从 Qdrant / SQLite 加载该视频全部候选块。
3. 计算余弦相似度，取 Top-N 候选。
4. **LocalReranker 精排**：术语匹配 recall + density 计算，返回 Top-K。
5. 未配置 Embedding API 时降级为 `HashEmbeddingClient`。
