/**
 * 拦截器类，请求和回复都要先经过这里才能发出去
 */
import axios, {type AxiosInstance, type AxiosRequestConfig, type AxiosResponse} from "axios";
import {useUserStore} from "../stores/user.ts";

export interface ApiResponse<T = any> {
    code: number
    data: T
    message?: string
}

const service: AxiosInstance = axios.create({
    baseURL: "/",
    timeout: 5000
})

/**
 * 给每个请求都设置配置，比如从pinia中拿到token放到header中
 */
service.interceptors.request.use(
    (config) =>{
        const userStore = useUserStore()
        if (userStore.token){
            config.headers['token'] = userStore.token
        }
        return config
    },
    (error) => {
        return Promise.reject(error)
    }
)

/**
 * 解析每个回复，得到回复时先经过这里，比如把token存储之类的
 */
service.interceptors.response.use(
    (response: AxiosResponse) => {
        const data = response.data as ApiResponse
        if(data.code !== 200){
            alert(data.message || '请求失败')
            return  Promise.reject(new Error(data.message))
        }
        return response
    },
    (error) => {
        if(error.response?.status ===401){
            alert('登录已过期请重新登入')

            // 清空 pinia
            const userStore = useUserStore()
            userStore.logout()

            // 回到login界面
            window.location.href = '/login'
        }
        return Promise.reject(error)
    }
)

const request = {
    async get<T = any>(url: string, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
        const res = await service.get(url, config)
        return res.data as ApiResponse<T>
    },
    async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResponse<T>> {
        const res = await service.post(url, data, config)
        return res.data as ApiResponse<T>
    }
}

export default request