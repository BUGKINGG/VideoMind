package com.example.backend.entity;

import lombok.Data;

import java.io.Serializable;

@Data
public class ChatTask implements Serializable {
    private String sid;
    private Long conversationId;
    private Long userId;
    private String message;
}
