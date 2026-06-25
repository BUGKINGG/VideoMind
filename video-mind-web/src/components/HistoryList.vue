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
        <div class="history-icon">🎬</div>
        <div class="history-meta">
          <div class="history-video-title">{{ item.title }}</div>
          <div class="history-video-time">{{ item.time }}</div>
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
</style>