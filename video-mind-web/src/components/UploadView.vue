<template>
  <div class="landing-view">
    <div class="landing-card">
      <!-- Brand section -->
      <div class="brand-section">
        <h1 class="brand-title">VideoMind</h1>
        <p class="brand-sub">粘贴视频链接，即刻开始 AI 分析</p>
      </div>

      <!-- URL input row -->
      <div class="input-row">
        <div class="url-input-wrapper">
          <span class="input-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
              <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
            </svg>
          </span>
          <input
              :value="videoUrl"
              @input="$emit('update:videoUrl', ($event.target as HTMLInputElement).value)"
              @keyup.enter="$emit('start')"
              type="text"
              class="url-input"
              placeholder="粘贴 B站 视频链接..."
          />
        </div>
        <button
            class="start-btn"
            @click="$emit('start')"
            :disabled="isLoading"
        >
          {{ confirmText }}
        </button>
      </div>

      <!-- Feature tags -->
      <div class="feature-tags">
        <span class="tag">B站视频</span>
        <span class="tag">Cookie 绑定</span>
        <span class="tag">AI 结构化总结</span>
        <span class="tag">持久化对话</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  videoUrl: string
  isLoading: boolean
  confirmText: string
}>()

defineEmits<{
  'update:videoUrl': [value: string]
  start: []
}>()
</script>

<style scoped>
.landing-view {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 10px 40px 15%;
}

.landing-card {
  width: 100%;
  max-width: 80%;
  text-align: center;
}

/* ── Brand ── */
.brand-section {
  margin-bottom: 1%;
}
.brand-title {
  font-size: 56px;
  font-weight: 700;
  letter-spacing: -1px;
  margin: 0 0 8px;
  color: #1e293b;
}
.brand-sub {
  font-size: 16px;
  color: #94a3b8;
  margin: 0;
}

/* ── Input row ── */
.input-row {
  display: flex;
  gap: 10px;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 6px 6px 6px 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 16px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-row:focus-within {
  border-color: #94a3b8;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 24px rgba(0, 0, 0, 0.08);
}

.url-input-wrapper {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.input-icon {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  color: #94a3b8;
}
.input-icon svg {
  width: 20px;
  height: 20px;
}

.url-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  color: #1e293b;
  background: transparent;
  padding: 8px 0;
}
.url-input::placeholder {
  color: #c0c8d4;
}

.start-btn {
  padding: 10px 24px;
  background: #1e293b;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
}
.start-btn:hover:not(:disabled) {
  background: #334155;
}
.start-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ── Tags ── */
.feature-tags {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 20px;
  flex-wrap: wrap;
}
.tag {
  font-size: 12px;
  padding: 5px 12px;
  background: #f1f5f9;
  color: #64748b;
  border-radius: 20px;
  border: 1px solid #e2e8f0;
  font-weight: 500;
}
</style>
