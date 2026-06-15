package com.example.backend.common;

import lombok.Data;

// 返回给前端
@Data
public class Result<T> {
    private Integer code;
    private String message;
    private T data;

    public static <T> Result<T> success(T data){
        Result<T> result = new Result<>();
        result.code = 200;
        result.message = "success";
        result.data = data;
        return result;
    }

    public static <T> Result<T> success(){
        return success(null);
    }

    public static <T> Result<T> error(String message){
        Result<T> result = new Result<>();
        result.code = 500;
        result.message = message;
        return result;
    }

    public static <T> Result<T> error(Integer code, String message) {
        Result<T> result = new Result<>();
        result.code = code;
        result.message = message;
        return result;
    }
}
