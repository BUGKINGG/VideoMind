<template>
  <div class="app-container">
    <Sidebar
        :user-name="userName"
        :user-uid="userUid"
        :history-list="history.list"
        :active-history-id="history.activeId"
        @turn-to-options="turnToOptions"
        @select-history="handleSelectHistory"
    />

    <main class="main-content">
      <UploadView
          v-if="currentView === 'upload'"
          v-model:video-url="videoUrl"
          :is-loading="summary.isLoading"
          :confirm-text="summary.confirmText"
          @start="handleStartSummary"
      />

      <ChatView
          v-else-if="currentView === 'chat'"
          :messages="messages"
          :current-video-title="summary.currentVideoTitle"
          :subtitle-count="summary.subtitleCount"
          :summary-stage="summary.stage"
          :is-process="chat.isProcess"
          @back="backToUpload"
          @send="handleSendMessage"
      />

      <OptionsView
          v-else-if="currentView === 'options'"
          @back="turnBack"
          @show-cookie="showCookieModal = true"
          @show-about="showAboutModal = true"
      />

      <CookieModal
          v-model="showCookieModal"
          v-model:cookie-value="cookieValue"
          @save="handleSaveCookie"
      />

      <AboutModal v-model="showAboutModal" />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useUserStore } from '@/stores/user'
import Sidebar from "@/components/Sidebar.vue";
import UploadView from '@/components/UploadView.vue'
import ChatView from '@/components/ChatView.vue'
import OptionsView from '@/components/OptionsView.vue'
import CookieModal from '@/components/CookieModal.vue'
import AboutModal from '@/components/AboutModal.vue'
import { useHistory } from '@/composables/useHistory'
import { useSummary } from '@/composables/useSummary'
import { useChat } from '@/composables/useChat'
import { renderMarkdown } from '@/utils/markdown'
import request from '@/utils/request'
import type { Message } from '@/types/message'
import { loadSseState, clearSseState, saveSseState } from '@/composables/sseSession'

// ========== 用户数据 ==========
const userStore = useUserStore()
const userName = computed(() => userStore.username || 'default name')
const userUid = ref('19241001')

// ========== 历史记录 ==========
const history = useHistory()

// ========== 总结 & 聊天 ==========
const messages = ref<Message[]>([])
const summary = useSummary(messages)
const chat = useChat(messages)

// ========== 视图切换 ==========
const currentView = ref<'upload' | 'chat' | 'options'>('upload')
const historyView = ref<'upload' | 'chat'>('upload')
const videoUrl = ref('')

// ========== 弹窗 ==========
const showCookieModal = ref(false)
const showAboutModal = ref(false)
const cookieValue = ref('')

// 监听 SSE 完成（isLoading 从 true 变为 false），自动刷新历史记录
watch(() => summary.isLoading, (newVal, oldVal) => {
  if (oldVal === true && newVal === false) {
    history.load()
  }
})

// metadata 到达时 Conversation 已入库，刷新历史列表让处理中的对话立刻可见
watch(() => summary.subtitleCount, (newVal) => {
  if (newVal > 0) history.load()
})

// 当 conversationId 确定后（metadata 或 done 事件），同步历史记录高亮
watch(() => summary.currentConversationId, (newVal) => {
  if (newVal) {
    history.activeId = newVal
  }
})

// ========== 操作 ==========
function turnToOptions() {
  historyView.value = currentView.value === 'options' ? 'upload' : currentView.value
  currentView.value = 'options'
}

function turnBack() {
  currentView.value = historyView.value
}

function backToUpload() {
  currentView.value = 'upload'
  videoUrl.value = ''
  messages.value = []
  summary.currentConversationId = null
  summary.currentVideoId = null
}

async function handleStartSummary() {
  const result = await summary.start(videoUrl.value, userStore.cookie, userStore.token)
  if(result === 'cached' || result === 'streaming') {
    currentView.value = 'chat'
    // 新对话已创建（即使是处理中 status=0），刷新历史列表
    history.load()
  }
}

