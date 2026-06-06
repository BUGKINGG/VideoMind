package com.example.backend.service.serviceImpl;

import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.backend.common.BaseContext;
import com.example.backend.common.BilibiliUrlUtils;
import com.example.backend.dto.SummaryDTO;
import com.example.backend.entity.Subtitle;
import com.example.backend.entity.Video;
import com.example.backend.mapper.SubtitleMapper;
import com.example.backend.mapper.VideoMapper;
import com.example.backend.service.AgentService;
import com.example.backend.vo.SummaryResult;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.client.RestTemplate;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;


@Service
public class AgentServiceImpl extends ServiceImpl<VideoMapper, Video> implements AgentService {

    @Autowired
    private VideoMapper videoMapper;
    @Autowired
    private RestTemplate restTemplate;
    @Autowired
    private SubtitleMapper subtitleMapper;

    @Transactional
    @Override
    public SummaryResult summary(SummaryDTO summaryDTO) {
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
        if (exist != null) {
            SummaryResult summaryResult = new SummaryResult();
            summaryResult.setSummary(exist.getSummary());
            summaryResult.setTitle(exist.getTitle());
            summaryResult.setVideoId(exist.getId());
            summaryResult.setStatus(1);
            summaryResult.setSubtitleCount(exist.getSubtitleCount());
            return summaryResult;
        }

        // 如果没有，则给python视频解析服务传递url和cookie
        Video video = new Video();
        video.setCreateAt(LocalDateTime.now());
        video.setPart(part);
        video.setUrl(baseUrl);
        video.setUserId(userId);
        video.setStatus(0);
        this.save(video);
        Long videoId = video.getId();

        try {
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
            if (result == null || !Integer.valueOf(200).equals(result.get("code"))) {
                throw new RuntimeException("字幕解析失败: " + (result != null ? result.get("message") : "无响应"));
            }

            String title = (String) result.get("title");
            List<Map<String, Object>> subtitles = (List<Map<String, Object>>) result.get("subtitles");

            // 得到JSON数据的返回，解析每条subtitle，把完整信息插入数据表
            StringBuilder fullText = new StringBuilder();
            int count = 0;

            List<Subtitle> subList = new ArrayList<>();

            for (Map<String, Object> track : subtitles) {
                List<Map<String, Object>> body = (List<Map<String, Object>>) track.get("body");
                if (body == null) continue;
                for (Map<String, Object> item : body) {
                    String content = (String) item.get("content");
                    Double start = ((Number) item.get("start")).doubleValue();
                    Double end = ((Number) item.get("end")).doubleValue();

                    Subtitle sub = new Subtitle();
                    sub.setVideoId(videoId);
                    sub.setContent(content);
                    sub.setStartAt(start);
                    sub.setEndAt(end);
                    subList.add(sub);

                    fullText.append(content).append(" ");
                    count++;
                }
            }

            // 一次性批量入库
            if (!subList.isEmpty()) {
                subtitleMapper.insertBatch(subList);
            }

            // TODO:调用agent，先调用视频解析agent对字幕内容进行总结，然后把字幕存入Qdrant；接着返回总结内容
            String textToSummarize = fullText.length() > 3000
                ? fullText.substring(0, 3000)
                : fullText.toString();

            Map<String, String> summarizeReq = new HashMap<>();
            summarizeReq.put("text", textToSummarize);
            summarizeReq.put("title", title != null ? title : "");

            ResponseEntity<Map> summarizeResp = restTemplate.postForEntity(
                "http://localhost:8001/summarize",
                summarizeReq,
                Map.class
            );

            Map summarizeResult = summarizeResp.getBody();
            String summary = (summarizeResult != null && summarizeResult.get("summary") != null)
                ? (String) summarizeResult.get("summary")
                : "总结生成失败";

            // 更新 video 为完成状态
            video.setTitle(title);
            video.setSummary(summary);
            video.setStatus(1);
            video.setSubtitleCount(count);
            this.updateById(video);

            SummaryResult res = new SummaryResult();
            res.setVideoId(videoId);
            res.setTitle(title);
            res.setSummary(summary);
            res.setStatus(1);
            res.setSubtitleCount(count);
            return res;

        } catch (Exception e) {
            // 标记失败，避免前端无限等待
            video.setStatus(2);
            video.setSummary("处理失败: " + e.getMessage());
            this.updateById(video);

            SummaryResult res = new SummaryResult();
            res.setVideoId(videoId);
            res.setStatus(2);
            res.setSummary(video.getSummary());
            res.setSubtitleCount(0);
            return res;
        }
    }
}
