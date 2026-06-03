package com.example.backend.vo;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class LoginVO {
    private String account;
    private String token;
}
