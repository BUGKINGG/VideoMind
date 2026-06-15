package com.example.backend.common;

import lombok.Getter;
import org.springframework.amqp.rabbit.connection.CorrelationData;

@Getter
public class VideoCorrelationData extends CorrelationData {
    private final Long videoId;

    public VideoCorrelationData(String id, Long videoId) {
        super(id);
        this.videoId = videoId;
    }
}
