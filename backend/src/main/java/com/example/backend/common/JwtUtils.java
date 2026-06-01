package com.example.backend.common;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

@Component
public class JwtUtils {
    // 注意 SECRET 长度一定要为 32 个字符，否则报错
    // 这里的 secret 由 配置文件全局引用
    @Value("${jwt.secret}")
    private String secret;

    private SecretKey key;

    // 初始化后执行，类似构造函数
    @PostConstruct
    public void init(){
        this.key = Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    private static final long EXPIRATION = 72000;

    public String generateToken(String account){
        return Jwts.builder()
            .subject(account)
            .issuedAt(new Date())
            .expiration(new Date(System.currentTimeMillis() + EXPIRATION))
            .signWith(this.key)
            .compact();
    }

    public String parseToken(String token){
        return Jwts.parser()
            .verifyWith(this.key)
            .build()
            .parseSignedClaims(token)
            .getPayload()
            .getSubject();
    }
}
