<template>
  <div class="chat-header">
    <button class="back-btn" @click="$emit('back')">← 返回</button>
    <div class="chat-header-center">
      <div class="chat-header-icon">🎬</div>
      <div class="chat-header-info">
        <h3>{{ title }}</h3>
        <p>{{ statusText }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  statusText: string
}>()

defineEmits(['back'])
</script>

<style scoped>
.chat-header {
  position: relative;
  padding: 8px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  min-height: 42px;
}
.chat-header-center {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  max-width: 70%;
}
.chat-header-icon {
  width: 24px;
  height: 24px;
  border-radius: 5px;
  background: #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  flex-shrink: 0;
}
.chat-header-info {
  min-width: 0;
  text-align: center;
}
.chat-header-info h3 {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
}
.chat-header-info p {
  font-size: 11px;
  color: #94a3b8;
  margin: 0;
}
.back-btn {
  position: absolute;
  left: 16px;
  padding: 4px 10px;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 5px;
  font-size: 12px;
  cursor: pointer;
  color: #64748b;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.15s;
}
.back-btn:hover {
  background: #f8fafc;
}
</style>
