package com.example.backend.controller;

import com.example.backend.dto.CookieDTO;
import com.example.backend.dto.LoginDTO;
import com.example.backend.dto.RegisterDTO;
import com.example.backend.entity.Conversation;
import com.example.backend.entity.Message;
import com.example.backend.entity.User;
import com.example.backend.service.UserService;
import com.example.backend.vo.LoginVO;
import com.example.backend.common.JwtUtils;
import com.example.backend.common.Result;
import com.example.backend.vo.MessageVO;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;

import java.util.List;


@RestController
@Slf4j
@RequestMapping("/user")
@Tag(name="用户相关接口")
public class UserController {

    @Autowired
    private JwtUtils jwtUtils;
    @Autowired
    private UserService userService;

    /**
     * 用户登入
     * @param loginDTO
     * @return
     */
    @PostMapping("/login")
    @Operation(summary = "用户登入接口")
    public Result<LoginVO> login(@RequestBody LoginDTO loginDTO){
        log.info("用户登入：{}", loginDTO);

        User user = userService.login(loginDTO);

        if(user == null){
            return Result.error("账户不存在或密码错误！");
        }

        // 得到 token
        String token = jwtUtils.generateToken(user.getId());

        LoginVO loginVO = LoginVO.builder()
            .cookie(user.getCookie())
            .token(token)
            .username(user.getUsername())
            .build();

        return Result.success(loginVO);
    }

    /**
     * 用户注册
     * @param registerDTO
     * @return
     */
    @PostMapping("/register")
    @Operation(summary = "用户注册接口")
    public Result register(@RequestBody RegisterDTO registerDTO){
        boolean bool = userService.register(registerDTO);
        if(!bool){
           return Result.error("账号已存在，请登录");
        }
        return Result.success();
    }

    /**
     * cookie登记
     * @param cookieDTO
     * @return
     */
    @PostMapping("/cookie")
    @Operation(summary = "更新用户cookie")
    public Result updateCookie(@RequestBody CookieDTO cookieDTO){
        String cookie = cookieDTO.getCookie();
        log.info("更新cookie：{}", cookie);
        userService.updateCookie(cookie);
        return Result.success();
    }

    @GetMapping("/conversation/list")
    @Operation(summary = "获取用户历史记录")
    public Result<List<MessageVO>> conversationList() {
        log.info("获取历史记录");
        List<MessageVO> list = userService.getList();
        return Result.success(list);
    }

    @GetMapping("/conversation/{id}")
    public Result<MessageVO> showMessage(@PathVariable Long id){
        MessageVO messageVO = userService.getMessages(id);
        return Result.success(messageVO);
    }
}
