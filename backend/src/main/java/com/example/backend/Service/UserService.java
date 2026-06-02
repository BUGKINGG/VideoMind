package com.example.backend.Service;


import com.example.backend.DTO.RegisterDTO;

public interface UserService {

    boolean register(RegisterDTO registerDTO);
}
