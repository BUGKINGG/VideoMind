<template>
  <div class="chat-view">
    <ChatHeader
      :title="currentVideoTitle"
      :status-text="headerStatusText"
      :bvid="bvid"
      :part="part"
      :url="url"
      @back="$emit('back')"
    />
    <MessageList :messages="messages" ref="messageListRef" />
    <ChatInput v-model="inputMessage" :disabled="isProcess" @send="handleSend" />
  </div>
</template>

<script setup lang="ts">
import {ref, computed, nextTick} from 'vue'
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
  url?: string
}>()

const emit = defineEmits<{
  back: []
  send: [text: string]
}>()

const inputMessage = ref('')
const messageListRef = ref<InstanceType<typeof MessageList> | null>(null)

const headerStatusText = computed(() => {
  if (props.summaryStage === 'done') return `总结完成 • 已提取 ${props.subtitleCount} 条字幕片段`
  if (props.summaryStage === 'summarizing') return `正在生成总结 • 已提取 ${props.subtitleCount} 条字幕片段`
  return `正在分析视频内容 • 已提取 ${props.subtitleCount} 条字幕片段`
})

function handleSend() {
  if (!inputMessage.value.trim()) return
  emit('send', inputMessage.value)
  nextTick(() =>{
    if(messageListRef.value?.checkIsNearBottom()){
      messageListRef.value?.scrollToBottom()
    }
  })
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