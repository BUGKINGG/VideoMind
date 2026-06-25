<template>
  <div class="profile-card">
    <div class="avatar">{{ initials }}</div>
    <div class="profile-info">
      <div class="profile-name">{{ userName }}</div>
      <div class="profile-uid">UID: {{ userUid }}</div>
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
.option-btn {
  background: white;
  border: none;
  font-size: 15px;
  color: #757474;
  border-radius: 12px;
  transition-duration: 0.2s;
  margin-left: 50px;
  width: 50px;
  height: 30px;
}
.option-btn:hover {
  background: #e8e5e5;
}
.option-btn:active {
  transform: translateY(-3px);
}
</style>
