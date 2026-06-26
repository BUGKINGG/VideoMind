<template>
  <div class="options-view">
    <div class="options-header">
      <h2>设置</h2>
      <button class="back-btn" @click="$emit('back')">← 返回</button>
    </div>
    <div class="options-body">
      <!-- 1. Cookie -->
      <div class="option-item" @click="$emit('showCookie')">
        <div class="option-icon">🍪</div>
        <div class="option-text">
          <div class="option-title">设置 Cookie</div>
          <div class="option-desc">用于获取视频平台的字幕和元数据</div>
        </div>
        <div class="option-arrow">›</div>
      </div>

      <!-- 2. 更改昵称 -->
      <div class="option-item" @click="openNicknameModal">
        <div class="option-icon">✏️</div>
        <div class="option-text">
          <div class="option-title">更改昵称</div>
          <div class="option-desc">修改你的显示名称</div>
        </div>
        <div class="option-arrow">›</div>
      </div>

      <!-- 3. 登出 -->
      <div class="option-item" @click="handleLogout">
        <div class="option-icon">🚪</div>
        <div class="option-text">
          <div class="option-title">登出账号</div>
          <div class="option-desc">退出当前登录状态</div>
        </div>
        <div class="option-arrow">›</div>
      </div>

      <!-- 4. 关于 -->
      <div class="option-item" @click="$emit('showAbout')">
        <div class="option-icon">ℹ️</div>
        <div class="option-text">
          <div class="option-title">关于 VideoMind</div>
          <div class="option-desc">版本信息、开源协议与致谢</div>
        </div>
        <div class="option-arrow">›</div>
      </div>
    </div>

    <!-- 昵称修改弹窗 -->
    <Teleport to="body">
      <div v-if="showNicknameModal" class="modal-overlay" @click.self="closeNicknameModal">
        <div class="modal-card">
          <h3>更改昵称</h3>
          <input
            v-model="nicknameInput"
            class="modal-input"
            placeholder="输入新昵称"
            @keyup.enter="submitNickname"
          />
          <div v-if="nicknameError" class="modal-error">{{ nicknameError }}</div>
          <div class="modal-actions">
            <button class="modal-btn cancel" @click="closeNicknameModal">取消</button>
            <button class="modal-btn confirm" @click="submitNickname" :disabled="nicknameLoading">
              {{ nicknameLoading ? '保存中…' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import request from '../utils/request'

const emit = defineEmits(['back', 'showCookie', 'showAbout'])
const router = useRouter()
const userStore = useUserStore()

// ── 昵称弹窗 ──
const showNicknameModal = ref(false)
const nicknameInput = ref('')
const nicknameError = ref('')
const nicknameLoading = ref(false)

function openNicknameModal() {
  nicknameInput.value = userStore.username || ''
  nicknameError.value = ''
  showNicknameModal.value = true
}

function closeNicknameModal() {
  showNicknameModal.value = false
  nicknameError.value = ''
}

async function submitNickname() {
  const name = nicknameInput.value.trim()
  if (!name) {
    nicknameError.value = '昵称不能为空'
    return
  }
  nicknameLoading.value = true
  nicknameError.value = ''
  try {
    await request.post('/user/username', { username: name })
    userStore.updateUsername(name)
    closeNicknameModal()
  } catch (e: any) {
    nicknameError.value = e?.response?.data?.message || '修改失败'
  } finally {
    nicknameLoading.value = false
  }
}

// ── 登出 ──
function handleLogout() {
  if (!confirm('确定要登出吗？')) return
  userStore.logout()
  router.push('/')
}
</script>

<style scoped>
.options-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8fafc;
}

.options-header {
  padding: 16px 24px;
  background: #fff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.options-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.back-btn {
  padding: 6px 14px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: #64748b;
}
.back-btn:hover {
  background: #f8fafc;
}

/* ── 选项列表 ── */
.options-body {
  padding: 24px 80px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.option-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.option-item:hover {
  border-color: #cbd5e1;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
}
.option-icon {
  font-size: 20px;
}
.option-text {
  flex: 1;
}
.option-title {
  font-size: 15px;
  font-weight: 500;
  color: #1e293b;
}
.option-desc {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 2px;
}
.option-arrow {
  font-size: 18px;
  color: #94a3b8;
}

/* ── 弹窗 ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.modal-card {
  background: #fff;
  border-radius: 14px;
  padding: 28px;
  width: 360px;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}
.modal-card h3 {
  margin: 0 0 18px;
  font-size: 18px;
  font-weight: 600;
  color: #1e293b;
}
.modal-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 15px;
  outline: none;
  color: #1e293b;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.modal-input:focus {
  border-color: #94a3b8;
}
.modal-error {
  font-size: 13px;
  color: #ef4444;
  margin-top: 8px;
}
.modal-actions {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
  margin-top: 20px;
}
.modal-btn {
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  border: none;
  font-weight: 500;
  transition: all 0.15s;
}
.modal-btn.cancel {
  background: #f1f5f9;
  color: #64748b;
}
.modal-btn.cancel:hover {
  background: #e2e8f0;
}
.modal-btn.confirm {
  background: #1e293b;
  color: #fff;
}
.modal-btn.confirm:hover:not(:disabled) {
  background: #334155;
}
.modal-btn.confirm:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
