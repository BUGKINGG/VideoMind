package com.example.backend.service.serviceImpl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.backend.common.BaseContext;
import com.example.backend.common.BilibiliUrlUtils;
import com.example.backend.common.RedisLockUtil;
import com.example.backend.dto.ChatDTO;
import com.example.backend.entity.*;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.mapper.ConversationMapper;
import com.example.backend.mapper.MessageMapper;
import com.example.backend.mapper.SubtitleMapper;
import com.example.backend.mapper.VideoMapper;
import com.example.backend.service.AgentService;
import com.example.backend.vo.ChatResult;
import com.example.backend.vo.SummaryResult;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.rabbitmq.client.Channel;
import io.netty.channel.ChannelOption;
import io.swagger.v3.oas.annotations.headers.Header;
import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.rabbit.annotation.RabbitListener;
import org.springframework.amqp.rabbit.core.RabbitTemplate;
import org.springframework.amqp.support.AmqpHeaders;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.reactive.function.client.WebClient;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import reactor.netty.http.client.HttpClient;


import java.io.IOException;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
public class AgentServiceImpl extends ServiceImpl<VideoMapper, Video> implements AgentService {

    @Autowired
    private VideoMapper videoMapper;
    @Autowired
    private RestTemplate restTemplate;
    @Autowired
    private SubtitleMapper subtitleMapper;
    @Autowired
    private ConversationMapper conversationMapper;
    @Autowired
    private RabbitTemplate rabbitTemplate;

    @Value("${agent.service.url:http://localhost:8765}")
    private String agentServiceUrl;

    // key: sessionId, value: SseEmitter 对象
    // 用于存储前端建立的 SSE 长连接，处理完成后通过该连接推送结果
    private final Map<String, SseEmitter> emitters = new ConcurrentHashMap<>();



    @Autowired
    private StringRedisTemplate redisTemplate;

    @Autowired
    private MessageMapper messageMapper;
    @Autowired
    private RedisLockUtil redisLockUtil;

    // ========== 已经迁移到 Redis 的 ==========
    // key: videomind:sse:summary:{sid}  value: videoId
    // key: videomind:sse:chat:{sid}     value: conversationId:userMessageId
    // key: videomind:video:agent_id:{videoId}  value: agentVideoId

    private static final String REDIS_SSE_SUMMARY_PREFIX = "videomind:sse:summary:";
    private static final String REDIS_SSE_CHAT_PREFIX = "videomind:sse:chat:";
    private static final String REDIS_VIDEO_AGENT_PREFIX = "videomind:video:agent_id:";
    private static final long REDIS_SSE_TTL_MINUTES = 10;
    private static final String REDIS_LOCK_VIDEO_PREFIX = "videomind:lock:video:";
    private static final long LOCK_WAIT_RETRY_MS = 500;
    private static final int LOCK_MAX_RETRY = 6;
    private static final String REDIS_USER_LIMIT = "videomind:limit:";

    private WebClient agentWebClient;

