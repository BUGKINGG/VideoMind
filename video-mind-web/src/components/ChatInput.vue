<template>
  <div class="chat-input-area">
    <div class="chat-input-pill">
      <textarea
          :value="modelValue"
          @input="handleInput"
          class="chat-input"
          rows="1"
          placeholder="询问关于视频的任何问题..."
          @keydown.enter.prevent="handleSend"
      ></textarea>
      <button class="send-btn" @click="handleSend" :disabled="disabled">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <line x1="12" y1="19" x2="12" y2="5"/>
          <polyline points="5 12 12 5 19 12"/>
        </svg>
      </button>
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
  padding: 12px 24px 16px;
}

.chat-input-pill {
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  gap: 10px;
  align-items: flex-end;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 20px;
  padding: 8px 8px 8px 18px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 2px 12px rgba(0, 0, 0, 0.04);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.chat-input-pill:focus-within {
  border-color: #c0c8d4;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04), 0 4px 20px rgba(0, 0, 0, 0.08);
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
  padding: 4px 0;
  color: #1e293b;
}
.chat-input::placeholder {
  color: #94a3b8;
}

.send-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #1e293b;
  color: #fff;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.15s;
}
.send-btn svg {
  width: 16px;
  height: 16px;
}
.send-btn:enabled:hover {
  background: #334155;
}
.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
</style>
