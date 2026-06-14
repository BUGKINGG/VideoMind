package com.example.backend.config;

import org.springframework.amqp.core.Binding;
import org.springframework.amqp.core.BindingBuilder;
import org.springframework.amqp.core.DirectExchange;
import org.springframework.amqp.core.Queue;
import org.springframework.amqp.support.converter.JacksonJsonMessageConverter;
import org.springframework.amqp.support.converter.MessageConverter;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class RabbitConfig {

    @Bean
    public MessageConverter jsonMessageConverter() {
        return new JacksonJsonMessageConverter();
    }

    @Bean
    public Queue parseQueue() {
        return new Queue("videomind.parse.queue", true); // durable=true
    }

    @Bean
    public Queue chatQueue() {
        return new Queue("videomind.chat.queue", true);
    }

    @Bean
    public DirectExchange parseExchange() {
        return new DirectExchange("videomind.parse.exchange");
    }

    @Bean
    public DirectExchange chatExchange() {
        return new DirectExchange("videomind.chat.exchange");
    }

    @Bean
    public Binding parseBinding() {
        return BindingBuilder.bind(parseQueue()).to(parseExchange()).with("parse");
    }

    @Bean
    public Binding chatBinding() {
        return BindingBuilder.bind(chatQueue()).to(chatExchange()).with("chat");
    }
}
