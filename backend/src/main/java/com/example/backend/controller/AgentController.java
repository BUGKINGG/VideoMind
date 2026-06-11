package com.example.backend.controller;

import com.example.backend.common.Result;
import com.example.backend.dto.ChatDTO;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.service.AgentService;
import com.example.backend.vo.ChatResult;
import com.example.backend.vo.SummaryResult;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

@Slf4j
@RestController
@RequestMapping("/agent")
@Tag(name = "agent相关接口")
public class AgentController {

    @Autowired
    private AgentService agentService;

    @PostMapping("/summary")
    @Operation(summary = "视频分析")
    public Result<SummaryResult> summary(@RequestBody SummaryDTO summaryDTO){
        log.info("开始视频分析，URL为:{}", summaryDTO);
        SummaryResult result = agentService.submitSummary(summaryDTO);
        return Result.success(result);
    }

    /**
     * SSE 长连接接口（总结）
     */
    @GetMapping(value = "/summary/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@RequestParam String sid) {
        return agentService.connectSse(sid);
    }

    /**
     * 提交视频对话任务（两步式流式）
     * 1. 前端 POST 提交，后端保存用户消息，启动异步处理，返回 sessionId
     * 2. 前端 GET /chat/stream 建立 SSE 连接，接收 AI 流式回复
     */
    @PostMapping("/chat")
    @Operation(summary = "提交视频对话")
    public Result<ChatResult> chat(@RequestBody ChatDTO chatDTO) {
        log.info("提交对话: conversationId={}, message={}", chatDTO.getConversationId(), chatDTO.getMessage());
        ChatResult result = agentService.submitChat(chatDTO);
        return Result.success(result);
    }

    /**
     * 视频对话 SSE 流式推送
     * 前端通过 fetch + ReadableStream 连接，携带 token 通过 Spring 拦截器
     */
    @GetMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    @Operation(summary = "视频对话流式推送")
    public SseEmitter chatStream(@RequestParam String sid) {
        return agentService.connectChatSse(sid);
    }
}
