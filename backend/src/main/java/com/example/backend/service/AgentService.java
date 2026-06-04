package com.example.backend.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.entity.Video;

public interface AgentService extends IService<Video> {

    void summary(SummaryDTO summaryDTO);
}
