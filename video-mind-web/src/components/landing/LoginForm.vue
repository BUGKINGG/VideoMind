<template>
  <div class="form-card">
    <h2 class="card-title">欢迎回来</h2>
    <p class="card-desc">登录你的 VideoMind 账号</p>

    <form class="form" @submit.prevent="onSubmit">
      <div class="field">
        <label class="field-label">账号</label>
        <input
          class="field-input"
          type="text"
          placeholder="请输入账号"
          :value="account"
          @input="$emit('update:account', ($event.target as HTMLInputElement).value)"
          @keyup.enter="onSubmit"
          autocomplete="username"
        />
      </div>

      <div class="field">
        <label class="field-label">密码</label>
        <input
          class="field-input"
          type="password"
          placeholder="请输入密码"
          :value="password"
          @input="$emit('update:password', ($event.target as HTMLInputElement).value)"
          @keyup.enter="onSubmit"
          autocomplete="current-password"
        />
      </div>

      <div v-if="error" class="error-msg">{{ error }}</div>

      <button class="btn-primary" type="submit" :disabled="loading">
        {{ loading ? '登录中…' : '登 录' }}
      </button>
    </form>

    <p class="switch-text">
      还没有账号？
      <button class="link-btn" @click="$emit('switchToRegister')">立即注册</button>
    </p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  account: string
  password: string
  loading?: boolean
  error?: string | null
}>()

const emit = defineEmits<{
  (e: 'update:account', v: string): void
  (e: 'update:password', v: string): void
  (e: 'submit'): void
  (e: 'switchToRegister'): void
}>()

function onSubmit() {
  emit('submit')
}
</script>

<style scoped>
.form-card {
  width: 100%;
}

.card-title {
  margin: 0 0 4px;
  font-size: 24px;
  font-weight: 700;
  color: #1e293b;
  letter-spacing: -0.4px;
}

.card-desc {
  margin: 0 0 28px;
  font-size: 14px;
  color: #94a3b8;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field-label {
  font-size: 13px;
  font-weight: 500;
  color: #64748b;
}

.field-input {
  padding: 11px 14px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  color: #1e293b;
  font-size: 15px;
  outline: none;
  transition: border-color 0.2s, background 0.2s, box-shadow 0.2s;
}
.field-input::placeholder {
  color: #c0c8d4;
}
.field-input:focus {
  border-color: #818cf8;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1);
}

.error-msg {
  font-size: 13px;
  color: #ef4444;
  padding: 8px 12px;
  background: #fef2f2;
  border-radius: 8px;
  border: 1px solid #fecaca;
}

.btn-primary {
  margin-top: 6px;
  padding: 12px;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  letter-spacing: 1px;
}
.btn-primary:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 18px rgba(99, 102, 241, 0.35);
}
.btn-primary:active:not(:disabled) {
  transform: translateY(0);
}
.btn-primary:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.switch-text {
  margin: 22px 0 0;
  text-align: center;
  font-size: 14px;
  color: #94a3b8;
}

.link-btn {
  background: none;
  border: none;
  color: #6366f1;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  padding: 0;
  transition: color 0.2s;
}
.link-btn:hover {
  color: #4f46e5;
}
</style>
