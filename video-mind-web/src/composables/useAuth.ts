import { useRouter } from 'vue-router'
import request from '../utils/request'
import { useUserStore } from '../stores/user'

export interface LoginPayload {
  account: string
  password: string
}

export interface RegisterPayload {
  username: string
  account: string
  password: string
  passwordRepeat: string
}

export function useAuth() {
  const router = useRouter()
  const userStore = useUserStore()

  const isPhone = (v: string) => /^\d{11}$/.test(v)
  const isPassword = (v: string) =>
    /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{7,}$/.test(v)

  /**
   * Login — returns an error message string on failure, or null on success
   */
  async function handleLogin(payload: LoginPayload): Promise<string | null> {
    if (!payload.account || !payload.password) {
      return '请输入账号和密码'
    }

    try {
      const data = await request.post('/user/login', {
        account: payload.account,
        password: payload.password,
      })

      userStore.setUserInfo({
        token: data.data.token,
        username: data.data.username,
        cookie: data.data.cookie || '',
      })
      console.log('登入成功', data)
      await router.push('/home')
      return null
    } catch (error) {
      console.error(error)
      return '登录失败，请检查账号和密码'
    }
  }

  /**
   * Register — returns an error message string on failure, or null on success.
   * On success the caller should switch back to the login view.
   */
  async function handleRegister(payload: RegisterPayload): Promise<string | null> {
    if (!payload.account) return '请输入手机号'
    if (!isPhone(payload.account)) return '手机号必须为11位数字'
    if (!payload.password) return '请输入密码'
    if (!isPassword(payload.password)) return '密码至少7位，且必须同时包含字母和数字'
    if (payload.password !== payload.passwordRepeat) return '两次输入的密码不一致'

    const res = await request.post('/user/register', {
      username: payload.username,
      account: payload.account,
      password: payload.password,
    })

    if (res.code === 500) return '账户已存在'
    if (res.code === 200) return null

    return '注册失败，请稍后重试'
  }

  return { handleLogin, handleRegister }
}
