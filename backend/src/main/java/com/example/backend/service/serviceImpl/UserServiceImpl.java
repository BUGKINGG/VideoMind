package com.example.backend.service.serviceImpl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.baomidou.mybatisplus.core.toolkit.Wrappers;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.backend.common.BaseContext;
import com.example.backend.dto.LoginDTO;
import com.example.backend.dto.RegisterDTO;
import com.example.backend.entity.Conversation;
import com.example.backend.mapper.ConversationMapper;
import com.example.backend.mapper.UserMapper;
import com.example.backend.service.UserService;
import com.example.backend.entity.User;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.List;

@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {

    @Autowired
    private BCryptPasswordEncoder bCryptPasswordEncoder;
    @Autowired
    private UserMapper userMapper;
    @Autowired
    private ConversationMapper conversationMapper;

    @Override
    public boolean register(RegisterDTO registerDTO) {
        QueryWrapper<User> wrapper = new QueryWrapper<>();

        // 判断手机号是否已经被注册
        // 利用mp在数据库中查询
        wrapper.eq("phone", registerDTO.getAccount());

        // count为符合记录的数量
        long count = this.count(wrapper);

        // 存在手机号，则返回false
        if(count > 0){
            return false;
        }

        User user = new User();
        BeanUtils.copyProperties(registerDTO, user);

        user.setPasswordHash(bCryptPasswordEncoder.encode(registerDTO.getPassword()));

        user.setCookie(null);
        user.setPhone(registerDTO.getAccount());
        user.setCreatedAt(LocalDateTime.now());
        user.setUpdatedAt(LocalDateTime.now());

        this.save(user);
        return true;
    }

    public User login(LoginDTO loginDTO){
        User tempUser = userMapper.selectOne(
            Wrappers.<User>lambdaQuery()
                .eq(User::getPhone, loginDTO.getAccount())
        );
        User user = new User();

        if(tempUser == null){
            return null;
        }

        boolean matches = bCryptPasswordEncoder.matches(loginDTO.getPassword(), tempUser.getPasswordHash());

        if(!matches){
            return null;
        }

        return tempUser;
    }

    public void updateCookie(String cookie){
        Long userId = BaseContext.getCurrentId();

        LambdaUpdateWrapper<User> wrapper = new LambdaUpdateWrapper<>();
        wrapper.eq(User::getId, userId)
            .set(User::getCookie, cookie);

        userMapper.update(null, wrapper);
    }

    @Override
    public List<Conversation> getList(){
        Long userId = BaseContext.getCurrentId();
        List<Conversation> list = conversationMapper.selectList(
            Wrappers.<Conversation>lambdaQuery()
                .eq(Conversation::getUserId, userId)
                .eq(Conversation::getStatus, 1)
                .orderByDesc(Conversation::getUpdatedAt)
        );
        return list;
    }
}
