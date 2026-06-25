<template>
  <div class="chat-input-area">
    <div class="chat-input-wrapper">
      <textarea
          :value="modelValue"
          @input="handleInput"
          class="chat-input"
          rows="1"
          placeholder="询问关于视频的任何问题，或要求 AI 截取特定时间戳分析..."
          @keydown.enter.prevent="handleSend"
      ></textarea>
      <button class="send-btn" @click="handleSend" :disabled="disabled">➤</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { nextTick } from 'vue'

const props = defineProps<{
  modelValue: string
  disabled: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
  send: []
}>()

function handleInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
  autoResize(target)
}

function handleSend() {
  if (!props.modelValue.trim() || props.disabled) return
  emit('send')
  nextTick(() => {
    const textarea = document.querySelector('.chat-input') as HTMLTextAreaElement
    if (textarea) textarea.style.height = 'auto'
  })
}

function autoResize(textarea: HTMLTextAreaElement) {
  nextTick(() => {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
  })
}
</script>

<style scoped>
.chat-input-area {
  padding: 16px 24px;
  background: var(--bg-chat);
  border-top: 1px solid var(--border);
}
.chat-input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: var(--bg-main);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 14px;
}
.chat-input {
  flex: 1;
  border: none;
  background: transparent;
  outline: none;
  font-size: 14px;
  resize: none;
  max-height: 120px;
  font-family: inherit;
  line-height: 1.5;
}
.chat-input::placeholder {
  color: var(--text-muted);
}
.send-btn {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: black;
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.2s;
}
.send-btn:enabled:hover {
  background: #2d2d2d;
}
.send-btn:disabled {
  background: #b41010;
}
</style>