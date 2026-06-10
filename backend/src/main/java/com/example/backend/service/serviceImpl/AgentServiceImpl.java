package com.example.backend.service.serviceImpl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.backend.common.BaseContext;
import com.example.backend.common.BilibiliUrlUtils;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.entity.Subtitle;
import com.example.backend.entity.Video;
import com.example.backend.mapper.SubtitleMapper;
import com.example.backend.mapper.VideoMapper;
import com.example.backend.service.AgentService;
import com.example.backend.vo.SummaryResult;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
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

    @Value("${agent.service.url:http://localhost:8765}")
    private String agentServiceUrl;

    // ========== SSE 单机内存连接池 ==========
    // key: sessionId, value: SseEmitter 对象
    // 用于存储前端建立的 SSE 长连接，处理完成后通过该连接推送结果
    private final Map<String, SseEmitter> emitters = new ConcurrentHashMap<>();

    // key: sessionId, value: videoId
    // 用于建立 sessionId 与视频记录的映射，推送时知道更新哪条记录
    private final Map<String, Long> sidToVideoId = new ConcurrentHashMap<>();

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

        log.info("[Summary] 请求解析: rawUrl={}, baseUrl={}, part={}, userId={}", rawUrl, baseUrl, part, userId);

        // 先查询 video 数据表中有没有相同的url以及part，如果有则直接读取summary内容并且返回
        // 要求同一baseUrl，同一part，status为1
        Video exist = videoMapper.selectOne(
            Wrappers.<Video>lambdaQuery()
                .eq(Video::getUrl, baseUrl)
                .eq(Video::getPart, part)
                .eq(Video::getStatus, 1)
        );

        // 如果有，那么直接返回summary
        if (exist != null) {
            log.info("[Summary] 命中缓存: videoId={}, title={}, url={}, part={}",
                exist.getId(), exist.getTitle(), exist.getUrl(), exist.getPart());
            SummaryResult cache = new SummaryResult();
            cache.setVideoId(exist.getId());
            // 命中缓存，不需要 SSE
            cache.setSessionId("");
            cache.setStatus(1);
            cache.setTitle(exist.getTitle());
            cache.setSummary(exist.getSummary());
            cache.setSubtitleCount(exist.getSubtitleCount());
            return cache;
        }

        log.info("[Summary] 未命中缓存，创建新记录: baseUrl={}, part={}", baseUrl, part);

        // 如果没有，则创建记录，标记为"处理中"
        Video video = new Video();
        video.setCreateAt(LocalDateTime.now());
        video.setPart(part);
        video.setUrl(baseUrl);
        video.setUserId(userId);
        video.setStatus(0);
        this.save(video);
        Long videoId = video.getId();

        // 生成 sessionId，绑定 videoId 关系
        // 使用 UUID 确保全局唯一，作为 SSE 连接的凭证
        String sid = UUID.randomUUID().toString();
        sidToVideoId.put(sid, videoId);

        // 启动后台线程处理耗时逻辑（B站解析 + 大模型总结）
        // 使用 CompletableFuture.runAsync 避免阻塞 Tomcat 线程，提升并发能力
        CompletableFuture.runAsync(() -> doProcess(videoId, baseUrl, part, userId, cookie, sid));

        // 立即返回前端：正在处理，请通过 sessionId 建立 SSE 连接监听结果
        SummaryResult res = new SummaryResult();
        res.setVideoId(videoId);
        res.setSessionId(sid);
        // 处理中
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
        // 5 分钟超时：足够大模型推理 + 网络波动，单位毫秒
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
        sidToVideoId.remove(sid);
    }

    /**
     * 异步处理核心逻辑
     * 将原来 summary 方法中的耗时操作（B站解析、字幕入库、Agent总结）全部移至此处
     * 处理完成后通过 SSE 推送给前端，并更新数据库状态
     */
    private void doProcess(Long videoId, String baseUrl, Integer part,
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

            // 得到JSON数据的返回，解析每条subtitle，把完整信息插入数据表
            StringBuilder fullText = new StringBuilder();
            int count = 0;

            List<Subtitle> subList = new ArrayList<>();

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
                }
            }

            // 一次性批量入库
            if (!subList.isEmpty()) {
                subtitleMapper.insertBatch(subList);
            }

            // 调用 Agent 服务进行字幕处理和总结
            // video_id 使用 bvid + "_p" + part 格式，确保唯一性
            String agentVideoId = (bvid != null ? bvid : "video") + "_p" + part;
            String transcriptText = fullText.toString();
            System.out.println("[Agent] 调用process: video_id=" + agentVideoId
                + ", title长度=" + (title != null ? title.length() : 0)
                + ", 字幕字数=" + transcriptText.length());

            Map<String, Object> processReq = new HashMap<>();
            processReq.put("video_id", agentVideoId);
            processReq.put("title", title != null ? title : "");
            processReq.put("transcript_text", transcriptText);
            processReq.put("user_id", String.valueOf(userId));

            // 使用 HttpURLConnection 直接发送，强制固定长度模式，避免 chunked 编码
            ObjectMapper mapper = new ObjectMapper();
            byte[] bodyBytes = mapper.writeValueAsBytes(processReq);

            URL agentUrl = new URL(agentServiceUrl + "/api/process");
            HttpURLConnection conn = (HttpURLConnection) agentUrl.openConnection();
            conn.setRequestMethod("POST");
            conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8");
            conn.setDoOutput(true);
            conn.setDoInput(true);
            conn.setFixedLengthStreamingMode(bodyBytes.length);
            // 建议加上超时，防止 Python 服务挂了 Java 一直等
            conn.setConnectTimeout(10000);
            conn.setReadTimeout(120000); // 2分钟读取超时

            try (OutputStream os = conn.getOutputStream()) {
                os.write(bodyBytes);
                os.flush();
            }

            int responseCode = conn.getResponseCode();
            InputStream responseStream = (responseCode < 400)
                ? conn.getInputStream()
                : conn.getErrorStream();
            Map processResult = mapper.readValue(responseStream, Map.class);
            conn.disconnect();

            System.out.println("[Agent] process返回: " + processResult);
            String summary = (processResult != null && processResult.get("summary") != null)
                ? (String) processResult.get("summary")
                : "总结生成失败";

            // 更新 video 为完成状态
            Video finish = new Video();
            finish.setId(videoId);
            finish.setTitle(title);
            finish.setSummary(summary);
            finish.setStatus(1);
            finish.setSubtitleCount(count);
            videoMapper.updateById(finish);

            // ========== SSE 流式推送总结给前端 ==========
            // 把总结内容逐段推送，模拟流式打字机效果
            int step = 20;
            for (int i = 0; i < summary.length(); i += step) {
                int end = Math.min(i + step, summary.length());
                String chunk = summary.substring(0, end);
                pushChunk(sid, chunk);
                try {
                    Thread.sleep(40);
                } catch (InterruptedException ie) {
                    Thread.currentThread().interrupt();
                    break;
                }
            }
            // 最后推送完成事件，携带完整数据
            pushDone(sid, videoId, title, summary, count);

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
        if (emitter == null) return;
        try {
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
    private void pushDone(String sid, Long videoId, String title, String summary, int count) {
        SseEmitter emitter = emitters.get(sid);
        if (emitter == null) return;
        try {
            Map<String, Object> payload = new HashMap<>();
            payload.put("type", "done");
            payload.put("videoId", videoId);
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
}
