<template>
  <div class="options-view">
    <div class="options-header">
      <h2>设置</h2>
      <button class="back-btn" @click="$emit('back')">← 返回</button>
    </div>
    <div class="options-body">
      <div class="option-item" @click="$emit('showCookie')">
        <div class="option-icon">🍪</div>
        <div class="option-text">
          <div class="option-title">绑定 / 修改 Cookie</div>
          <div class="option-desc">用于获取视频平台的字幕和元数据</div>
        </div>
        <div class="option-arrow">›</div>
      </div>
      <div class="option-item" @click="$emit('showAbout')">
        <div class="option-icon">ℹ️</div>
        <div class="option-text">
          <div class="option-title">关于 VideoMind</div>
          <div class="option-desc">版本信息、开源协议与致谢</div>
        </div>
        <div class="option-arrow">›</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
defineEmits(['back', 'showCookie', 'showAbout'])
</script>

<style scoped>
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
</style>