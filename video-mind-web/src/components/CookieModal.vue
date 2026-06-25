<template>
  <div v-if="modelValue" class="modal-overlay" @click.self="close">
    <div class="modal-card">
      <h3>绑定 Cookie</h3>
      <p class="modal-hint">粘贴你从浏览器开发者工具中复制的 Cookie 字符串</p>
      <textarea
          :value="cookieValue"
          @input="handleInput"
          class="modal-textarea"
          rows="4"
          placeholder="例如: SESSDATA=xxx; bili_jct=yyy..."
      ></textarea>
      <div class="modal-actions">
        <button class="modal-btn secondary" @click="close">取消</button>
        <button class="modal-btn primary" @click="save">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  modelValue: boolean
  cookieValue: string
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  'update:cookieValue': [value: string]
  save: []
}>()

function handleInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  emit('update:cookieValue', target.value)
}

function close() {
  emit('update:modelValue', false)
}

function save() {
  if (!props.cookieValue.trim()) {
    alert('请输入 cookie！')
    return
  }
  emit('save')
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
