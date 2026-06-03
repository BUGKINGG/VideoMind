package com.example.backend.service.serviceImpl;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.example.backend.dto.RegisterDTO;
import com.example.backend.mapper.UserMapper;
import com.example.backend.service.UserService;
import com.example.backend.entity.User;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class UserServiceImpl extends ServiceImpl<UserMapper, User> implements UserService {

    @Autowired
    private BCryptPasswordEncoder bCryptPasswordEncoder;

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
}
