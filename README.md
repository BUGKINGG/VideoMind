# 项目结构

```text
VideoMind/
├── backend/                              # Java + Maven 后端
│   ├── src/
│   │   └── main/
│   │       ├── java/com/example/backend/
│   │       │   ├── common/
│   │       │   │   ├── JwtUtils.java     # JWT 令牌生成/解析工具
│   │       │   │   └── Result.java       # 统一 JSON 响应封装
│   │       │   ├── Config/
│   │       │   │   └── WebMvcConfigure.java  # MVC 配置、拦截器注册
│   │       │   ├── Controller/
│   │       │   │   └── LoginController.java  # 登录/认证接口
│   │       │   ├── DTO/
│   │       │   │   ├── LoginDTO.java     # 登录请求参数对象
│   │       │   │   └── TextDTO.java      # 文本传输对象
│   │       │   ├── interceptor/
│   │       │   │   └── JwtTokenInterceptor.java  # Token 校验拦截器
│   │       │   ├── VO/                   # 响应视图对象（目录预留）
|   |       |   |    └──LoginVO           # LoginVO对象
│   │       │   └── Application.java      # Spring Boot 启动类
│   │       └── resources/
│   │           └── application.yml       # 数据源、JWT 密钥等配置
│   ├── pom.xml                           # Maven 依赖管理
├── frontend/                             # Vite + Vue3 前端
│   ├── src/
│   │   ├── assets/
│   │   │   ├── main.css                  # 全局样式
│   │   ├── components/                   # 公共 Vue 组件
│   │   ├── router/
│   │   │   └── index.ts                  # Vue Router 路由配置
│   │   ├── utils/
│   │   │   └── request.ts                # Axios 请求封装（放置 jwt 令牌）
│   │   ├── views/                        # 页面级组件
│   │   ├── App.vue                       # 根组件
│   │   ├── main.ts                       # 应用入口（挂载、全局配置）
│   │   └── style.css
│   ├── .env                              # 环境变量（API 基地址等）
│   ├── index.html                        # 单页入口 HTML
```
