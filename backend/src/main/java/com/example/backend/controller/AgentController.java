package com.example.backend.controller;

import com.example.backend.common.Result;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.service.AgentService;
import com.example.backend.vo.SummaryResult;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

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
        SummaryResult result = agentService.summary(summaryDTO);
        return Result.success(result);
    }
}
