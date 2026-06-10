package com.example.backend.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.entity.Video;
import com.example.backend.vo.SummaryResult;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

public interface AgentService extends IService<Video> {

    SseEmitter connectSse(String sid);

    SummaryResult submitSummary(SummaryDTO summaryDTO);
}
