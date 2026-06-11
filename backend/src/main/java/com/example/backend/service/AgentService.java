package com.example.backend.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.backend.dto.ChatDTO;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.entity.Video;
import com.example.backend.vo.ChatResult;
import com.example.backend.vo.SummaryResult;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;

public interface AgentService extends IService<Video> {

    SseEmitter connectSse(String sid);

    SummaryResult submitSummary(SummaryDTO summaryDTO);

    /**
     * 视频对话问答
     * @param chatDTO 对话请求
     * @return AI回复结果
     */
    ChatResult chat(ChatDTO chatDTO);

    ChatResult submitChat(ChatDTO chatDTO);

    SseEmitter connectChatSse(String sid);
}
