<template>
  <div class="history-section">
    <div class="history-title">历史记录</div>
    <div class="history-list">
      <div
          v-for="item in list"
          :key="item.id"
          class="history-item"
          :class="{ active: activeId === item.id }"
          @click="$emit('select', item.id)"
      >
        <div class="history-icon">
          <span v-if="item.status === 0" class="processing-spinner"></span>
          <span v-else>🎬</span>
        </div>
        <div class="history-meta">
          <div class="history-video-title">{{ item.title }}</div>
          <div class="history-video-time">
            <template v-if="item.status === 0">处理中...</template>
            <template v-else>{{ item.time }}</template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { HistoryItem } from '../composables/useHistory'

defineProps<{
  list: HistoryItem[]
  activeId: number | null
}>()

defineEmits<{
  select: [id: number]
}>()
</script>

<style scoped>
.history-section {
  flex: 1;
  overflow-y: auto;
  padding: 12px 12px;
  /* 隐藏滚动条 */
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.history-section::-webkit-scrollbar {
  display: none;
}

.history-title {
  font-size: 12px;
  font-weight: 600;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  padding: 0 8px 10px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 10px;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 1px solid transparent;
  margin-bottom: 2px;
}

.history-item:hover {
  background: #f1f5f9;
}
.history-item.active {
  background: #eef2ff;
  border-bottom-color: #e0e7ff;
}

.history-icon {
  width: 34px;
  height: 34px;
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
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-weight: 500;
}
.history-video-time {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

/* 处理中动画 */
.processing-spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid #e2e8f0;
  border-top-color: #6366f1;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
