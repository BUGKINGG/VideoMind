package com.example.backend.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.entity.Video;
import com.example.backend.vo.SummaryResult;

public interface AgentService extends IService<Video> {

    SummaryResult summary(SummaryDTO summaryDTO);
}
