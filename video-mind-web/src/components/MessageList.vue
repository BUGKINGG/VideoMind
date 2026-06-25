<template>
  <div class="chat-messages" ref="container">
    <div
        v-for="msg in messages"
        :key="msg.id"
        class="message"
        :class="msg.role"
    >
      <div class="message-avatar">{{ msg.role === 'ai' ? 'AI' : '我' }}</div>
      <div class="message-content">
        <div v-if="msg.isPlaceholder" class="placeholder-message">
          <div class="placeholder-main">{{ placeholderText }}</div>
        </div>
        <div v-else-if="msg.role === 'ai'" class="markdown-body" v-html="msg.content"></div>
        <div v-else>{{ msg.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import type { Message } from '../types/message'

const props = defineProps<{
  messages: Message[]
}>()

const container = ref<HTMLElement | null>(null)
const dots = ref(1)
let timer: ReturnType<typeof setInterval> | null = null

const placeholderText = computed(() => {
  const placeholder = props.messages.find(m => m.isPlaceholder)
  if (!placeholder) return ''
  const base = placeholder.placeholderType === 'chat' ? '思考中' : '正在解析视频内容并生成总结'
  return base + '。'.repeat(dots.value)
})

watch(() => props.messages.find(m => m.isPlaceholder), (hasPlaceholder) => {
  if (hasPlaceholder) {
    if (timer) clearInterval(timer)
    dots.value = 1
    timer = setInterval(() => { dots.value = dots.value % 3 + 1 }, 500)
  } else {
    if (timer) { clearInterval(timer); timer = null }
    dots.value = 1
  }
}, { immediate: true, deep: true })

watch(() => props.messages, () => {
  scrollToBottom()
}, { deep: true })

function scrollToBottom() {
  nextTick(() => {
    if (container.value) container.value.scrollTop = container.value.scrollHeight
  })
}

defineExpose({ scrollToBottom, container })
</script>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  background: var(--bg-main);
}
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 24px;
  max-width: 80%;
}
.message.user {
  margin-left: auto;
  flex-direction: row-reverse;
}
.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  font-weight: 600;
}
.message.ai .message-avatar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}
.message.user .message-avatar {
  background: #e2e8f0;
  color: var(--text-secondary);
}
.message-content {
  background: white;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid var(--border);
  font-size: 18px;
  line-height: 1.8;
  box-shadow: var(--shadow);
  text-align: left;
  width: 100%;
  color: var(--text-primary);
}
.placeholder-message {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.placeholder-main {
  font-size: 18px;
  line-height: 1.8;
  color: var(--text-primary);
  white-space: pre-line;
}
.message.user .message-content {
  background: #ffffff;
  color: #1f2937;
  border: 1px solid #e5e7eb;
}
</style>