import { createRouter, createWebHistory} from "vue-router";
import Login from "../views/Login.vue";
import Home from "../views/Home.vue";
import {useUserStore} from "../stores/user.ts";

const routes = [
    { path: "/", component: Login },
    { path: "/login", component: Login },
    { path: '/home', component: Home}
]

const router = createRouter({
    history: createWebHistory(),
    routes
})

// 路由管家，防止通过直接输入网址的方式，跳过登入到达/home界面
router.beforeEach((to) => {
    const userStore = useUserStore()
    const whiteList = ['/login', '/register']

    if(whiteList.includes(to.path)){ return true}
    if(!userStore.token) return '/login'
    return true
})

export default router
