<template>
  <div v-if="modelValue" class="modal-overlay" @click.self="close">
    <div class="modal-card">
      <h3>关于 VideoMind</h3>
      <div class="about-content">
        <p><strong>VideoMind</strong> — 视频学习总结助手</p>
        <p>版本：v0.1.0</p>
        <p>基于 AI Agent 技术，支持字幕提取、结构化总结与多模态时间戳分析。</p>
        <p>如有疑问请联系：</p>
        <p>麦生：1062362280@qq.com</p>
        <p>麦生：1924153440@qq.com</p>
      </div>
      <div class="modal-actions">
        <button class="modal-btn primary" @click="close">知道了</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()

function close() {
  emit('update:modelValue', false)
}
</script>

<style scoped>
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
</style>