package com.example.backend.service;


import com.baomidou.mybatisplus.extension.service.IService;
import com.example.backend.dto.LoginDTO;
import com.example.backend.dto.RegisterDTO;
import com.example.backend.entity.User;

public interface UserService extends IService<User> {

    boolean register(RegisterDTO registerDTO);

    User login(LoginDTO loginDTO);

    void updateCookie(String cookie);
}
