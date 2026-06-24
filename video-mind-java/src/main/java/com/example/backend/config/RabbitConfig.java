package com.example.backend.config;

import com.example.backend.common.VideoCorrelationData;
import com.example.backend.entity.Video;
import com.example.backend.mapper.VideoMapper;
import lombok.extern.slf4j.Slf4j;
import org.springframework.amqp.core.*;
import org.springframework.amqp.support.converter.JacksonJsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.boot.amqp.autoconfigure.RabbitTemplateCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.util.HashMap;
import java.util.Map;

@Configuration
@Slf4j
public class RabbitConfig {

    @Bean
    public RabbitTemplateCustomizer rabbitTemplateCustomizer(VideoMapper videoMapper) {
        return template -> {
            template.setConfirmCallback((correlationData, ack, cause) -> {
                String id = correlationData != null ? correlationData.getId() : "unknown";
                if (ack) {
                    log.info("[MQ Confirm] 消息成功到达交换机, id={}", id);
                } else {
                    log.error("[MQ Confirm] 消息到达交换机失败, id={}, cause={}", id, cause);

                    if (correlationData instanceof VideoCorrelationData) {
                        Long videoId = ((VideoCorrelationData) correlationData).getVideoId();
                        try {
                            Video fail = new Video();
                            fail.setId(videoId);
                            fail.setStatus(2);
                            fail.setSummary("MQ发送失败: " + cause);
                            videoMapper.updateById(fail);
                            log.info("[MQ Confirm] 已标记视频失败状态, videoId={}", videoId);
                        } catch (Exception e) {
                            log.error("[MQ Confirm] 更新视频失败状态异常, videoId={}", videoId, e);
                        }
                    }
                }
            });

            template.setReturnsCallback(returned -> {
                log.error("[MQ Return] 消息路由失败: exchange={}, routingKey={}, replyCode={}, replyText={}",
                    returned.getExchange(),
                    returned.getRoutingKey(),
                    returned.getReplyCode(),
                    returned.getReplyText());
            });

            template.setMandatory(true);
        };
    }

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new JacksonJsonMessageConverter();
    }

    // ========== 解析任务队列（带死信） ==========
    @Bean
    public Queue parseQueue() {
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", "videomind.parse.dlx");
        args.put("x-dead-letter-routing-key", "parse.failed");
        return new Queue("videomind.parse.queue", true, false, false, args);
    }

    @Bean
    public Queue parseDlq() {
        return new Queue("videomind.parse.dlq", true);
    }

    @Bean
    public DirectExchange parseExchange() {
        return new DirectExchange("videomind.parse.exchange");
    }

    @Bean
    public DirectExchange parseDlx() {
        return new DirectExchange("videomind.parse.dlx");
    }

    @Bean
    public Binding parseBinding() {
        return BindingBuilder.bind(parseQueue()).to(parseExchange()).with("parse");
    }

    @Bean
    public Binding parseDlqBinding() {
        return BindingBuilder.bind(parseDlq()).to(parseDlx()).with("parse.failed");
    }

    // ========== 聊天任务队列（带死信） ==========
    @Bean
    public Queue chatQueue() {
        Map<String, Object> args = new HashMap<>();
        args.put("x-dead-letter-exchange", "videomind.chat.dlx");
        args.put("x-dead-letter-routing-key", "chat.failed");
        return new Queue("videomind.chat.queue", true, false, false, args);
    }

    @Bean
    public Queue chatDlq() {
        return new Queue("videomind.chat.dlq", true);
    }

    @Bean
    public DirectExchange chatExchange() {
        return new DirectExchange("videomind.chat.exchange");
    }

    @Bean
    public DirectExchange chatDlx() {
        return new DirectExchange("videomind.chat.dlx");
    }

    @Bean
    public Binding chatBinding() {
        return BindingBuilder.bind(chatQueue()).to(chatExchange()).with("chat");
    }

    @Bean
    public Binding chatDlqBinding() {
        return BindingBuilder.bind(chatDlq()).to(chatDlx()).with("chat.failed");
    }
}
