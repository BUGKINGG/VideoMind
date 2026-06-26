<template>
  <div class="chat-messages" ref="container" @scroll="onScroll">
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

    <!-- 两个箭头都在右下角，↑ 在上 ↓ 在下 -->
    <button
        class="scroll-btn scroll-top-btn"
        :class="{ visible: showScrollTopBtn }"
        @click="scrollToTop"
        aria-label="滚动到顶部"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="18 15 12 9 6 15"/>
      </svg>
    </button>
    <button
        class="scroll-btn scroll-bottom-btn"
        :class="{ visible: showScrollBottomBtn }"
        @click="scrollToBottom"
        aria-label="滚动到底部"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
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
const showScrollTopBtn = ref(false)
const showScrollBottomBtn = ref(false)
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
  nextTick(() => checkScrollPosition())
}, { deep: true })

function checkScrollPosition() {
  const el = container.value
  if (!el) return
  const nearTop = el.scrollTop < 80
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80
  showScrollTopBtn.value = !nearTop
  showScrollBottomBtn.value = !nearBottom
}

function onScroll() {
  checkScrollPosition()
}

function scrollToTop() {
  if (container.value) {
    container.value.scrollTo({ top: 0, behavior: 'smooth' })
    // smooth 滚动结束后再检查一次
    setTimeout(() => checkScrollPosition(), 400)
  }
}

function scrollToBottom() {
  if (container.value) {
    container.value.scrollTo({ top: container.value.scrollHeight, behavior: 'smooth' })
    setTimeout(() => checkScrollPosition(), 400)
  }
}

defineExpose({ scrollToBottom, container })
</script>

<style scoped>
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 32px 48px;
  position: relative;
}

.message {
  display: flex;
  gap: 14px;
  margin-bottom: 36px;
  max-width: 75%;
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
  background: #1e293b;
  color: #fff;
}
.message.user .message-avatar {
  background: #e2e8f0;
  color: #64748b;
}
.message-content {
  background: #fff;
  padding: 16px 20px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  font-size: 16px;
  line-height: 1.8;
  text-align: left;
  color: #1e293b;
  overflow-wrap: break-word;
}
.placeholder-message {
  display: flex;
  flex-direction: column;
}
.placeholder-main {
  font-size: 16px;
  line-height: 1.8;
  color: #64748b;
  white-space: pre-line;
}
.message.user .message-content {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
}

/* ── shared scroll buttons ── */
.scroll-btn {
  position: sticky;
  left: calc(100% - 54px);
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #fff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #64748b;
  opacity: 0;
  pointer-events: none;
  z-index: 10;
  transition: opacity 0.25s, transform 0.25s;
}
.scroll-btn.visible {
  opacity: 1;
  pointer-events: auto;
}
.scroll-btn:hover {
  background: #f8fafc;
  color: #1e293b;
  border-color: #cbd5e1;
}
.scroll-btn svg {
  width: 20px;
  height: 20px;
}

.scroll-top-btn {
  bottom: 62px;   /* 16px + 38px + 8px gap */
  transform: translateY(-8px);
}
.scroll-top-btn.visible {
  transform: translateY(0);
}

.scroll-bottom-btn {
  bottom: 16px;
  transform: translateY(8px);
}
.scroll-bottom-btn.visible {
  transform: translateY(0);
}
</style>
