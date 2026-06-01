package com.example.backend.VO;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class LoginVO {
    private String account;
    private String token;
}
