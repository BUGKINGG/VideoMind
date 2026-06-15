package com.example.backend.entity;

import lombok.Data;

import java.io.Serializable;

@Data
public class ParseTask implements Serializable {
    private Long videoId;
    private String baseUrl;
    private Integer part;
    private Long userId;
    private String cookie;
    private String sid;
}
