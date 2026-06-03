import axios, { Axios } from "axios";
import {useUserStore} from "../stores/user.ts";

const request = axios.create({
    baseURL: import.meta.env.VITE_BASE_URL,
    timeout: 5000
})

request.interceptors.request.use(
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

request.interceptors.response.use(
    (response) => {
        const data = response.data
        if(data.code !== 200){
            alert(data.message || '请求失败')
            return  Promise.reject(new Error(data.message))
        }
        return data
    },
    (error) => {
        if(error.response?.status ===401){
            alert('登录已过期请重新登入')

            // 清空 pinia
            const userStore = useUserStore()
            userStore.logout()

            window.location.href = '\login'
        }
        return Promise.reject(error)
    }
)

export default request