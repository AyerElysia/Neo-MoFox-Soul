<template>
  <div class="welcome-page">
    <div class="card m3-card">
      <div class="welcome-content">
        <!-- 问候语 -->
        <div class="greeting">
          <h2 class="title">{{ greetingMessage }}</h2>
          <p class="subtitle">欢迎使用 MoFox Bot 配置向导</p>
        </div>

        <!-- 介绍文本 -->
        <div class="intro">
          <p class="intro-text">
            让我们花几分钟时间，完成 MoFox Bot 的基础配置。
            这将包括：
          </p>

          <ul class="feature-list">
            <li>
              <span class="material-symbols-rounded icon">smart_toy</span>
              <div>
                <strong>机器人配置</strong>
                <span>设置昵称、人格和回复风格</span>
              </div>
            </li>
            <li>
              <span class="material-symbols-rounded icon">psychology</span>
              <div>
                <strong>AI 模型配置</strong>
                <span>快速接入 SiliconFlow API</span>
              </div>
            </li>
            <li>
              <span class="material-symbols-rounded icon">deployed_code</span>
              <div>
                <strong>Git 配置</strong>
                <span>启用系统自动更新功能</span>
              </div>
            </li>
          </ul>
        </div>

        <!-- 提示信息 -->
        <div class="hint">
          <span class="material-symbols-rounded">info</span>
          <span>配置过程中，所有修改都会自动备份</span>
        </div>

        <!-- 开始按钮 -->
        <button class="m3-button filled" @click="$emit('next')">
          <span>开始配置</span>
          <span class="material-symbols-rounded">arrow_forward</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

defineEmits<{
  next: []
}>()

// 根据时间生成问候语
const greetingMessage = computed(() => {
  const hour = new Date().getHours()

  if (hour >= 5 && hour < 12) {
    return '早上好！☀️'
  } else if (hour >= 12 && hour < 18) {
    return '下午好！🌤️'
  } else if (hour >= 18 && hour < 22) {
    return '晚上好！🌙'
  } else {
    return '夜深了！✨'
  }
})
</script>

<style scoped>
.welcome-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 500px;
  animation: fadeIn 0.5s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.card {
  width: 100%;
  max-width: 600px;
  padding: 48px;
  background: var(--md-sys-color-surface);
  border-radius: 28px;
  box-shadow: var(--md-sys-elevation-2);
}

.welcome-content {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* 问候语 */
.greeting {
  text-align: center;
}

.title {
  font-size: 32px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  margin: 0 0 8px 0;
}

.subtitle {
  font-size: 18px;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0;
}

/* 介绍 */
.intro {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.intro-text {
  font-size: 16px;
  line-height: 1.6;
  color: var(--md-sys-color-on-surface);
  margin: 0;
}

/* 功能列表 */
.feature-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.feature-list li {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  background: var(--md-sys-color-surface-variant);
  border-radius: 16px;
}

.feature-list .icon {
  font-size: 32px;
  color: var(--md-sys-color-primary);
  flex-shrink: 0;
}

.feature-list strong {
  display: block;
  font-size: 16px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  margin-bottom: 4px;
}

.feature-list span:not(.icon) {
  font-size: 14px;
  color: var(--md-sys-color-on-surface-variant);
}

/* 提示 */
.hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  background: var(--md-sys-color-secondary-container);
  color: var(--md-sys-color-on-secondary-container);
  border-radius: 12px;
  font-size: 14px;
}

.hint .material-symbols-rounded {
  font-size: 20px;
}

/* 按钮 */
.m3-button {
  align-self: center;
  padding: 14px 32px;
  font-size: 16px;
  font-weight: 600;
  border: none;
  border-radius: 100px;
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.m3-button.filled {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  box-shadow: var(--md-sys-elevation-1);
}

.m3-button.filled:hover {
  box-shadow: var(--md-sys-elevation-2);
  transform: scale(1.02);
}

.m3-button.filled:active {
  transform: scale(0.98);
}

.m3-button .material-symbols-rounded {
  font-size: 20px;
}

/* 响应式 */
@media (max-width: 768px) {
  .card {
    padding: 32px 24px;
  }

  .title {
    font-size: 28px;
  }

  .subtitle {
    font-size: 16px;
  }

  .feature-list .icon {
    font-size: 28px;
  }
}
</style>
