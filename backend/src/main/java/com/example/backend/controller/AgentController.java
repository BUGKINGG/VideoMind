package com.example.backend.controller;

import com.example.backend.common.Result;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.service.AgentService;
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
     * SSE 长连接接口
     * 前端使用 fetch + ReadableStream 连接，通过 Headers 携带 token
     * 因此可以正常通过 Spring 的 token 拦截器验证
     * produces 指定返回 text/event-stream 格式，浏览器识别为 SSE 流
     */
    @GetMapping(value = "/summary/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter stream(@RequestParam String sid) {
        return agentService.connectSse(sid);
    }
}
