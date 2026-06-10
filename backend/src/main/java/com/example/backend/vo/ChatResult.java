package com.example.backend.vo;

import lombok.Data;

import java.util.List;
import java.util.Map;

@Data
public class ChatResult {

    /**
     * AI回复内容
     */
    private String answer;

    /**
     * 检索到的相关字幕片段
     */
    private List<Map<String, Object>> sources;
}
