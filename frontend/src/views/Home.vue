<template>
  <div class="app-container">
    <!-- 左侧边栏 -->
    <aside class="sidebar">
      <div class="profile-section">
        <div class="profile-card">
          <div class="avatar">{{ userInitials }}</div>
          <div class="profile-info">
            <div class="profile-name">{{ userName }}</div>
            <div class="profile-uid">UID: {{ userUid }}</div>

          </div>
          <button class="option-btn" @click="turnToOptions">设置</button>
        </div>
      </div>

      <div class="history-section">
        <div class="history-title">历史记录</div>
        <div class="history-list">
          <div
              v-for="(item, index) in historyList"
              :key="item.id"
              class="history-item"
              :class="{ active: activeHistoryId === item.id }"
              @click="selectHistory(item.id)"
          >
            <div class="history-icon">🎬</div>
            <div class="history-meta">
              <div class="history-video-title">{{ item.title }}</div>
              <div class="history-video-time">{{ item.time }}</div>
            </div>
          </div>
        </div>
      </div>
    </aside>

    <!-- 右侧主区域 -->
    <main class="main-content">
      <!-- 视图1：上传界面 -->
      <div v-if="currentView === 'upload'" class="upload-view">
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
            <div class="upload-zone-hint">
              支持 MP4, MKV, AVI, WebM 等格式
            </div>
          </div>

          <div class="input-row">
            <button class="file-btn" @click="triggerFileSelect">
              📎 选择文件
            </button>
            <input
                ref="fileInput"
                type="file"
                accept="video/*"
                style="display: none"
                @change="handleFileChange"
            />
            <input
                v-model="videoUrl"
                type="text"
                class="url-input"
                placeholder="粘贴视频 URL 链接 (B站/YouTube/...)"
            />
          </div>

          <button class="confirm-btn" @click="startSummary">
             开始总结
          </button>

          <div class="feature-tags">
            <span class="tag"> 智能字幕提取</span>
            <span class="tag"> AI 结构化总结</span>
            <span class="tag"> 多模态时间戳</span>
          </div>
        </div>
      </div>

      <!-- 视图2：AI 聊天界面 -->
      <div v-else-if="currentView === 'chat'" class="chat-view">
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="chat-header-icon">🎬</div>
            <div class="chat-header-info">
              <h3>{{ currentVideoTitle }}</h3>
              <p>正在分析视频内容 • 已提取 {{ subtitleCount }} 条字幕片段</p>
            </div>
          </div>
          <button class="back-btn" @click="backToUpload">← 返回上传</button>
        </div>

        <div class="chat-messages" ref="messagesContainer">
          <div
              v-for="(msg, index) in messages"
              :key="index"
              class="message"
              :class="msg.role"
          >
            <div class="message-avatar">
              {{ msg.role === 'ai' ? 'AI' : '我' }}
            </div>
            <div class="message-content" v-html="msg.content"></div>
          </div>
        </div>

        <div class="chat-input-area">
          <div class="chat-input-wrapper">
            <textarea
                v-model="inputMessage"
                class="chat-input"
                rows="1"
                placeholder="询问关于视频的任何问题，或要求 AI 截取特定时间戳分析..."
                @input="autoResize"
                @keydown.enter.prevent="sendMessage"
            ></textarea>
            <button class="send-btn" @click="sendMessage">➤</button>
          </div>
        </div>
      </div>

      <!--                视图三：设置界面            -->
      <div v-else-if="currentView === 'options'" class="options-view">
        <div class="options-header">
          <h2>设置</h2>
          <button class="back-btn" @click="turnBack">← 返回</button>
        </div>
        <div class="options-body">
          <div class="option-item" @click="showCookieModal = true">
            <div class="option-icon">🍪</div>
            <div class="option-text">
              <div class="option-title">绑定 / 修改 Cookie</div>
              <div class="option-desc">用于获取视频平台的字幕和元数据</div>
            </div>
            <div class="option-arrow">›</div>
          </div>
          <div class="option-item" @click="showAboutModal = true">
            <div class="option-icon">ℹ️</div>
            <div class="option-text">
              <div class="option-title">关于 VideoMind</div>
              <div class="option-desc">版本信息、开源协议与致谢</div>
            </div>
            <div class="option-arrow">›</div>
          </div>
        </div>
      </div>

      <!-- Cookie 弹窗 -->
      <div v-if="showCookieModal" class="modal-overlay" @click.self="showCookieModal = false">
        <div class="modal-card">
          <h3>绑定 Cookie</h3>
          <p class="modal-hint">粘贴你从浏览器开发者工具中复制的 Cookie 字符串</p>
          <textarea v-model="cookieValue" class="modal-textarea" rows="4" placeholder="例如: SESSDATA=xxx; bili_jct=yyy..."></textarea>
          <div class="modal-actions">
            <button class="modal-btn secondary" @click="showCookieModal = false">取消</button>
            <button class="modal-btn primary" @click="saveCookie">保存</button>
          </div>
        </div>
      </div>

      <!-- 关于弹窗 -->
      <div v-if="showAboutModal" class="modal-overlay" @click.self="showAboutModal = false">
        <div class="modal-card">
          <h3>关于 VideoMind</h3>
          <div class="about-content">
            <p><strong>VideoMind</strong> — 视频学习总结助手</p>
            <p>版本：v0.1.0</p>
            <p>基于 AI Agent 技术，支持字幕提取、结构化总结与多模态时间戳分析。</p>
          </div>
          <div class="modal-actions">
            <button class="modal-btn primary" @click="showAboutModal = false">知道了</button>
          </div>
        </div>
      </div>

    </main>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import {useUserStore} from "../stores/user.ts";
