package com.example.backend.vo;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class LoginVO {
    private Long userId;
    private String account;
    private String token;
    private String username;
    private String cookie;
}
