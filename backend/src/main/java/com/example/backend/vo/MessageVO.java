package com.example.backend.vo;

import com.example.backend.entity.Message;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
public class MessageVO {
    private Long id;
    private String title;
    private Integer status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Long videoId;
    private String url;
    private Integer part;
    private Long subtitleCount;
    private List<Message> messages;

}
