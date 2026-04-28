<template>
  <div class="git-config-step">
    <div class="card m3-card">
      <div class="step-header">
        <h2 class="step-title">
          <span class="material-symbols-rounded">deployed_code</span>
          Git 配置
        </h2>
        <p class="step-description">配置 Git 以启用系统自动更新功能</p>
      </div>

      <form class="config-form" @submit.prevent="handleSubmit">
        <!-- Git 路径 -->
        <div class="form-field">
          <label class="field-label">
            <span class="material-symbols-rounded">folder</span>
            Git 可执行文件路径
          </label>
          <div class="input-with-action">
            <input
              v-model="formData.git_path"
              type="text"
              class="m3-input"
              placeholder="例如：C:\Program Files\Git\bin\git.exe"
            />
            <button
              type="button"
              class="detect-button"
              @click="autoDetectGit"
              :disabled="detecting"
            >
              <span class="material-symbols-rounded">{{ detecting ? 'progress_activity' : 'search' }}</span>
              <span>自动检测</span>
            </button>
          </div>
          <span class="field-hint">Git 程序的完整路径，用于执行更新操作</span>
        </div>

        <!-- 检测结果提示 -->
        <div v-if="detectMessage" :class="['detect-message', detectSuccess ? 'success' : 'error']">
          <span class="material-symbols-rounded">
            {{ detectSuccess ? 'check_circle' : 'error' }}
          </span>
          <span>{{ detectMessage }}</span>
        </div>

        <!-- 信息卡片 -->
        <div class="info-card">
          <div class="info-icon">
            <span class="material-symbols-rounded">info</span>
          </div>
          <div class="info-content">
            <h3>为什么需要配置 Git？</h3>
            <p>
              MoFox Bot 使用 Git 来拉取最新的代码更新，确保您始终使用最新的功能和修复。
            </p>
            <p class="hint-text">
              💡 如果您的系统中已安装 Git，点击"自动检测"按钮可以自动查找。
            </p>
          </div>
        </div>

        <!-- 按钮组 -->
        <div class="button-group">
          <button type="button" class="m3-button outlined" @click="$emit('skip')" :disabled="loading">
            <span>跳过此步</span>
          </button>
          <button type="submit" class="m3-button filled" :disabled="loading">
            <span v-if="!loading">保存并完成</span>
            <span v-else>保存中...</span>
            <span class="material-symbols-rounded">check</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { saveGitConfig, getGitConfig, detectGitPath, type GitConfigRequest } from '@/api/initialization'

const emit = defineEmits<{
  next: []
  skip: []
}>()

const loading = ref(false)
const detecting = ref(false)
const detectMessage = ref('')
const detectSuccess = ref(false)

const formData = ref<GitConfigRequest>({
  git_path: ''
})

async function loadExistingConfig() {
  try {
    const result = await getGitConfig()
    const configData = (result.data as any)?.data
    if (result.success && configData?.git_path) {
      formData.value.git_path = configData.git_path
    }
  } catch (error) {
    console.error('[GitConfigStep] 加载 Git 配置失败:', error)
  }
}

onMounted(() => {
  loadExistingConfig()
})

async function autoDetectGit() {
  detecting.value = true
  detectMessage.value = ''

  try {
    const result = await detectGitPath()
    if (result.success && result.data?.found && result.data.path) {
      formData.value.git_path = result.data.path
      detectMessage.value = '✓ 已找到 Git'
      detectSuccess.value = true
    } else {
      detectMessage.value = '未找到 Git，请手动输入路径'
      detectSuccess.value = false
    }
  } catch (error) {
    detectMessage.value = '检测失败，请手动输入路径'
    detectSuccess.value = false
  } finally {
    detecting.value = false
  }
}

