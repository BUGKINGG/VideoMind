package com.example.backend.vo;

import lombok.Data;

@Data
public class SummaryResult {
    private Long videoId;

    private String title;

    private String summary;
    // 1完成 2失败

    private Integer status;

    private Integer subtitleCount;

    private String sessionId;
}
