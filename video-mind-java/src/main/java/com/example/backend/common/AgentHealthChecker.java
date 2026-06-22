package com.example.backend.common;

import lombok.Getter;
import org.springframework.beans.factory.annotation.Value;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatusCode;
import org.springframework.scheduling.annotation.EnableScheduling;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.concurrent.atomic.AtomicInteger;

@Component
@EnableScheduling
@Slf4j
public class AgentHealthChecker {
    private final WebClient healthClient;
    @Getter
    private volatile boolean healthy = true;
    private final AtomicInteger failCount = new AtomicInteger(0);
    private final AtomicInteger successCount = new AtomicInteger(0);
    private static final int MAX_FAIL = 3;
    private static final int RECOVERY_THRESHOLD = 2;
    private static final Duration TIMEOUT = Duration.ofSeconds(3);

    public AgentHealthChecker(@Value("${agent.service.url}") String url) {
        this.healthClient = WebClient.builder().baseUrl(url).build();
    }

    // 10s 一次
    @Scheduled(fixedRate = 10_000)
    public void check() {
        try{
            healthClient.get()
                .uri("/api/health")
                .retrieve()
                .onStatus(HttpStatusCode::isError, resp -> {
                    Mono.error(new RuntimeException("Agent返回非200"));
                })
                .bodyToMono(String.class)
                .timeout(TIMEOUT)
                .block();

            // 探测成功
            failCount.set(0);
            if (!healthy) {
                if (successCount.incrementAndGet() >= RECOVERY_THRESHOLD) {
                    healthy = true;
                    successCount.set(0);
                    log.info("Agent服务恢复可用");
                }
            }
        }catch (Exception e){
            successCount.set(0);
            int cnt = failCount.incrementAndGet();
            log.warn("Agent健康检查失败 ({}/{}): {}", cnt, MAX_FAIL, e.getMessage());
            if (cnt >= MAX_FAIL && healthy) {
                healthy = false;
                log.error("Agent服务被标记为DOWN");
            }
        }
    }

}
