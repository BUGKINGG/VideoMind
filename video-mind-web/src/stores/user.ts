/**
 * 持久化层，把关键的属性放在这里，可供全局组件拿到
 */
import {defineStore} from "pinia";
import { ref, computed} from "vue";

export const useUserStore = defineStore('user', () => {
    const token = ref('')
    const username = ref('')
    const cookie = ref('')
    const isLoggedIn = ref(false)

    const hasCookie = computed(() => {
        !!cookie.value
    })

    function setUserInfo(data: {
        token: string;
        username: string;
        cookie?: string
    }){
        token.value = data.token
        username.value = data.username
        cookie.value = data.cookie || ''
        isLoggedIn.value = true;
    }

    function updateCookie(newCookie: string) {
        cookie.value = newCookie
    }

    function updateUsername(newUsername: string) {
        username.value = newUsername
    }

    function logout() {
        token.value = ''
        username.value = ''
        cookie.value = ''
        isLoggedIn.value = false
    }

    return {
        token,
        username,
        cookie,
        isLoggedIn,
        hasCookie,
        setUserInfo,
        updateCookie,
        updateUsername,
        logout
    }
}, {
    // 关键：持久化到 localStorage，刷新不丢
    persist: {
        key: 'videomind-user',
        pick: ['token', 'username', 'cookie', 'isLoggedIn']
    }
})