async function handleSendMessage(text: string) {
  await chat.send(text, summary.currentConversationId, userStore.token)
  history.load()
}

async function handleSelectHistory(id: number) {
  // 用户主动切换上下文：中断旧的 SSE 连接，防止后台流事件覆盖当前视图的数据
  summary.abort()
  clearSseState()

  history.activeId = id
  const data = await history.loadDetail(id)
  if (!data) return

  currentView.value = 'chat'
  summary.currentConversationId = data.id
  summary.currentVideoId = data.videoId || null
  summary.currentVideoTitle = data.title || '未命名视频'
  summary.subtitleCount = data.subtitleCount || 0
  videoUrl.value = data.url || ''

  // 处理中的对话（status=0）：通过 sid 重连 SSE 流
  if (data.status === 0 && data.sid) {
    summary.stage = 'parsing'
    summary.isLoading = true
    summary.confirmText = '重连中...'
    messages.value = [{
      id: Date.now() + '_placeholder',
      role: 'ai',
      isPlaceholder: true,
      placeholderType: 'summary'
    }]
    // 保存状态并重连（abort 已断开旧连接，cleanSid 会标记 pendingCatchup，
    // 新连接建立后 pushChunk 检测到 emitter 回来 → 自动补发 catchup）
    saveSseState({ sid: data.sid, type: 'summary', view: 'chat' })
    summary.reconnect(data.sid, userStore.token)
    return
  }

  summary.stage = 'done'

  if (data.messages && data.messages.length > 0) {
    messages.value = data.messages.map((msg: any, idx: number) => ({
      id: msg.id || `hist_${idx}_${Date.now()}`,
      role: msg.role,
      content: msg.role === 'ai' ? renderMarkdown(msg.content) : msg.content
    }))
  } else {
    messages.value = [{
      id: Date.now() + '_summary',
      role: 'ai',
      content: renderMarkdown(data.summary || '暂无总结')
    }]
  }
}

async function handleSaveCookie() {
  if (!cookieValue.value) {
    alert('请输入cookie！')
    return
  }
  try {
    await request.post('/user/cookie', { cookie: cookieValue.value })
    userStore.updateCookie(cookieValue.value)
    showCookieModal.value = false
    alert('Cookie 已保存')
  } catch (error) {
    console.error(error)
  }
}

// 初始化
history.load()

// 页面加载时检查是否有未完成的 SSE 会话，自动重连恢复
onMounted(() => {
  const savedState = loadSseState()
  if (!savedState) return

  // 延迟一下，确保 DOM 和 store 已就绪
  setTimeout(() => {
    if (savedState.type === 'summary') {
      // 恢复到刷新前所在的视图（如果之前就是 upload，保持在 upload）
      if (savedState.view === 'upload') {
        // 之前就在开始总结页面等待，保持在当前视图，后台重连
        currentView.value = 'upload'
        summary.isLoading = true
        summary.confirmText = '重连中...'
        // 后台重连 SSE，token 到来后手动切到 chat 视图
      }
      summary.reconnect(savedState.sid, userStore.token)
      // 重连成功后（收到第一个 chunk/metadata/catchup）自动切到 chat
      // 这个逻辑在 processChunk 中：收到数据后 currentView 应为 chat
      if (savedState.view !== 'upload') {
        currentView.value = 'chat'
      }
    } else if (savedState.type === 'chat' && savedState.conversationId) {
      // Chat 重连：先加载历史消息，再创建占位符，最后重连 SSE
      currentView.value = 'chat'
      history.loadDetail(savedState.conversationId).then(data => {
        if (data && data.messages) {
          summary.currentConversationId = data.id
          summary.currentVideoId = data.videoId || null
          summary.currentVideoTitle = data.title || ''
          summary.subtitleCount = data.subtitleCount || 0
          summary.stage = 'done'
          messages.value = data.messages.map((msg: any, idx: number) => ({
            id: msg.id || `hist_${idx}_${Date.now()}`,
            role: msg.role,
            content: msg.role === 'ai' ? renderMarkdown(msg.content) : msg.content
          }))
        }
        // 创建占位符，等待 AI 流式回复（catchup + chunk）
        messages.value.push({
          id: Date.now() + '_ai_placeholder',
          role: 'ai',
          isPlaceholder: true,
          placeholderType: 'chat'
        })
        chat.reconnect(savedState.sid, userStore.token, messages.value.length - 1)
      })
    }
  }, 300)
})
</script>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

