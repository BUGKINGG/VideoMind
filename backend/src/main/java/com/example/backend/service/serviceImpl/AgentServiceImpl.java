package com.example.backend.service.serviceImpl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.backend.common.BaseContext;
import com.example.backend.common.BilibiliUrlUtils;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.entity.Video;
import com.example.backend.mapper.VideoMapper;
import com.example.backend.service.AgentService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.List;
import java.util.Map;


@Service
public class AgentServiceImpl extends ServiceImpl<VideoMapper, Video> implements AgentService {

    @Autowired
    private VideoMapper videoMapper;
    @Autowired
    private RestTemplate restTemplate;

    @Transactional
    public void summary (SummaryDTO summaryDTO){
        // TODO：之后实现总结内容返回前端功能
        // dto里存放着url和cookie
        String rawUrl = summaryDTO.getUrl();
        String baseUrl = BilibiliUrlUtils.extractBaseUrl(rawUrl);
        String cookie = summaryDTO.getCookie();
        Integer part = BilibiliUrlUtils.extractPart(rawUrl);
        Long userId = BaseContext.getCurrentId();

        // 先查询 video 数据表中有没有相同的url以及part，如果有则直接读取summary内容并且返回
        // 要求同一baseUrl，同一part，status为1
        Video exist = videoMapper.selectOne(
            Wrappers.<Video>lambdaQuery()
                .eq(Video::getUrl, baseUrl)
                .eq(Video::getPart, part)
                .eq(Video::getStatus, 1)
        );

        // 如果有，那么直接返回summary
        if(exist != null){
            // TODO: 返回summary
            return ;
        }

        // 如果没有，则给python视频解析服务传递url和cookie
        Video video = new Video();
        video.setCreateAt(LocalDateTime.now());
        video.setPart(part);
        video.setUrl(baseUrl);
        video.setUserId(userId);
        video.setStatus(0);
        this.save(video);

        //调用 视频解析 的接口
        String pythonUrl = "http://localhost:8001/parse";

        if (cookie != null && !cookie.isEmpty() && !cookie.contains("=")) {
            cookie = "SESSDATA=" + cookie;
        }

        // 构造请求体
        Map<String, String> requestBody = new HashMap<>();
        requestBody.put("url", baseUrl);
        requestBody.put("cookie", cookie);
        requestBody.put("part", part.toString());

        // 发送 POST
        ResponseEntity<Map> response = restTemplate.postForEntity(
            pythonUrl,
            requestBody,
            Map.class
        );

        // 取结果
        Map result = response.getBody();
        List<Map<String, Object>> subtitles = (List<Map<String, Object>>) result.get("subtitles");

        // 得到JSON数据的返回，解析每条subtitle，把完整信息插入数据表

        // TODO:调用agent，先调用视频解析agent对字幕内容进行总结，然后把字幕存入Qdrant；接着返回总结内容
    }
}
