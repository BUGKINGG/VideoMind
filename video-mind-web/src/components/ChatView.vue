<template>
  <div class="chat-view">
    <ChatHeader
      :title="currentVideoTitle"
      :status-text="headerStatusText"
      :bvid="bvid"
      :part="part"
      @back="$emit('back')"
    />
    <MessageList :messages="messages" ref="messageListRef" />
    <ChatInput v-model="inputMessage" :disabled="isProcess" @send="handleSend" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import ChatHeader from './ChatHeader.vue'
import MessageList from './MessageList.vue'
import ChatInput from './ChatInput.vue'
import type { Message } from '../types/message'

const props = defineProps<{
  messages: Message[]
  currentVideoTitle: string
  subtitleCount: number
  summaryStage: string
  isProcess: boolean
  bvid?: string
  part?: number
}>()

const emit = defineEmits<{
  back: []
  send: [text: string]
}>()

const inputMessage = ref('')

const headerStatusText = computed(() => {
  if (props.summaryStage === 'done') return `总结完成 • 已提取 ${props.subtitleCount} 条字幕片段`
  if (props.summaryStage === 'summarizing') return `正在生成总结 • 已提取 ${props.subtitleCount} 条字幕片段`
  return `正在分析视频内容 • 已提取 ${props.subtitleCount} 条字幕片段`
})

function handleSend() {
  if (!inputMessage.value.trim()) return
  emit('send', inputMessage.value)
  inputMessage.value = ''
}
</script>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}
</style>