:root {
  --sidebar-width: 260px;
  --primary: #4f46e5;
  --primary-hover: #4338ca;
  --bg-main: #f8fafc;
  --bg-sidebar: #ffffff;
  --bg-chat: #ffffff;
  --border: #e2e8f0;
  --text-primary: #1e293b;
  --text-secondary: #64748b;
  --text-muted: #94a3b8;
  --radius: 12px;
  --shadow: 0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
}

.app-container {
  display: flex;
  height: 100vh;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
  'Helvetica Neue', Arial, sans-serif;
  background: var(--bg-main);
  color: var(--text-primary);
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* ========== Markdown 全局样式（v-html 穿透） ========== */
:deep(.markdown-body),
:deep(.markdown-body *) {
  text-align: left !important;
}

:deep(.markdown-body) {
  font-size: 18px;
  line-height: 1.8;
  color: var(--text-primary);
  word-break: break-word;
}

:deep(.markdown-body h1) {
  font-size: 18px;
  font-weight: 600;
  margin: 20px 0 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}

:deep(.markdown-body h2) {
  font-size: 17px;
  font-weight: 600;
  margin: 18px 0 10px;
}

:deep(.markdown-body h3) {
  font-size: 16px;
  font-weight: 600;
  color: var(--primary);
  margin: 16px 0 8px;
}

:deep(.markdown-body p) {
  margin-bottom: 12px;
}

:deep(.markdown-body ul),
:deep(.markdown-body ol) {
  padding-left: 24px;
  margin-bottom: 12px;
}

:deep(.markdown-body li) {
  margin-bottom: 6px;
}

:deep(.markdown-body ul li) {
  list-style-type: disc;
}

:deep(.markdown-body ul li::marker) {
  color: var(--primary);
}

:deep(.markdown-body strong) {
  font-weight: 600;
  color: var(--primary);
}

:deep(.markdown-body pre) {
  background: #f8fafc;
  border-radius: 8px;
  padding: 14px 16px;
  overflow-x: auto;
  margin-bottom: 12px;
  border: 1px solid var(--border);
  text-align: left !important;
}

:deep(.markdown-body pre code) {
  font-size: 13.5px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  color: #334155;
  background: transparent;
  padding: 0;
}

:deep(.markdown-body code) {
  background: #eef2ff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13.5px;
  font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
  color: var(--primary);
}

:deep(.markdown-body blockquote) {
  margin: 12px 0;
  padding: 10px 16px;
  border-left: 4px solid var(--primary);
  background: #f8fafc;
  border-radius: 0 8px 8px 0;
  color: var(--text-secondary);
}

:deep(.markdown-body table) {
  width: 100%;
  border-collapse: collapse;
  margin-bottom: 12px;
  font-size: 14px;
}

:deep(.markdown-body th),
:deep(.markdown-body td) {
  border: 1px solid var(--border);
  padding: 8px 12px;
  text-align: left !important;
}

:deep(.markdown-body th) {
  background: #f8fafc;
  font-weight: 600;
}

:deep(.markdown-body hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 18px 0;
}

:deep(.markdown-body a) {
  color: var(--primary);
  text-decoration: none;
}

:deep(.markdown-body a:hover) {
  text-decoration: underline;
}

:deep(.markdown-body img) {
  max-width: 100%;
  border-radius: 8px;
  margin: 8px 0;
}

:deep(.timestamp-badge) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #fef3c7;
  color: #92400e;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  margin: 0 4px;
  cursor: pointer;
}
</style>
