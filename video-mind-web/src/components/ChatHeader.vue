<template>
  <div class="chat-header">
    <div class="chat-header-left">
      <div class="chat-header-icon">🎬</div>
      <div class="chat-header-info">
        <h3>{{ title }}</h3>
        <p>{{ statusText }}</p>
      </div>
    </div>
    <button class="back-btn" @click="$emit('back')">← 返回上传</button>
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
  padding: 16px 24px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-chat);
  display: flex;
  align-items: center;
  justify-content: space-between;
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
</style>