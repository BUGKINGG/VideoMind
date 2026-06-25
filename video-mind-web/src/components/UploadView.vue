<template>
  <div class="upload-view">
    <div class="upload-card">
      <div class="upload-title">开始视频学习</div>
      <div class="upload-subtitle">
        上传本地视频或粘贴视频链接，AI 将自动生成结构化总结
      </div>

      <div
          class="upload-zone"
          @click="triggerFileSelect"
          @dragover.prevent
          @drop.prevent="handleDrop"
      >
        <div class="upload-zone-icon">📁</div>
        <div class="upload-zone-text">
          {{ isDragging ? '松开以上传视频' : '点击上传或拖拽视频到此处' }}
        </div>
        <div class="upload-zone-hint">支持 MP4, MKV, AVI, WebM 等格式</div>
      </div>

      <div class="input-row">
        <button class="file-btn" @click="triggerFileSelect">📎 选择文件</button>
        <input
            ref="fileInput"
            type="file"
            accept="video/*"
            style="display: none"
            @change="handleFileChange"
        />
        <input
            :value="videoUrl"
            @input="$emit('update:videoUrl', ($event.target as HTMLInputElement).value)"
            type="text"
            class="url-input"
            placeholder="粘贴视频 URL 链接 (B站/YouTube/...)"
        />
      </div>

      <button class="confirm-btn" @click="$emit('start')" :disabled="isLoading" :class="{ loading: isLoading }">
        {{ confirmText }}
      </button>

      <div class="feature-tags">
        <span class="tag">视频内容提取</span>
        <span class="tag">AI 结构化总结</span>
        <span class="tag">对话学习助手</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  videoUrl: string
  isLoading: boolean
  confirmText: string
}>()

const emit = defineEmits<{
  'update:videoUrl': [value: string]
  start: []
}>()

const fileInput = ref<HTMLInputElement | null>(null)
const isDragging = ref(false)

function triggerFileSelect() {
  fileInput.value?.click()
}

function handleFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) emit('update:videoUrl', file.name)
}

function handleDrop(e: DragEvent) {
  isDragging.value = false
  const files = e.dataTransfer?.files
  if (files && files.length > 0) emit('update:videoUrl', files[0].name)
}
</script>

<style scoped>
.upload-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  padding: 40px;
}
.upload-card {
  background: var(--bg-chat);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 48px 40px;
  width: 100%;
  max-width: 640px;
  box-shadow: var(--shadow-lg);
  text-align: center;
}
.upload-title {
  font-size: 22px;
  font-weight: 700;
  margin-bottom: 8px;
}
.upload-subtitle {
  color: var(--text-secondary);
  font-size: 14px;
  margin-bottom: 32px;
}
.upload-zone {
  border: 2px dashed #cbd5e1;
  border-radius: var(--radius);
  padding: 40px 24px;
  margin-bottom: 24px;
  transition: all 0.2s;
  cursor: pointer;
}
.upload-zone:hover {
  border-color: var(--primary);
  background: #f8fafc;
}
.upload-zone-icon {
  font-size: 40px;
  margin-bottom: 12px;
  opacity: 0.6;
}
.upload-zone-text {
  font-size: 14px;
  color: var(--text-secondary);
  margin-bottom: 4px;
}
.upload-zone-hint {
  font-size: 12px;
  color: var(--text-muted);
}
.input-row {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.url-input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}
.url-input:focus {
  border-color: var(--primary);
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}
.file-btn {
  padding: 10px 18px;
  border: 1px solid var(--border);
  background: white;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  color: var(--text-primary);
}
.file-btn:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
}
.confirm-btn {
  width: 100%;
  padding: 12px 24px;
  background: var(--primary);
  color: #575555;
  border-radius: 8px;
  border-color: #c8ced9;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s;
}
.confirm-btn:hover {
  background: var(--primary-hover);
}
.feature-tags {
  display: flex;
  gap: 8px;
  justify-content: center;
  margin-top: 16px;
}
.tag {
  font-size: 12px;
  padding: 4px 10px;
  background: #f1f5f9;
  color: var(--text-secondary);
  border-radius: 20px;
  border: 1px solid var(--border);
}
</style>