package com.example.backend.Controller;

import com.example.backend.DTO.LoginDTO;
import com.example.backend.VO.LoginVO;
import com.example.backend.common.JwtUtils;
import com.example.backend.common.Result;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;


@RestController
@Slf4j
@RequestMapping("/api")
@Tag(name="登入相关接口")
public class LoginController {

    @Autowired
    private JwtUtils jwtUtils;

    /**
     * 用户登入
     * @param loginDTO
     * @return
     */
    @PostMapping("/login")
    @Operation(summary = "用户登入接口")
    public Result<LoginVO> login(@RequestBody LoginDTO loginDTO){
        log.info("用户登入：{}", loginDTO);

        // TODO: 改成调用数据库进行账户查询
        String defaultAccount = "admin";
        String defaultPassword = "123456";
        if(!defaultAccount.equals(loginDTO.getAccount()) || !defaultPassword.equals(loginDTO.getPassword())){
            return Result.error("用户或密码错误");
        }

        // 得到 token
        String token = jwtUtils.generateToken(loginDTO.getAccount());

        LoginVO loginVO = LoginVO.builder()
            .account(loginDTO.getAccount())
            .token(token)
            .build();

        return Result.success(loginVO);
    }
}
