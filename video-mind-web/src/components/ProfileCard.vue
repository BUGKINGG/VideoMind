<template>
  <div class="profile-card">
    <div class="avatar">{{ initials }}</div>
    <div class="profile-info">
      <div class="profile-name">{{ userName }}</div>
    </div>
    <button class="option-btn" @click="$emit('turnToOptions')">设置</button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  userName: string
  userUid: string
}>()

const initials = computed(() => {
  return props.userName
      .split(' ')
      .map((w) => w[0])
      .join('')
      .toUpperCase()
      .slice(0, 2)
})

defineEmits(['turnToOptions'])
</script>

<style scoped>
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
  flex: 1;
}
.profile-name {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.option-btn {
  background: white;
  border: none;
  font-size: 14px;
  color: #94a3b8;
  border-radius: 8px;
  transition: all 0.2s;
  padding: 4px 10px;
  cursor: pointer;
}
.option-btn:hover {
  background: #f1f5f9;
  color: #64748b;
}
.option-btn:active {
  transform: translateY(-1px);
}
</style>
