package com.example.backend.vo;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class ChatResult {

    /**
     * 会话ID（流式推送凭证）
     */
    private String sessionId;

    /**
     * 0-处理中 1-完成 2-失败
     */
    private Integer status;

    /**
     * AI回复内容
     */
    private String answer;

    /**
     * 检索到的相关字幕片段
     */
    private List<Map<String, Object>> sources;
}
