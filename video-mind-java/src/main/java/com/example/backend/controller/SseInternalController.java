package com.example.backend.controller;

import com.example.backend.service.AgentService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/internal/sse")
@RequiredArgsConstructor
public class SseInternalController {

    private final AgentService agentService;

    @PostMapping("/push")
    public void push(@RequestBody Map<String, Object> payload) {
        String sid = (String) payload.get("sid");
        String type = (String) payload.get("type");
        log.debug("[Internal] 收到实例间推送: sid={}, type={}", sid, type);

        switch (type) {
            case "chunk" -> {
                String token = (String) payload.get("token");
                agentService.pushChunkInternal(sid, token);
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
    }
}
