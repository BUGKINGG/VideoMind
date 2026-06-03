<script setup lang="ts">
  import {ref} from "vue";
  import {useRouter} from "vue-router";
  import request from "../utils/request";
  import { useUserStore } from "../stores/user.ts";

  const account = ref<string>('');
  const password = ref<string>('');
  const currentView = ref('');
  const password_register = ref('')
  const password_repeat = ref('')
  const account_register = ref('')
  const username_register = ref('')
  currentView.value = 'login'

  const userStore = useUserStore()

  const router = useRouter();

  const handleLogin = async() => {
    if(!account.value || !password.value){
      alert("请输入账号和密码");
      return;
    }

    try{
      const data = await request.post('/api/login', {
        account: account.value,
        password: password.value
      })

      userStore.setUserInfo({
        token: data.data.token,
        username: data.data.username,
        cookie: data.data.cookie || ''
      })
      console.log("登入成功", data);
      await router.push('/home')

    }catch (error){
      console.error(error);
    }
  }

  function registerView(){
    currentView.value = 'register'
  }


  // 校验规则
  const isPhone = (v: string) => /^\d{11}$/.test(v)
  const isPassword = (v: string) => /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d]{7,}$/.test(v)

  async function register() {
    // 先清空旧提示

    // 1. 校验手机号
    if (!account_register.value) {
      alert("请输入手机号")
      return
    }
    if (!isPhone(account_register.value)) {
      alert('手机号必须为11位数字')
      return
    }

    // 2. 校验密码
    if (!password_register.value) {
      alert("请输入密码")
      return
    }
    if (!isPassword(password_register.value)) {
      alert("密码至少7位，且必须同时包含字母和数字")
      return
    }

    // 3. 校验两次密码是否一致
    if (password_register.value !== password_repeat.value) {
      alert("两次输入的密码不一")
      return
    }

    // 全部通过，执行注册请求
    const res = await request.post("/api/register", {
      username: username_register.value,
      account: account_register.value,
      password: password_register.value
    })

    if(res.code === 500){
      alert("账户已存在")
      return;
    }

    if(res.code === 200){
      alert("注册成功！")
      currentView.value = 'login'
      return;
    }
  }

  function turnBack() {
    currentView.value='login'
  }

</script>

<template>
  <div class="container">
    <div v-if="currentView === 'login'" class="card">
      <h2 class="title">登录账号</h2>

      <div class="form">
        <div class="form-row">
          <label>账号：</label>
          <input class="input" placeholder="请输入账号" v-model="account" @keyup.enter="handleLogin">
        </div>

        <div class="form-row">
          <label>密码：</label>
          <input type="password" class="input" placeholder="请输入密码" v-model="password" @keyup.enter="handleLogin">
        </div>

        <button class="btn" @click="handleLogin" >登入</button>
        <button class="btn btn-register" @click="registerView">注册</button>
      </div>
    </div>

    <div v-else-if="currentView === 'register'" class="card">
      <h2 class="title">注册账号</h2>
      <div class="form">

        <div class="form-row">
          <label>用户名：</label>
          <input class="input" placeholder="用户名" v-model="username_register">
        </div>

        <div class="form-row">
          <label>账号：</label>
          <input class="input" placeholder="请输入手机号注册" v-model="account_register">
        </div>

        <div class="form-row">
          <label>密码：</label>
          <input type="password" class="input" placeholder="请输入密码，要求大于6位" v-model="password_register">
        </div>

        <div class="form-row">
          <label></label>
          <input type="password" class="input" placeholder="请再次输入密码" v-model="password_repeat">
        </div>

        <button class="btn" @click="register">注册</button>
        <button class="btn btn-register" @click="turnBack">返回</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.container {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: #f5f5f5;
}

.card {
  background: white;
  padding: 40px;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  width: 400px;
}

.title {
  text-align: center;
  margin-bottom: 30px;
  color: #333;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.form-row label {
  width: 80px;
  flex-shrink: 0;
  color: #555;
}

.input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 6px;
  outline: none;
}

.input:focus {
  border-color: #667eea;
}

.btn {
  margin-top: 10px;
  padding: 12px;
  background: #667eea;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:hover {
  background: #5568d3;
}

.btn-register {
  background: rgba(255, 165, 0, 0.8);
}

.btn-register:hover {
  background: orange;
}
</style>