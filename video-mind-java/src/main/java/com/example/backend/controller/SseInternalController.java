package com.example.backend.controller;

import com.example.backend.service.AgentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.scheduling.annotation.Async;
import org.springframework.web.bind.annotation.*;

import java.util.Map;
import java.util.concurrent.CompletableFuture;

@Slf4j
@RestController
@RequestMapping("/internal/sse")
@RequiredArgsConstructor
public class SseInternalController {

    private final AgentService agentService;

    /**
     * 使用虚拟线程执行，不阻塞tomcat线程
     * @param payload
     * @return
     */
    @PostMapping("/push")
    @Async
    public CompletableFuture<ResponseEntity<Void>> push(@RequestBody Map<String, Object> payload) {
        String sid = (String) payload.get("sid");
        String type = (String) payload.get("type");
        log.debug("[Internal] 收到实例间推送: sid={}, type={}", sid, type);

        try {
            switch (type) {
                case "chunk" -> {
                    String token = (String) payload.get("token");
                    agentService.pushChunkInternal(sid, token);
                }
                case "catchup" -> {
                    String json = (String) payload.get("json");
                    agentService.pushCatchupInternal(sid, json);
                }
                case "metadata" -> {
                    String title = (String) payload.get("title");
                    Integer subtitleCount = payload.get("subtitleCount") != null
                        ? Integer.valueOf(payload.get("subtitleCount").toString()) : 0;
                    Long conversationId = payload.get("conversationId") != null
                        ? Long.valueOf(payload.get("conversationId").toString()) : null;
                    agentService.pushMetadataInternal(sid, title, subtitleCount, conversationId);
                }
                case "done" -> {
                    Long videoId = payload.get("videoId") != null
                        ? Long.valueOf(payload.get("videoId").toString()) : null;
                    Long conversationId = payload.get("conversationId") != null
                        ? Long.valueOf(payload.get("conversationId").toString()) : null;
                    String title = (String) payload.get("title");
                    String summary = (String) payload.get("summary");
                    Integer count = payload.get("subtitleCount") != null
                        ? Integer.valueOf(payload.get("subtitleCount").toString()) : 0;
                    agentService.pushDoneInternal(sid, videoId, conversationId, title, summary, count);
                }
                case "error" -> {
                    String msg = (String) payload.get("message");
                    agentService.pushErrorInternal(sid, msg);
                }
                default -> log.warn("[Internal] 未知推送类型: {}", type);
            }
        } catch (Exception e) {
            log.error("[Internal] 推送处理失败: sid={}, type={}", sid, type, e);
            // 捕获异常，不让消费者 B 收到 500，避免 B 重试
        }
        return CompletableFuture.completedFuture(ResponseEntity.ok().build());
    }
}
