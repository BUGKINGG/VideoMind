package com.example.backend.Service.ServiceImpl;

import com.example.backend.DTO.RegisterDTO;
import com.example.backend.Service.UserService;
import org.springframework.stereotype.Service;

@Service
public class UserServiceImpl implements UserService {

    @Override
    public boolean register(RegisterDTO registerDTO) {
        return false;
    }
}
