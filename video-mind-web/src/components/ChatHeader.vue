<template>
  <div class="chat-header">
    <button class="back-btn" @click="$emit('back')">← 返回</button>
    <div class="chat-header-center" :class="{ clickable: !!url }" @click="openUrl">
      <span v-if="bvid" class="meta-bvid">{{ bvid }}</span>
      <span v-if="part" class="meta-part">p{{ part }}</span>
      <h3 class="header-title">{{ title }}</h3>
    </div>
    <p class="header-status">{{ statusText }}</p>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  title: string
  statusText: string
  bvid?: string
  part?: number
  url?: string
}>()

defineEmits(['back'])

function openUrl() {
  if (props.url) {
    window.open(props.url, '_blank')
  }
}
</script>

<style scoped>
.chat-header {
  position: relative;
  padding: 8px 16px;
  border-bottom: 1px solid #e2e8f0;
  background: #fff;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  min-height: 42px;
  gap: 1px;
}
.chat-header-center {
  display: flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
  max-width: 75%;
}
.chat-header-center.clickable {
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 6px;
  transition: background 0.15s;
}
.chat-header-center.clickable:hover {
  background: #f8fafc;
}
.meta-bvid {
  font-size: 11px;
  color: #6366f1;
  font-weight: 500;
  background: #eef2ff;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.meta-part {
  font-size: 11px;
  color: #f59e0b;
  font-weight: 600;
  background: #fffbeb;
  padding: 1px 6px;
  border-radius: 3px;
  flex-shrink: 0;
}
.header-title {
  font-size: 13px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
}
.header-status {
  font-size: 11px;
  color: #94a3b8;
  margin: 0;
}
.back-btn {
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
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
