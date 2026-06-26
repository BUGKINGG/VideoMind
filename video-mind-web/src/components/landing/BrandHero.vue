<template>
  <div class="brand-hero">
    <div class="brand-content">
      <!-- Logo -->
      <div class="logo-wrap">
        <img src="/videomind.svg" alt="VideoMind Logo" class="logo" />
      </div>

      <!-- Title -->
      <h1 class="title">
        <span class="title-gradient">VideoMind</span>
      </h1>

      <!-- Subtitle -->
      <p class="subtitle">AI 视频助手 — 让每一个视频都值得被理解</p>

      <!-- Feature list -->
      <ul class="features">
        <li class="feature-item">
          <span class="feature-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
              <line x1="16" y1="13" x2="8" y2="13"/>
              <line x1="16" y1="17" x2="8" y2="17"/>
            </svg>
          </span>
          <div class="feature-text">
            <strong>AI 视频总结</strong>
            <span>智能分析视频内容，生成结构化摘要</span>
          </div>
        </li>
        <li class="feature-item">
          <span class="feature-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
          </span>
          <div class="feature-text">
            <strong>智能对话</strong>
            <span>基于视频内容与  AI  进行自然语言问答</span>
          </div>
        </li>
        <li class="feature-item">
          <span class="feature-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <rect x="3" y="3" width="18" height="18" rx="3" ry="3"/>
              <circle cx="8.5" cy="8.5" r="1.5"/>
              <polyline points="21 15 16 10 5 21"/>
            </svg>
          </span>
          <div class="feature-text">
            <strong>多源支持</strong>
            <span>支持 B 站视频链接，使用 Cookie 绑定</span>
          </div>
        </li>
        <li class="feature-item">
          <span class="feature-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
            </svg>
          </span>
          <div class="feature-text">
            <strong>深色模式</strong>
            <span>内置暗色深色主题，保护您的用眼健康</span>
          </div>
        </li>
      </ul>

      <!-- Footer note -->
      <p class="footer-note">
        开源项目 ·
        <a href="https://github.com/BUGKINGG/VideoMind" target="_blank" rel="noopener">GitHub</a>
      </p>
    </div>
  </div>
</template>

<style scoped>
.brand-hero {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px 32px 48px 48px;
  z-index: 1;
  position: relative;
}

.brand-content {
  width: 390px;
}

/* ── Logo ── */
.logo-wrap {
  margin-bottom: 20px;
}
.logo {
  width: 52px;
  height: 52px;
  filter: drop-shadow(0 4px 12px rgba(102, 126, 234, 0.25));
  animation: logo-float 3s ease-in-out infinite;
}
@keyframes logo-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-5px); }
}

/* ── Title ── */
.title {
  margin: 0 0 12px;
  font-size: 48px;
  font-weight: 750;
  letter-spacing: -1.5px;
  line-height: 1.15;
}
.title-gradient {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 40%, #a855f7 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

/* ── Subtitle ── */
.subtitle {
  margin: 0 0 44px;
  font-size: 17px;
  color: #64748b;
  line-height: 1.5;
}

/* ── Features ── */
.features {
  list-style: none;
  padding: 0;
  margin: 0 0 44px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 50px;
}

.feature-icon {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  margin-top: 1px;
  border-radius: 10px;
  background: rgba(99, 102, 241, 0.08);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366f1;
}
.feature-icon svg {
  width: 20px;
  height: 20px;
}

.feature-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.4;
}
.feature-text strong {
  font-size: 15px;
  color: #1e293b;
  font-weight: 600;
}
.feature-text span {
  font-size: 13.5px;
  color: #94a3b8;
}

/* ── Footer ── */
.footer-note {
  font-size: 13px;
  color: #c0c8d4;
}
.footer-note a {
  color: #a5b4fc;
  text-decoration: none;
  transition: color 0.2s;
}
.footer-note a:hover {
  color: #6366f1;
}

/* ── Mobile ── */
@media (max-width: 768px) {
  .brand-hero {
    padding: 36px 28px;
    text-align: center;
  }
  .brand-content {
    width: 100%;
  }
  .title {
    font-size: 34px;
  }
  .subtitle {
    font-size: 15px;
    margin-bottom: 32px;
  }
  .features {
    gap: 16px;
    margin-bottom: 28px;
  }
  .feature-item {
    justify-content: flex-start;
    text-align: left;
  }
  .feature-text strong {
    font-size: 14px;
  }
  .feature-text span {
    font-size: 12.5px;
  }
  .logo {
    width: 42px;
    height: 42px;
  }
}
</style>
