package com.example.backend.common;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;
import java.util.UUID;

@Slf4j
@Component
@RequiredArgsConstructor
public class RedisLockUtil {

    private final StringRedisTemplate redisTemplate;

    /**
     * 尝试加锁
     * @param lockkey
     * @param expire
     * @return
     */
    public String tryLock(String lockkey, Duration expire) {
        String lockValue = UUID.randomUUID().toString();
        // 没锁就返回True，否则False
        Boolean success = redisTemplate.opsForValue().setIfAbsent(lockkey, lockValue, expire);
        if(Boolean.TRUE.equals(success)){
            return lockValue;
        }
        return null;
    }


    /**
     * 释放锁（安全释放：只有持有锁的人才能释放）
     */
    public void unlock(String lockKey, String lockValue) {
        String currentValue = redisTemplate.opsForValue().get(lockKey);
        if (lockValue.equals(currentValue)) {
            redisTemplate.delete(lockKey);
        } else {
            log.warn("锁已被他人持有或已过期，跳过释放: {}", lockKey);
        }
    }
}
