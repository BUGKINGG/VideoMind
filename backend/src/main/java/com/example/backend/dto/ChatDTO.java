package com.example.backend.dto;

import lombok.Data;

@Data
public class ChatDTO {

    /**
     * 对话会话ID
     */
    private Long conversationId;

    /**
     * 用户发送的消息内容
     */
    private String message;
}