async function handleSubmit() {
  loading.value = true
  try {
    const result = await saveGitConfig(formData.value)
    if (result.success) {
      emit('next')
    } else {
      alert('保存失败：' + (result.error || '未知错误'))
    }
  } catch (error) {
    alert('保存失败，请检查网络连接')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.git-config-step {
  display: flex;
  justify-content: center;
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
  max-width: 700px;
  padding: 40px;
  background: var(--md-sys-color-surface);
  border-radius: 28px;
  box-shadow: var(--md-sys-elevation-2);
}

/* 步骤头部 */
.step-header {
  margin-bottom: 32px;
  text-align: center;
}

.step-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  font-size: 28px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
  margin: 0 0 8px 0;
}

.step-title .material-symbols-rounded {
  font-size: 32px;
  color: var(--md-sys-color-primary);
}

.step-description {
  font-size: 16px;
  color: var(--md-sys-color-on-surface-variant);
  margin: 0;
}

/* 表单 */
.config-form {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.field-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--md-sys-color-on-surface);
}

.field-label .material-symbols-rounded {
  font-size: 20px;
  color: var(--md-sys-color-primary);
}

.input-with-action {
  display: flex;
  gap: 12px;
  align-items: center;
}

.m3-input {
  flex: 1;
  padding: 14px 16px;
  font-size: 16px;
  font-family: inherit;
  color: var(--md-sys-color-on-surface);
  background: var(--md-sys-color-surface-variant);
  border: 2px solid transparent;
  border-radius: 12px;
  outline: none;
  transition: all 0.2s ease;
}

.m3-input:focus {
  border-color: var(--md-sys-color-primary);
  background: var(--md-sys-color-surface);
}

.detect-button {
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 6px;
  border: 2px solid var(--md-sys-color-outline);
  background: transparent;
  color: var(--md-sys-color-primary);
  border-radius: 100px;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.detect-button:hover:not(:disabled) {
  background: var(--md-sys-color-surface-variant);
}

.detect-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.detect-button .material-symbols-rounded {
  font-size: 18px;
}

.field-hint {
  font-size: 12px;
  color: var(--md-sys-color-on-surface-variant);
  margin-left: 4px;
}

/* 检测结果消息 */
.detect-message {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 14px;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.detect-message.success {
  background: var(--md-sys-color-tertiary-container);
  color: var(--md-sys-color-on-tertiary-container);
}

.detect-message.error {
  background: var(--md-sys-color-error-container);
  color: var(--md-sys-color-on-error-container);
}

.detect-message .material-symbols-rounded {
  font-size: 20px;
}

/* 信息卡片 */
.info-card {
  display: flex;
  gap: 16px;
  padding: 20px;
  background: var(--md-sys-color-secondary-container);
  border-radius: 16px;
}

.info-icon {
  flex-shrink: 0;
}

.info-icon .material-symbols-rounded {
  font-size: 32px;
  color: var(--md-sys-color-on-secondary-container);
}

.info-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: var(--md-sys-color-on-secondary-container);
  margin: 0 0 8px 0;
}

.info-content p {
  font-size: 14px;
  line-height: 1.6;
  color: var(--md-sys-color-on-secondary-container);
  margin: 0 0 8px 0;
}

.info-content p:last-child {
  margin-bottom: 0;
}

.hint-text {
  font-size: 13px;
  opacity: 0.9;
}

/* 按钮组 */
.button-group {
  display: flex;
  gap: 16px;
  justify-content: center;
  margin-top: 16px;
}

.m3-button {
  padding: 12px 28px;
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

.m3-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.m3-button.filled {
  background: var(--md-sys-color-primary);
  color: var(--md-sys-color-on-primary);
  box-shadow: var(--md-sys-elevation-1);
}

.m3-button.filled:hover:not(:disabled) {
  box-shadow: var(--md-sys-elevation-2);
  transform: scale(1.02);
}

.m3-button.outlined {
  background: transparent;
  color: var(--md-sys-color-primary);
  border: 2px solid var(--md-sys-color-outline);
}

.m3-button.outlined:hover:not(:disabled) {
  background: var(--md-sys-color-surface-variant);
}

.m3-button .material-symbols-rounded {
  font-size: 20px;
}

/* 响应式 */
@media (max-width: 768px) {
  .card {
    padding: 32px 24px;
  }

  .step-title {
    font-size: 24px;
  }

  .input-with-action {
    flex-direction: column;
    align-items: stretch;
  }

  .detect-button {
    justify-content: center;
  }

  .info-card {
    flex-direction: column;
  }

  .button-group {
    flex-direction: column;
  }
}
</style>
