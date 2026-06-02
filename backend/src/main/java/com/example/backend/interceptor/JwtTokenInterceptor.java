package com.example.backend.interceptor;

import com.example.backend.common.JwtUtils;
import com.example.backend.common.Result;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;
import tools.jackson.databind.ObjectMapper;

@Component
public class JwtTokenInterceptor implements HandlerInterceptor {

    @Autowired
    private JwtUtils jwtUtils;

    // 拦截器方法
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String token = request.getHeader("token");

        String uri = request.getRequestURI();
        // 放行登入接口
        if(uri.contains("/login")){
            return true;
        }

        // 没有 token 直接401
        if(token == null || token.isEmpty()){
            writeError(response, 401, "未登入，请先登入");
            return false;
        }

        try{
            // parseToken 方法可以解析 token 是否合规，如果不合规则抛出异常
            jwtUtils.parseToken(token);
            return true;
        } catch (Exception e){
            writeError(response, 401, "登入已过期，请重新登入");
            return false;
        }
    }

    // 辅助方法，往response里写JSON
    private void writeError(HttpServletResponse response, int code, String msg) throws Exception{
        response.setStatus(code);
        response.setContentType("application/json;charset=UTF-8");
        Result<Object> result = Result.error(msg);
        response.getWriter().write(new ObjectMapper().writeValueAsString(result));
    }
}
