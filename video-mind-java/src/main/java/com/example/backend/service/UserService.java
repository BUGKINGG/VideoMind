package com.example.backend.service;


import com.baomidou.mybatisplus.extension.service.IService;
import com.example.backend.dto.LoginDTO;
import com.example.backend.dto.RegisterDTO;
import com.example.backend.entity.Conversation;
import com.example.backend.entity.User;
import com.example.backend.vo.MessageVO;

import java.util.List;

public interface UserService extends IService<User> {

    /**
     * 用户注册功能
     * @param registerDTO
     * @return
     */
    boolean register(RegisterDTO registerDTO);

    /**
     * 用户登入功能
     * @param loginDTO
     * @return
     */
    User login(LoginDTO loginDTO);

    /**
     * 更新用户的cookie
     * @param cookie
     */
    void updateCookie(String cookie);

    /**
     * 获得用户的历史记录列表
     * @return
     */
    List<MessageVO> getList();

    /**
     * 获得具体的历史对话记录
     * @param id
     * @return
     */
    MessageVO getMessages(Long id);
}
