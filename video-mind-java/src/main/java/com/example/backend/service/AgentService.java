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

    ChatResult submitChat(ChatDTO chatDTO);

    SseEmitter connectChatSse(String sid);

    void pushChunkInternal(String sid, String token);

    void pushCatchupInternal(String sid, String catchupJson);

    void pushMetadataInternal(String sid, String title, int subtitleCount, Long conversationId,
                              String bvid, Integer part);

    void pushDoneInternal(String sid, Long videoId, Long conversationId, String title, String summary,
                          int count, String bvid, Integer part);

    void pushErrorInternal(String sid, String message);
}
