<template>
  <div class="login-page">
    <AnimatedBackground />

    <div class="split-layout">
      <!-- Left panel: brand hero -->
      <div class="left-panel">
        <BrandHero />
      </div>

      <!-- Right panel: card with form -->
      <div class="right-panel">
        <div class="auth-card">
          <Transition name="form-switch" mode="out-in">
            <LoginForm
              v-if="currentView === 'login'"
              key="login"
              :account="loginForm.account"
              :password="loginForm.password"
              :loading="loading"
              :error="errorMsg"
              @update:account="loginForm.account = $event"
              @update:password="loginForm.password = $event"
              @submit="onLogin"
              @switchToRegister="switchToRegister"
            />
            <RegisterForm
              v-else
              key="register"
              :username="registerForm.username"
              :account="registerForm.account"
              :password="registerForm.password"
              :passwordRepeat="registerForm.passwordRepeat"
              :loading="loading"
              :error="errorMsg"
              @update:username="registerForm.username = $event"
              @update:account="registerForm.account = $event"
              @update:password="registerForm.password = $event"
              @update:passwordRepeat="registerForm.passwordRepeat = $event"
              @submit="onRegister"
              @switchToLogin="switchToLogin"
            />
          </Transition>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import AnimatedBackground from '../components/landing/AnimatedBackground.vue'
import BrandHero from '../components/landing/BrandHero.vue'
import LoginForm from '../components/landing/LoginForm.vue'
import RegisterForm from '../components/landing/RegisterForm.vue'
import { useAuth } from '../composables/useAuth'

const { handleLogin, handleRegister } = useAuth()

const currentView = ref<'login' | 'register'>('login')
const loading = ref(false)
const errorMsg = ref<string | null>(null)

const loginForm = reactive({
  account: '',
  password: '',
})

const registerForm = reactive({
  username: '',
  account: '',
  password: '',
  passwordRepeat: '',
})

function clearError() {
  errorMsg.value = null
}

function switchToRegister() {
  clearError()
  currentView.value = 'register'
}

function switchToLogin() {
  clearError()
  currentView.value = 'login'
}

async function onLogin() {
  clearError()
  loading.value = true
  const err = await handleLogin({
    account: loginForm.account,
    password: loginForm.password,
  })
  loading.value = false
  if (err) {
    errorMsg.value = err
  }
}

async function onRegister() {
  clearError()
  loading.value = true
  const err = await handleRegister({
    username: registerForm.username,
    account: registerForm.account,
    password: registerForm.password,
    passwordRepeat: registerForm.passwordRepeat,
  })
  loading.value = false
  if (err) {
    errorMsg.value = err
  } else {
    registerForm.username = ''
    registerForm.account = ''
    registerForm.password = ''
    registerForm.passwordRepeat = ''
    switchToLogin()
  }
}
</script>

<style scoped>
.login-page {
  width: 100%;
  min-height: 100vh;
  position: relative;
}

/* ── split layout ── */
.split-layout {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  max-width: 1300px;
  margin: 0 auto;
  padding: 0 24px;
  gap: 0;
}

.left-panel {
  flex: 1 1 5%;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 25px;
}

.right-panel {
  flex: 0 1 45%;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  padding-left: 20px;
}

/* ── card wrapper ── */
.auth-card {
  width: 100%;
  max-width: 420px;
  padding: 44px 40px;
  background: #fff;
  border: 1px solid #e8ecf1;
  border-radius: 20px;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.04),
    0 8px 32px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}

/* ── form transition ── */
.form-switch-enter-active,
.form-switch-leave-active {
  transition: all 0.3s ease;
}
.form-switch-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.form-switch-leave-to {
  opacity: 0;
  transform: translateX(-30px);
}

/* ── mobile ── */
@media (max-width: 860px) {
  .split-layout {
    flex-direction: column;
    max-width: 100%;
    padding: 0;
  }

  .left-panel {
    flex: none;
    padding: 0;
    justify-content: center;
  }

  .right-panel {
    flex: none;
    padding: 0 24px 48px;
    justify-content: center;
  }

  .auth-card {
    padding: 32px 24px;
    max-width: 100%;
  }
}

@media (max-width: 480px) {
  .auth-card {
    padding: 28px 20px;
    border-radius: 16px;
  }
}
</style>
