<script setup lang="ts">
  import {ref} from "vue";
  import {useRouter} from "vue-router";
  import request from "../utils/request";

  const account = ref<string>('');
  const password = ref<string>('');

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

      localStorage.setItem('token', data.data.token)
      console.log("登入成功", data);
      await router.push('/home')

    }catch (error){
      console.error(error);
    }
  }

</script>

<template>
  <div class="container">
    <div class="card">
      <h2 class="title">登录账号</h2>

      <div class="form">
        <div class="form-row">
          <label>账号：</label>
          <input class="input" placeholder="请输入账号" v-model="account">
        </div>

        <div class="form-row">
          <label>密码：</label>
          <input type="password" class="input" placeholder="请输入密码" v-model="password">
        </div>

        <button class="btn" @click="handleLogin">登入</button>
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
  gap: 8px;
}

.form-row label {
  width: 60px;
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
</style>