    @PostConstruct
    public void init() {
        this.agentWebClient = WebClient.builder().baseUrl(agentServiceUrl)
            .clientConnector(new ReactorClientHttpConnector(
                HttpClient.create()
                    .responseTimeout(Duration.ofMinutes(5))
                    .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, 10000)
            ))
            .build();
    }

    /**
     * 提交总结任务（同步入口）
     * 1. 检查数据库缓存（已完成的直接返回）
     * 2. 创建 video 记录，标记为处理中 (status=0)
     * 3. 生成 sessionId 并绑定 videoId
     * 4. 启动 CompletableFuture 异步执行耗时逻辑
     * 5. 立即返回 sessionId 给前端，前端据此建立 SSE 连接监听结果
     */
    @Transactional
    @Override
    public SummaryResult submitSummary(SummaryDTO summaryDTO) {
        // dto里存放着url和cookie
        String rawUrl = summaryDTO.getUrl();
        String baseUrl = BilibiliUrlUtils.extractBaseUrl(rawUrl);
        String cookie = summaryDTO.getCookie();
        Integer part = BilibiliUrlUtils.extractPart(rawUrl);
        Long userId = BaseContext.getCurrentId();

        // 用redis对用户进行限流，限制每10秒只能进行一次总结，放置脚本刷爆token
        String limitKey = REDIS_USER_LIMIT + userId.toString();
        // 如果redis没有开或者死亡，则放行并抛出log，否则会阻塞业务
        // 但实际上如果redis死亡，后面的业务都无法实现，前端会返回500
        try{
            Boolean allowed = redisTemplate.opsForValue().
                setIfAbsent(limitKey, "1", Duration.ofSeconds(10));
            if(!allowed) {
                throw new RuntimeException("操作太频繁，请稍后再试");
            }
        }catch(Exception e){
            log.warn("redis死亡，降级放行");
        }

        log.info("[Summary] 请求解析: rawUrl={}, baseUrl={}, part={}, userId={}", rawUrl, baseUrl, part, userId);

        // 先查询 video 数据表中有没有相同的url以及part，如果有则直接读取summary内容并且返回
        // 免去SSE的建立
        // 要求同一baseUrl，同一part，status为1
        Video exist = videoMapper.selectOne(
            Wrappers.<Video>lambdaQuery()
                .eq(Video::getUrl, baseUrl)
                .eq(Video::getPart, part)
        );

        // 如果有并且已经处理完（status为1），那么直接返回summary
        if (exist != null && exist.getStatus() == 1) {
            log.info("[Summary] 命中缓存: videoId={}, title={}, url={}, part={}",
                exist.getId(), exist.getTitle(), exist.getUrl(), exist.getPart());
            // 查询对应的conversation
            Conversation existConv = conversationMapper.selectOne(
                Wrappers.<Conversation>lambdaQuery()
                    .eq(Conversation::getVideoId, exist.getId())
                    .eq(Conversation::getUserId, userId)
                    .eq(Conversation::getStatus, 1)
                    .orderByDesc(Conversation::getCreatedAt)
                    .last("LIMIT 1")
            );
            SummaryResult cache = new SummaryResult();
            cache.setVideoId(exist.getId());
            // 命中缓存，不需要 SSE
            cache.setSessionId("");
            cache.setStatus(1);
            cache.setTitle(exist.getTitle());
            cache.setSummary(exist.getSummary());
            cache.setSubtitleCount(exist.getSubtitleCount());
            if (existConv != null) {
                cache.setConversationId(existConv.getId());
            }
            return cache;
        }

        // 如果status为2，说明之前处理失败，把记录删除然后重新处理
        if(exist != null && exist.getStatus() == 2){
            log.info("删除处理失败的视频重新处理");
            videoMapper.deleteById(exist);
        }

        log.info("[Summary] 未命中缓存，创建新记录: baseUrl={}, part={}", baseUrl, part);

        // 构造分布式锁
        // 如果同时有多个用户并发的解析同一个视频，会导致数据库有多条相同的数据
        // 由于对redis是单进程的，而且指令的执行是单线程，因此所有请求会在redis中排队
        // 当有用户的线程拿到了锁，则该用户得到唯一的密码，否则返回null
        String lockKey = REDIS_LOCK_VIDEO_PREFIX + baseUrl + ":" + part;
        String lockValue = redisLockUtil.tryLock(lockKey, Duration.ofSeconds(30));

       if (lockValue != null) {
            // 获取锁成功，仅允许带了锁的线程对视频进行CRUD和解析（免得浪费token)
            try {
                // 3. 双重检查：拿到锁后再查一次（等锁期间可能别人已经创建好了）
                // 这两次检查不能合并，如果不要上面的检查，会导致只有拿到锁的线程才能查到缓存
                // 导致并行退化成串行（都被迫等到自己拿锁）
                exist = videoMapper.selectOne(
                    Wrappers.<Video>lambdaQuery()
                        .eq(Video::getUrl, baseUrl)
                        .eq(Video::getPart, part)
                        .eq(Video::getStatus, 1)
                );
                if (exist != null) {
                    log.info("[Summary] 双重检查命中缓存: videoId={}", exist.getId());
                    return buildCacheResult(exist, userId);
                }

                // 4. 确认没有正在处理中的记录（防止死锁残留或异常）
                Video processing = videoMapper.selectOne(
                    Wrappers.<Video>lambdaQuery()
                        .eq(Video::getUrl, baseUrl)
                        .eq(Video::getPart, part)
                        .eq(Video::getStatus, 0)
                );
                if (processing != null) {
                    // 别人正在处理，直接共享等待（不重复创建）
                    log.info("[Summary] 发现已有任务在处理中，共享等待: videoId={}",
                        processing.getId());
                    return buildProcessingResult(processing, userId);
                }

                // 5. 真正创建新记录，启动任务
                log.info("[Summary] 未命中缓存，创建新记录: baseUrl={}, part={}",
                    baseUrl, part);
                Video video = new Video();
                video.setCreateAt(LocalDateTime.now());
                video.setPart(part);
                video.setUrl(baseUrl);
                video.setUserId(userId);
                video.setStatus(0);
                this.save(video);
                Long videoId = video.getId();

                String sid = UUID.randomUUID().toString();
                String redisKey = REDIS_SSE_SUMMARY_PREFIX + sid;
                redisTemplate.opsForValue().set(redisKey, videoId.toString(),
                    Duration.ofMinutes(REDIS_SSE_TTL_MINUTES));

                ParseTask task = new ParseTask();
                task.setVideoId(videoId);
                task.setSid(sid);
                task.setCookie(cookie);
                task.setPart(part);
                task.setBaseUrl(baseUrl);
                task.setUserId(userId);
                rabbitTemplate.convertAndSend("videomind.parse.exchange", "parse", task);

                SummaryResult res = new SummaryResult();
                res.setVideoId(videoId);
                res.setSessionId(sid);
                res.setStatus(0);
                return res;

            } finally {
                // 6. 释放锁（30秒内任务肯定已经启动，锁可以释放）
                // 实际处理由 CompletableFuture 在后台继续，不依赖锁
                redisLockUtil.unlock(lockKey, lockValue);
            }
        }

        // 7. 获取锁失败：别人正在创建/处理，轮询等待
        log.info("[Summary] 获取锁失败，进入轮询等待: baseUrl={}, part={}", baseUrl, part);

        for (int i = 0; i < LOCK_MAX_RETRY; i++) {
            try {
                Thread.sleep(LOCK_WAIT_RETRY_MS);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                throw new RuntimeException("等待中断");
            }

            // 再次查缓存
            exist = videoMapper.selectOne(
                Wrappers.<Video>lambdaQuery()
                    .eq(Video::getUrl, baseUrl)
                    .eq(Video::getPart, part)
                    .eq(Video::getStatus, 1)
            );
            if (exist != null) {
                log.info("[Summary] 轮询命中缓存: videoId={}", exist.getId());
                return buildCacheResult(exist, userId);
            }

            // 查是否已有处理中的记录
            Video processing = videoMapper.selectOne(
                Wrappers.<Video>lambdaQuery()
                    .eq(Video::getUrl, baseUrl)
                    .eq(Video::getPart, part)
                    .eq(Video::getStatus, 0)
            );
            if (processing != null) {
                log.info("[Summary] 轮询发现处理中，共享等待: videoId={}",
                    processing.getId());
                return buildProcessingResult(processing, userId);
            }
        }

        // 8. 轮询结束仍未命中，返回错误让前端重试
        log.error("[Summary] 轮询超时仍未获取结果: baseUrl={}, part={}", baseUrl, part);
        throw new RuntimeException("系统繁忙，请稍后重试");
    }

    private SummaryResult buildCacheResult(Video video, Long userId) {
        Conversation existConv = conversationMapper.selectOne(
            Wrappers.<Conversation>lambdaQuery()
                .eq(Conversation::getVideoId, video.getId())
                .eq(Conversation::getUserId, userId)
                .eq(Conversation::getStatus, 1)
                .orderByDesc(Conversation::getCreatedAt)
                .last("LIMIT 1")
        );
        SummaryResult cache = new SummaryResult();
        cache.setVideoId(video.getId());
        cache.setSessionId("");
        cache.setStatus(1);
        cache.setTitle(video.getTitle());
        cache.setSummary(video.getSummary());
        cache.setSubtitleCount(video.getSubtitleCount());
        if (existConv != null) {
            cache.setConversationId(existConv.getId());
        }
        return cache;
    }

    private SummaryResult buildProcessingResult(Video processing, Long userId) {
        // 生成新的 sid，绑定到同一个 videoId
        // 前端用这个 sid 连 SSE，等后台任务完成后统一推送
        String sid = UUID.randomUUID().toString();
        String redisKey = REDIS_SSE_SUMMARY_PREFIX + sid;
        redisTemplate.opsForValue().set(redisKey, processing.getId().toString(),
            Duration.ofMinutes(REDIS_SSE_TTL_MINUTES));

        SummaryResult res = new SummaryResult();
        res.setVideoId(processing.getId());
        res.setSessionId(sid);
        res.setStatus(0);
        return res;
    }

    /**
     * 建立 SSE 长连接
     * 1. 创建 SseEmitter，设置 5 分钟超时（足够 deepseek-v4-pro 推理 + 网络波动）
     * 2. 存入内存池，绑定 sessionId
     * 3. 注册 onCompletion/onTimeout/onError 回调，防止连接断开时内存泄漏
     * 4. 发送 connect 事件通知前端连接成功
     *
     * 注意：前端使用 fetch + ReadableStream 连接，通过 Headers 携带 token
     * 因此可以正常通过 Spring 的 token 拦截器验证
     */
    @Override
    public SseEmitter connectSse(String sid) {
        String redisKey = REDIS_SSE_SUMMARY_PREFIX + sid;
        String videoIdStr = redisTemplate.opsForValue().get(redisKey);

        // redisKey过期或者无效，则直接返回错误
        if(videoIdStr == null){
            SseEmitter deadEmitter = new SseEmitter(0L);
            try{
                deadEmitter.send(SseEmitter.event()
                    .name("error")
                    .data("{\"type\":\"error\",\"message\":\"会话已过期或不存在\"}")
                );
                deadEmitter.complete();
            } catch (Exception e) {
                log.error("发送过期通知失败：", e);
            }
            return deadEmitter;
        }

        Long videoId = Long.valueOf(videoIdStr);


        // 如果视频已经处理完了，直接返回结果
        Video video = videoMapper.selectById(videoId);
        if(video != null && video.getStatus() == 2) {
            SseEmitter failEmitter = new SseEmitter(30_000L);
            try{
                failEmitter.send(SseEmitter.event()
                    .name("error")
                    .data("{\"type\":\"error\",\"message\":\"cookie已过期或者该视频没有字幕\"}")
                );
            } catch (Exception e){
                log.info("返回fail错误：", e);
            }
            return failEmitter;
        }

        if(video != null && video.getStatus() == 1){
            SseEmitter emitter = new SseEmitter(0L);
            try {
                Conversation existConv = conversationMapper.selectOne(
                    Wrappers.<Conversation>lambdaQuery()
                        .eq(Conversation::getVideoId, videoId)
                        .eq(Conversation::getUserId, video.getUserId())
                        .eq(Conversation::getStatus, 1)
                        .orderByDesc(Conversation::getCreatedAt)
                        .last("LIMIT 1")
                );

                Map<String, Object> payload = new HashMap<>();
                payload.put("type", "done");
                payload.put("videoId", videoId);
                payload.put("conversationId", existConv != null ? existConv.getId() : null);
                payload.put("title", video.getTitle());
                payload.put("summary", video.getSummary());
                payload.put("subtitleCount", video.getSubtitleCount());

                emitter.send(SseEmitter.event()
                    .name("message")
                    .data(new ObjectMapper().writeValueAsString(payload)));
                emitter.complete();
            } catch (Exception e) {
                log.error("补发已完成事件失败", e);
            }
            return emitter;
        }

        // 视频还在处理中，建立SSE长连接
        SseEmitter emitter = new SseEmitter(300_000L);
        emitters.put(sid, emitter);

        // 连接关闭/超时/报错时，必须从内存移除，防止内存泄漏
        emitter.onCompletion(() -> cleanSid(sid));
        emitter.onTimeout(() -> cleanSid(sid));
        emitter.onError((e) -> cleanSid(sid));

        // 发送连接成功事件（前端可据此显示"已连接，等待中..."）
        try {
            emitter.send(SseEmitter.event()
                .name("connect")
                .data("{\"status\":0,\"msg\":\"connected\"}"));
        } catch (Exception e) {
            // 发送失败说明连接已断开，立即清理
            cleanSid(sid);
        }
        return emitter;
    }

    /**
     * 清理指定 sessionId 的内存数据
     * 防止连接断开后 emitter 和映射关系残留在内存中导致泄漏
     */
    private void cleanSid(String sid) {
        emitters.remove(sid);
    }

    /**
     * 异步处理核心逻辑
     * 将原来 summary 方法中的耗时操作（B站解析、字幕入库、Agent总结）全部移至此处
     * 处理完成后通过 SSE 推送给前端，并更新数据库状态
     * 大概流程：
     * java把url、cookie传给python，python进行字幕扒取写成JSON文件再返回
     * java得到JSON文件后一条一条读取，然后一次性写入数据库
     * 写入完数据库后把字幕全部返回给视频解析agent
     * 视频解析agent得到结果再返回java端
     */
    @Async
    protected void doProcess(Long videoId, String baseUrl, Integer part,
        Long userId, String cookie, String sid) {
        try {
            // 给python视频解析服务传递url和cookie
            String pythonUrl = "http://localhost:8001/parse";

            if (cookie != null && !cookie.isEmpty() && !cookie.contains("=")) {
                cookie = "SESSDATA=" + cookie;
            }

            // 构造请求体
            Map<String, String> requestBody = new HashMap<>();
            requestBody.put("url", baseUrl);
            requestBody.put("cookie", cookie);
            requestBody.put("part", part.toString());

            // 发送 POST
            ResponseEntity<Map> response = restTemplate.postForEntity(
                pythonUrl,
                requestBody,
                Map.class
            );

            // 取结果
            Map result = response.getBody();
            if (result == null || !Integer.valueOf(200).equals(result.get("code"))) {
                throw new RuntimeException("字幕解析失败: " + (result != null ? result.get("message") : "无响应"));
            }

            String title = (String) result.get("title");
            String bvid = (String) result.get("bvid");
            log.info("[Agent] parse返回: title={}, bvid={}, 字幕轨道数={}",
                title, bvid, result.get("subtitles") != null ? ((List)result.get("subtitles")).size() : 0);
            List<Map<String, Object>> subtitles = (List<Map<String, Object>>) result.get("subtitles");

            // 如果字幕为空，那么是cookie失效了或者该视频没有字幕
            if(subtitles == null || subtitles.isEmpty()){
                pushError(sid, "cookie已过期或者该视频没有字幕");
                // 更新 video 为完成状态
                Video fail = new Video();
                fail.setId(videoId);
                fail.setTitle(title);
                fail.setSummary("cookie已过期或该视频没有字幕");
                fail.setStatus(2);
                fail.setSubtitleCount(0);
                videoMapper.updateById(fail);
                return;
            }

            // 得到JSON数据的返回，解析每条subtitle，把完整信息插入数据表
            StringBuilder fullText = new StringBuilder();
            int count = 0;

            List<Subtitle> subList = new ArrayList<>();
            List<Map<String, Object>> segments = new ArrayList<>();

            for (Map<String, Object> track : subtitles) {
                List<Map<String, Object>> body = (List<Map<String, Object>>) track.get("body");
                if (body == null) continue;
                for (Map<String, Object> item : body) {
                    String content = (String) item.get("content");
                    Double start = ((Number) item.get("start")).doubleValue();
                    Double end = ((Number) item.get("end")).doubleValue();

                    Subtitle sub = new Subtitle();
                    sub.setVideoId(videoId);
                    sub.setContent(content);
                    sub.setStartAt(start);
                    sub.setEndAt(end);
                    subList.add(sub);

                    fullText.append(content).append("\n");
                    count++;

                    Map<String, Object> seg = new HashMap<>();
                    seg.put("text", content);
                    seg.put("start_time", start);
                    seg.put("end_time", end);
                    segments.add(seg);
                }
            }

            // 一次性批量入库
            if (!subList.isEmpty()) {
                subtitleMapper.insertBatch(subList);
            }

            // 调用 Agent 服务进行字幕处理和总结
            // video_id 使用 bvid + "_p" + part 格式，确保唯一性
            String agentVideoId = (bvid != null ? bvid : "video") + "_p" + part;
            String agentIdKey = REDIS_VIDEO_AGENT_PREFIX + videoId;
            redisTemplate.opsForValue().set(agentIdKey, agentVideoId);
            String transcriptText = fullText.toString();
            System.out.println("[Agent] 调用process: video_id=" + agentVideoId
                + ", title长度=" + (title != null ? title.length() : 0)
                + ", 字幕字数=" + transcriptText.length());

            Map<String, Object> processReq = new HashMap<>();
            processReq.put("video_id", agentVideoId);
            processReq.put("title", title != null ? title : "");
            processReq.put("transcript_text", transcriptText);
            processReq.put("segments", segments);
            processReq.put("user_id", String.valueOf(userId));

            StringBuilder summaryBuilder = new StringBuilder();

            Iterator<String> iterator = agentWebClient.post()
                .uri("/api/process/stream")
                .bodyValue(processReq)
                .retrieve()
                .bodyToFlux(String.class)
                .toStream()
                .iterator();

            while(iterator.hasNext()){
                String line = iterator.next();
                if(line == null || line.isEmpty()){
                    return;
                }
                try {
                    Map<String,Object> data = new ObjectMapper().readValue(line, Map.class);
                    String type = (String) data.get("type");

                    if("chunk".equals(type)) {
                        String content = (String) data.get("content");
                        if (content != null){
                            summaryBuilder.setLength(0);
                            summaryBuilder.append(content);
                            pushChunk(sid, content);
                        }
                    }
                    else if("error".equals(type)){
                        throw new RuntimeException((String) data.get("message"));
                    }
                    else if("done".equals(type)){
                        break;
                    }
                }catch (Exception e){
                    log.error("解析 process chunk 失败：", e);
                }
            }

            String summary = summaryBuilder.toString();

            // 更新 video 为完成状态
            Video finish = new Video();
            finish.setId(videoId);
            finish.setTitle(title);
            finish.setSummary(summary);
            finish.setStatus(1);
            finish.setSubtitleCount(count);
            videoMapper.updateById(finish);

            // 创建conversation表并且保存
            Conversation conversation = new Conversation();
            conversation.setUserId(userId);
            conversation.setTitle(title);
            conversation.setVideoId(videoId);
            conversation.setStatus(1);
            conversation.setSubtitleCount(count);
            conversation.setCreatedAt(LocalDateTime.now());
            conversation.setUpdatedAt(LocalDateTime.now());
            conversationMapper.insert(conversation);

            // 创建message表，插入summary数据并且保存
            Long conversationId = conversation.getId();
            Message message = new Message();
            message.setRole("ai");
            message.setContent(summary);
            message.setConversationId(conversationId);
            message.setCreatedAt(LocalDateTime.now());
            messageMapper.insert(message);

            // 最后推送完成事件，携带完整数据
            pushDone(sid, videoId, conversationId, title, summary, count);

        } catch (Exception e) {
            // 标记失败，避免前端无限等待
            log.error("视频异步处理失败, videoId={}, sid={}, baseUrl={}, part={}", videoId, sid, baseUrl, part, e);
            Video fail = new Video();
            fail.setId(videoId);
            fail.setStatus(2);
            fail.setSummary("处理失败: " + e.getMessage());
            videoMapper.updateById(fail);

            // ========== SSE 推送错误给前端 ==========
            pushError(sid, e.getMessage());
        }
    }

    /**
     * SSE 流式推送：内容片段
     * 前端收到后实时更新 AI 消息内容
     */
    private void pushChunk(String sid, String chunk) {
        SseEmitter emitter = emitters.get(sid);
        if (emitter == null) {
            log.warn("[SSE] pushChunk 失败，sid={} 不在 emitters 池中", sid);
            return;
        }        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("type", "chunk");
            payload.put("content", chunk);
            String json = new ObjectMapper().writeValueAsString(payload);
            emitter.send(SseEmitter.event().name("message").data(json));
        } catch (Exception e) {
            log.warn("SSE chunk 推送失败, sid={}", sid);
            cleanSid(sid);
        }
    }

    /**
     * SSE 流式推送：完成事件
     * 携带完整的视频数据和总结内容，前端收到后标记流式结束
     */
    private void pushDone(String sid, Long videoId, Long conversationId, String title, String summary, int count) {
        SseEmitter emitter = emitters.get(sid);
        if (emitter == null) return;
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("type", "done");
            payload.put("videoId", videoId);
            payload.put("conversationId", conversationId);
            payload.put("title", title);
            payload.put("summary", summary);
            payload.put("subtitleCount", count);
            String json = new ObjectMapper().writeValueAsString(payload);
            emitter.send(SseEmitter.event().name("message").data(json));
            emitter.complete();
        } catch (Exception e) {
            log.error("SSE done 推送失败, sid={}", sid);
            cleanSid(sid);
        }
    }

    /**
     * SSE 流式推送：错误事件
     */
    private void pushError(String sid, String errorMsg) {
        SseEmitter emitter = emitters.get(sid);
        if (emitter == null) return;
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("type", "error");
            payload.put("message", errorMsg);
            String json = new ObjectMapper().writeValueAsString(payload);
            emitter.send(SseEmitter.event().name("error").data(json));
            emitter.complete();
        } catch (Exception e) {
            log.error("SSE error 推送失败, sid={}", sid);
            cleanSid(sid);
        }
    }


    @Transactional
    public ChatResult submitChat(ChatDTO chatDTO) {
        Long userId = BaseContext.getCurrentId();
        Long conversationId = chatDTO.getConversationId();
        String message = chatDTO.getMessage();

        // 保存用户消息
        Message userMsg = new Message();
        userMsg.setConversationId(conversationId);
        userMsg.setRole("user");
        userMsg.setContent(message);
        userMsg.setCreatedAt(LocalDateTime.now());
        messageMapper.insert(userMsg);

        String sid = UUID.randomUUID().toString();
        String redisKey = REDIS_SSE_CHAT_PREFIX + sid;
        // 同时记录 conversationId 与当前用户消息 ID，SSE 连接时用于精确识别“本次请求”的 AI 回复
        redisTemplate.opsForValue().set(redisKey,
                conversationId + ":" + userMsg.getId(),
                Duration.ofMinutes(REDIS_SSE_TTL_MINUTES));

        // 放入消息队列
        ChatTask task = new ChatTask();
        task.setSid(sid);
        task.setConversationId(conversationId);
        task.setUserId(userId);
        task.setMessage(message);
        rabbitTemplate.convertAndSend("videomind.chat.exchange", "chat", task);

        ChatResult res = new ChatResult();
        res.setSessionId(sid);
        res.setStatus(0);
        return res;
    }

   public SseEmitter connectChatSse(String sid) {
    // 1. 从 Redis 验证 sid 是否存在
    String redisKey = REDIS_SSE_CHAT_PREFIX + sid;
    String convIdStr = redisTemplate.opsForValue().get(redisKey);

    if (convIdStr == null) {
        // sid 不存在或已过期，直接返回错误并关闭
        SseEmitter deadEmitter = new SseEmitter(0L);
        try {
            deadEmitter.send(SseEmitter.event()
                .name("error")
                .data("{\"type\":\"error\",\"message\":\"会话已过期或不存在\"}"));
            deadEmitter.complete();
        } catch (Exception e) {
            log.error("发送对话过期通知失败", e);
        }
        return deadEmitter;
    }

    Long conversationId;
    Long userMessageId = null;
    if (convIdStr.contains(":")) {
        String[] parts = convIdStr.split(":");
        conversationId = Long.valueOf(parts[0]);
        userMessageId = Long.valueOf(parts[1]);
    } else {
        conversationId = Long.valueOf(convIdStr);
    }

    // 2. 双重检查：后台线程 doChatProcess 可能已经跑完了
    // 查 message 表，看是否已有属于本次用户消息的 AI 回复（id 大于当前用户消息 id）
    Message latestAiMsg = messageMapper.selectOne(
        Wrappers.<Message>lambdaQuery()
            .eq(Message::getConversationId, conversationId)
            .eq(Message::getRole, "ai")
            .gt(userMessageId != null, Message::getId, userMessageId)
            .orderByDesc(Message::getId)
            .last("LIMIT 1")
    );

    if (latestAiMsg != null) {
        // 已经处理完成，直接补发 done 事件，不挂起等待
        SseEmitter emitter = new SseEmitter(30_000L);
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("type", "done");
            payload.put("conversationId", conversationId);
            payload.put("answer", latestAiMsg.getContent());
            emitter.send(SseEmitter.event()
                .name("message")
                .data(new ObjectMapper().writeValueAsString(payload)));
            emitter.complete();
        } catch (Exception e) {
            log.error("补发对话完成事件失败, sid={}, conversationId={}", sid, conversationId, e);
        }
        return emitter;
    }

    // 3. 还在处理中，建立 SSE 长连接等待 doChatProcess 推送
    SseEmitter emitter = new SseEmitter(120_000L);
    emitters.put(sid, emitter);

    emitter.onCompletion(() -> cleanChatSid(sid));
    emitter.onTimeout(() -> cleanChatSid(sid));
    emitter.onError((e) -> cleanChatSid(sid));

    try {
        emitter.send(SseEmitter.event()
            .name("connect")
            .data("{\"status\":0,\"msg\":\"connected\"}"));
    } catch (Exception e) {
        cleanChatSid(sid);
    }
    return emitter;
}

    private void cleanChatSid(String sid) {
        emitters.remove(sid);
    }

    @Async
    protected void doChatProcess(String sid, Long conversationId, Long userId, String message) {
        try {
            Conversation conversation = conversationMapper.selectById(conversationId);
            Long videoId = conversation.getVideoId();
            Video video = videoMapper.selectById(videoId);

            // 构造 agentVideoId
            String agentVideoId = redisTemplate.opsForValue()
                .get(REDIS_VIDEO_AGENT_PREFIX + videoId.toString());
            if (agentVideoId == null) {
                String bvid = BilibiliUrlUtils.extractBvid(video.getUrl());
                agentVideoId = bvid + "_p" + video.getPart();
            }

            // 调用 Python /api/chat/stream（流式接口）
            Map<String, Object> chatReq = new HashMap<>();
            chatReq.put("user_id", String.valueOf(userId));
            chatReq.put("session_id", conversationId.toString());
            chatReq.put("video_id", agentVideoId);
            chatReq.put("question", message);

            StringBuilder answerBuilder = new StringBuilder();

            Iterator<String> iterator = agentWebClient.post()
                .uri("/api/chat/stream")
                .bodyValue(chatReq)
                .retrieve()
                .bodyToFlux(String.class)
                .toStream()
                .iterator();

            while (iterator.hasNext()){
                    String line = iterator.next();
                    if(line == null || line.isEmpty()) {
                        return;
                    }
                    try {
                        Map<String, Object> data = new ObjectMapper().readValue(line, Map.class);
                        String type = (String) data.get("type");
                        if("chunk".equals(type)) {
                            String content = (String) data.get("content");
                            if(content!= null) {
                                answerBuilder.setLength(0);
                                answerBuilder.append(content);
                                pushChunk(sid, content);
                            }
                        }
                        else if("error".equals(type)) {
                            throw new RuntimeException((String) data.get("content"));
                        }
                        else if("done".equals(type)) {
                            break;
                        }
                    }catch (Exception e) {
                        log.error("chat process 错误：", e);
                    }
                }

            String answer = answerBuilder.toString();

            // 保存 AI 回复
            Message aiMsg = new Message();
            aiMsg.setConversationId(conversationId);
            aiMsg.setRole("ai");
            aiMsg.setContent(answer);
            aiMsg.setCreatedAt(LocalDateTime.now());
            messageMapper.insert(aiMsg);

            // 更新会话时间
            Conversation upd = new Conversation();
            upd.setId(conversationId);
            upd.setUpdatedAt(LocalDateTime.now());
            conversationMapper.updateById(upd);

            // 推送 done（携带完整数据）
            pushChatDone(sid, conversationId, answer);

        } catch (Exception e) {
            log.error("Chat处理失败", e);
            pushError(sid, e.getMessage());
        }
    }

    private void pushChatDone(String sid, Long conversationId, String answer) {
        SseEmitter emitter = emitters.get(sid);
        if (emitter == null) return;
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("type", "done");
            payload.put("conversationId", conversationId);
            payload.put("answer", answer);
            emitter.send(SseEmitter.event().name("message").data(new ObjectMapper().writeValueAsString(payload)));
            emitter.complete();
        } catch (Exception e) {
            cleanChatSid(sid);
        }
    }

    // RabbitMQ consumer，使用虚拟线程
    @RabbitListener(queues = "videomind.parse.queue", ackMode = "MANUAL")
    public void onParseTask(ParseTask task,
                            org.springframework.amqp.core.Message amqpMessage,
                            Channel channel) {
        long tag = amqpMessage.getMessageProperties().getDeliveryTag();
        try {
            // 下面两次查库均是为了保证幂等性
            Video video = videoMapper.selectById(task.getVideoId());
            if (video != null && video.getStatus() == 1) {
                channel.basicAck(tag, false);
                return;
            }

            doProcess(task.getVideoId(), task.getBaseUrl(), task.getPart(),
                task.getUserId(), task.getCookie(), task.getSid());

            video = videoMapper.selectById(task.getVideoId());
            if (video != null && video.getStatus() == 1) {
                channel.basicAck(tag, false);
            } else {
                channel.basicNack(tag, false, true);
            }
        } catch (Exception e) {
            log.error("MQ 解析任务失败", e);
            try { channel.basicNack(tag, false, true); } catch (IOException ex) {}
        }
    }

    @RabbitListener(queues = "videomind.chat.queue", ackMode = "MANUAL")
    public void onChatTask(ChatTask task,
                           org.springframework.amqp.core.Message amqpMessage,
                           Channel channel) {
        long tag = amqpMessage.getMessageProperties().getDeliveryTag();
        try {
            doChatProcess(task.getSid(), task.getConversationId(),
                task.getUserId(), task.getMessage());
            channel.basicAck(tag, false);
        } catch (Exception e) {
            log.error("MQ 对话任务失败", e);
            try { channel.basicNack(tag, false, true); } catch (IOException ex) {}
        }
    }

}