import request from '../utils/request'

// ========== 用户数据 ==========
const userStore = useUserStore()
const userName = computed(() => userStore.username || "default name")
const userUid = ref('19241001')
const userInitials = computed(() => {
  return userName.value
      .split(' ')
      .map((w) => w[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
})

// ========== 历史记录 ==========
const activeHistoryId = ref(1)
const historyList = ref([
  { id: 1, title: 'LangChain Agent 深度解析...', time: '2小时前' },
  { id: 2, title: 'Spring Boot 微服务架构实战', time: '昨天' },
  { id: 3, title: '高等代数技巧选讲 - 第3讲', time: '3天前' },
  { id: 4, title: 'React 18 并发模式原理', time: '1周前' },
  { id: 5, title: '微分方程数值解法 - Lanczos', time: '2周前' },
])

function selectHistory(id) {
  activeHistoryId.value = id
  // TODO: 加载对应历史会话
}

// ========== 视图切换 ==========
const currentView = ref('upload') // 'upload' | 'chat'
const videoUrl = ref('')
const currentVideoTitle = ref('')
const subtitleCount = ref(0)
const historyView = ref('')
const showCookieModal = ref(false)
const showAboutModal = ref(false)
const cookieValue = ref('')


function startSummary() {
  if (!videoUrl.value) {
    alert('请先上传视频或输入链接')
    return
  }
  currentVideoTitle.value = videoUrl.value
  subtitleCount.value = 1247
  currentView.value = 'chat'
  // TODO: 调用后端 API 开始分析
}

function backToUpload() {
  currentView.value = 'upload'
  videoUrl.value = ''
  messages.value = [...defaultMessages]
}

async function saveCookie() {
  if(!cookieValue){
    alert("请输入cookie！")
    return
  }

  try{
    const res = await request.post("/api/cookie", {
      cookie: cookieValue.value
    })

    userStore.updateCookie(cookieValue.value)

    console.log('保存 Cookie:', cookieValue.value)
    showCookieModal.value = false
    alert('Cookie 已保存')
  } catch (error){
    console.error(error)
  }
}

function turnToOptions() {
  historyView.value = currentView.value
  currentView.value = 'options'
}

function turnBack (){
  currentView.value = historyView.value
}

// ========== 文件上传 ==========
const fileInput = ref(null)
const isDragging = ref(false)

function triggerFileSelect() {
  fileInput.value?.click()
}

function handleFileChange(e) {
  const file = e.target.files[0]
  if (file) {
    videoUrl.value = file.name
    // TODO: 实际上传文件到后端
  }
}

function handleDrop(e) {
  isDragging.value = false
  const files = e.dataTransfer.files
  if (files.length > 0) {
    videoUrl.value = files[0].name
    // TODO: 处理拖拽上传
  }
}

// ========== 聊天消息 ==========
const messagesContainer = ref(null)
const inputMessage = ref('')

const defaultMessages = [
  {
    role: 'ai',
    content: `已完成视频分析！以下是结构化总结：<br><br>
<strong>1. Agent 核心架构</strong><br>
视频首先介绍了 ReAct 推理模式，即 Reasoning + Acting 的循环架构。<br><br>
<strong>2. 工具调用机制</strong><br>
在 <span class="timestamp-badge">⏱ 04:32</span> 处详细讲解了 Tool 的注册与绑定方式。<br><br>
<strong>3. 记忆系统设计</strong><br>
视频后半部分重点讲解了 Short-term vs Long-term Memory 的设计权衡。`,
  },
  {
    role: 'user',
    content: '请帮我找到视频中讲解 LangGraph 状态机的部分',
  },
  {
    role: 'ai',
    content: `在 <span class="timestamp-badge">⏱ 12:15</span> 开始讲解 LangGraph 的状态机设计。讲师提到"看图我们可知，StateGraph 的核心是通过节点和边来构建有向图结构..."<br><br>
这里我截取了该时间点的画面进行分析：<br>
[🖼️ 截图分析占位] 图中展示了 StateGraph 的初始化流程。<br><br>
关键要点：LangGraph 相比普通 Agent 的优势在于支持循环流程和条件分支。`,
  },
]

const messages = ref([...defaultMessages])

function sendMessage() {
  const text = inputMessage.value.trim()
  if (!text) return

  messages.value.push({ role: 'user', content: text })
  inputMessage.value = ''
  autoResize()

  // TODO: 调用后端 API 发送消息
  // 模拟 AI 回复
  setTimeout(() => {
    messages.value.push({
      role: 'ai',
      content: `这是关于您提问的回复。相关时间点 <span class="timestamp-badge">⏱ 08:45</span> 处有详细讲解。`,
    })
    scrollToBottom()
  }, 800)

  nextTick(() => scrollToBottom())
}

function scrollToBottom() {
  nextTick(() => {
    const container = messagesContainer.value
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}

// ========== 输入框自适应高度 ==========
function autoResize() {
  nextTick(() => {
    const textarea = document.querySelector('.chat-input')
    if (textarea) {
      textarea.style.height = 'auto'
      textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px'
    }
  })
}
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
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1),
  0 4px 6px -4px rgb(0 0 0 / 0.1);
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

/* ========== 左侧边栏 ========== */
.sidebar {
  width: 350px;
  background: var(--bg-sidebar);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.profile-section {
  padding: 20px;
  border-bottom: 1px solid var(--border);
}

.profile-card {
  display: flex;
  align-items: center;
  gap: 12px;
}

.avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-weight: 600;
  font-size: 16px;
  flex-shrink: 0;
}

.profile-info {
  overflow: hidden;
}

.profile-name {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.profile-uid {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.history-section {
  flex: 1;
  overflow-y: auto;
  padding: 16px 12px;
}

.history-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  padding: 0 8px 12px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 8px;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.history-item:hover {
  background: #f1f5f9;
}

.history-item.active {
  background: #eef2ff;
}

.history-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  flex-shrink: 0;
}

.history-item.active .history-icon {
  background: #c7d2fe;
}

.history-meta {
  overflow: hidden;
  flex: 1;
}

.history-video-title {
  font-size: 13px;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}

.history-video-time {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

/* ========== 右侧主区域 ========== */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* --- 上传视图 --- */
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

/* --- 聊天视图 --- */
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.chat-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-chat);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-header-option {
  justify-content: right;
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.chat-header-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #eef2ff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.chat-header-info h3 {
  font-size: 15px;
  font-weight: 600;
}

.chat-header-info p {
  font-size: 12px;
  color: var(--text-muted);
  margin-top: 2px;
}

.back-btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  background: white;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: var(--text-secondary);
}

.back-btn:hover {
  background: #f8fafc;
}

.back-btn-option {
  margin-right: 30px;
}

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
  padding: 14px 18px;
  border-radius: 12px;
  border: 1px solid var(--border);
  font-size: 14px;
  line-height: 1.6;
  box-shadow: var(--shadow);
}

.message.user .message-content {
  background: var(--primary);
  color: white;
  border-color: var(--primary);
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
  background: var(--primary);
  color: white;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: background 0.2s;
}

.send-btn:hover {
  background: var(--primary-hover);
}

.option-btn {
  background: white;
  border: none;
  font-size: 15px;
  color: #757474;
  border-radius: 12px;
  transition-duration: 0.2s;
  margin-left: 20px;
  width: 50px;
  height: 30px;
}

.option-btn:hover{
  background: #e8e5e5;
}

.option-btn:active{
  transform: translateY(-3px);
}

.main-options {
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 100px;
  border: 2px solid #eaeaea;
  border-radius: 8px;
  box-shadow: 1px 1px 1px 1px #9ca3af ;
  height: 600px;
}

.cookie-btn {
  border-radius: 12px;
  width: 300px;
  height: 30px;
  background: #ececec;
}

/* 设置按钮 */
.settings-btn {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: background 0.2s;
}
.settings-btn:hover {
  background: #f1f5f9;
}

/* 设置视图 */
.options-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #f8fafc;
}
.options-header {
  padding: 16px 24px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.options-header h2 {
  font-size: 18px;
  font-weight: 600;
}
.options-body {
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.option-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 18px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-left: 80px;
  margin-right: 80px;
}
.option-item:hover {
  border-color: #cbd5e1;
  box-shadow: 0 1px 3px 0 rgb(0 0 0 / 0.08);
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

/* 弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal-card {
  background: #ffffff;
  border-radius: 12px;
  padding: 24px;
  width: 100%;
  max-width: 440px;
  box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1);
}
.modal-card h3 {
  font-size: 17px;
  font-weight: 600;
  margin-bottom: 8px;
}
.modal-hint {
  font-size: 13px;
  color: #64748b;
  margin-bottom: 16px;
}
.modal-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
  outline: none;
}
.modal-textarea:focus {
  border-color: #4f46e5;
  box-shadow: 0 0 0 3px rgba(79, 70, 229, 0.1);
}
.about-content {
  font-size: 14px;
  line-height: 1.7;
  color: #475569;
  margin-bottom: 8px;
}
.about-content p {
  margin-bottom: 8px;
}
.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 20px;
}
.modal-btn {
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.2s;
}
.modal-btn.primary {
  background: #4f46e5;
  color: white;
  border-color: #4f46e5;
}
.modal-btn.primary:hover {
  background: #4338ca;
}
.modal-btn.secondary {
  background: #ffffff;
  color: #64748b;
  border-color: #e2e8f0;
}
.modal-btn.secondary:hover {
  background: #f8fafc;
}
</style>