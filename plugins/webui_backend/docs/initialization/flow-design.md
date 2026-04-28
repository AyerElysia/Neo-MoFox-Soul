# 初始化流程设计

> 本文档描述 MoFox WebUI 初始化系统的完整流程和状态检测逻辑

---

## 📊 流程图

### 主流程

```
┌─────────────────┐
│  用户首次登录    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 检测初始化状态   │────┐ 已完成初始化
└────────┬────────┘    │
         │ 未初始化     │
         ▼             ▼
┌─────────────────┐  ┌─────────────────┐
│ 显示欢迎页面     │  │ 直接进入仪表盘   │
└────────┬────────┘  └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Step 1:         │
│ 机器人基础配置   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 2:         │
│ SiliconFlow API │
│ 配置            │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Step 3:         │
│ Git 路径配置     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 配置完成页面     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 进入仪表盘       │
└─────────────────┘
```

---

## 🔍 状态检测逻辑

系统启动时，执行以下检测步骤：

### 1. 初始化标记检测

**检测目标**: `backend_storage` 中的 `webui_initialized` 标记

**逻辑**:
```python
if backend_storage.get("webui_initialized") == True:
    # 已完成初始化，跳转到仪表盘
    redirect_to_dashboard()
else:
    # 未初始化，进入初始化流程
    start_initialization_wizard()
```

**API**: `GET /api/initialization/status`

---

### 2. 配置文件检测

针对每个配置步骤，检测对应的配置是否已存在。

#### Step 1: 机器人配置

**配置文件**: `config/bot_config.toml`

**加载逻辑**:
```python
# 尝试读取现有配置
config = {}
if os.path.exists("config/bot_config.toml"):
    config = load_toml("config/bot_config.toml")

# 返回配置数据（如果存在）供前端预填充
return {
    "nickname": config.get("bot", {}).get("nickname", ""),
    "personality_core": config.get("personality", {}).get("personality_core", ""),
    "identity": config.get("personality", {}).get("identity", ""),
    "master_users": config.get("permission", {}).get("master_users", [])
}
```

**显示给用户**:
- 如果存在配置文件，自动预填充表单字段
- 用户可以修改任意字段
- 页面底部提供操作按钮：`[保存配置] [跳过此步骤]`

**跳过逻辑**:
- 点击"跳过此步骤"直接进入下一步
- 不验证字段，不保存配置
- 跳过后标记该步骤状态为 `SKIPPED`

---

#### Step 2: 模型配置检测

**检测文件**: `config/model_config.toml`

**显示给用户**:
```
✅ 检测到已配置的 SiliconFlow API
API Key: sk-****1234

[保持原配置] [更新配置]
```

---

#### Step 3: Git 配置检测

**检测来源**:
1. `backend_storage.git_custom_path` (自定义路径)
2. 系统 PATH 中的 Git (自动检测)
3. 便携式 Git (项目内置)

**检测逻辑**:
```python
# 1. 检查自定义路径
custom_path = backend_storage.get_git_path()
if custom_path and is_valid_git_executable(custom_path):
    return {
        "git_detected": True,
        "git_path": custom_path,
        "git_version": get_git_version(custom_path),
        "source": "custom"
    }

# 2. 检查系统 Git
system_git = find_system_git()
if system_git:
    return {
        "git_detected": True,
        "git_path": system_git,
        "git_version": get_git_version(system_git),
        "source": "system"
    }

# 3. 检查便携式 Git
portable_git = find_portable_git()
if portable_git:
    return {
        "git_detected": True,
        "git_path": portable_git,
        "git_version": get_git_version(portable_git),
        "source": "portable"
    }

# 未检测到 Git
return {
    "git_detected": False,
    "git_path": None,
    "git_version": None,
    "source": None
}
```

**显示给用户**:

- **检测成功**:
```
✅ 已检测到系统 Git (v2.43.0)
路径: C:\Program Files\Git\bin\git.exe

💡 提示：如果自动检测成功，无需手动配置

[跳过此步骤]
```

- **检测失败**:
```
❌ 未检测到 Git

MoFox 使用 Git 进行系统更新和回滚。
请下载并安装 Git，或手动指定 Git 路径。

[📥 下载 Git] [📂 手动配置]
```

---

## 🎯 智能跳过策略

### 策略 1: 全局智能跳过

如果所有配置步骤都已完成，直接进入仪表盘：

```python
if all_steps_completed:
    backend_storage.set("webui_initialized", True)
    redirect_to_dashboard()
```

---

### 策略 2: 配置预填充与跳过

每个配置步骤都提供跳过功能：

**机器人配置 (Step 1)**:
- 如果存在配置文件，自动预填充表单
- 用户可以修改或保持原样
- 底部提供 `[保存配置]` 和 `[跳过此步骤]` 按钮

**模型配置 (Step 2)**:
- 如果已配置，预填充 API Key（脱敏显示）
- 提供 `[保存配置]` 和 `[跳过此步骤]` 按钮

**Git 配置 (Step 3)**:
- 自动检测 Git 路径
- 如果检测成功，提示用户可以跳过
- 提供 `[保存配置]` 和 `[跳过此步骤]` 按钮

---

### 配置表单 UI

```vue
┌─────────────────────────────────────┐
│  机器人基础配置                      │
├─────────────────────────────────────┤
│                                     │
│  昵称: [墨狐___________________]    │
│                                     │
│  核心人格:                          │
│  [是一个积极向上的女大学生_______]  │
│                                     │
│  Master 用户:                       │
│  [12345 ▼] [+ 添加]                │
│                                     │
│  💡 提示：如果已有配置，这里会自动    │
│  预填充。您可以修改或直接跳过。      │
│                                     │
│  [保存配置]       [跳过此步骤]      │
│                                     │
└─────────────────────────────────────┘
```

---

## 🔄 步骤导航逻辑

### 前进到下一步

**条件检查**:
```typescript
function canProceedToNextStep(): boolean {
  // 当前步骤必须通过验证
  if (!currentStepIsValid()) {
    showValidationErrors()
    return false
  }

  // 如果用户选择"跳过"，直接允许
  if (userChoseToSkip()) {
    return true
  }

  // 如果用户修改了配置，必须保存成功
  if (configWasModified() && !saveSuccessful()) {
    showSaveError()
    return false
  }

  return true
}
```

---

### 返回上一步

**允许条件**:
- 当前不是第一步（欢迎页面）
- 没有正在进行的保存操作

**行为**:
- 不丢失用户在当前步骤的输入
- 返回后重新加载上一步的状态

---

### 步骤跳转限制

**规则**:
1. 用户不能直接跳转到未解锁的步骤
2. 只有当前步骤完成后，才能进入下一步
3. 可以随时返回已完成的步骤修改配置

**状态标识**:
```typescript
enum StepStatus {
  LOCKED = 'locked',        // 未解锁
  CURRENT = 'current',      // 当前步骤
  COMPLETED = 'completed',  // 已完成
  SKIPPED = 'skipped'       // 已跳过
}
```

---

## 💾 配置保存策略

### 自动备份

**触发时机**: 保存配置前

---

### 原子性保存

**策略**: 先写临时文件，再原子性替换


---

## ✅ 初始化完成标记

### 完成条件

**所有步骤必须满足**:
1. Step 1: 机器人配置已保存
2. Step 2: 模型配置已保存（或跳过）
3. Step 3: Git 配置已保存（或跳过）

### 标记逻辑

```python
def mark_initialization_complete():
    backend_storage.set("webui_initialized", True)
    backend_storage.set("webui_initialized_at", datetime.now().isoformat())
    logger.info("初始化已完成")
```

### 完成后行为

1. **显示完成页面** (3秒)
   - 庆祝动画
   - 配置摘要
   - 小贴士

2. **自动跳转仪表盘**
   - 播放欢迎动画
   - 显示快速入门提示


---

## 📝 流程示例

### 场景 1: 全新用户

```
用户首次登录
  → 检测: webui_initialized = False
  → 显示欢迎页面
  → Step 1: 配置机器人 (表单为空，可填写或跳过)
  → Step 2: 配置模型 (表单为空，可填写或跳过)
  → Step 3: 检测到系统 Git，提示跳过
  → 完成页面
  → 设置 webui_initialized = True
  → 跳转仪表盘
```

---

### 场景 2: 配置了机器人但未完成初始化

```
用户重新登录
  → 检测: webui_initialized = False
  → 显示欢迎页面
  → Step 1: 读取已有配置，预填充表单
  → 用户选择跳过此步骤
  → Step 2: 配置模型
  → Step 3: 配置 Git
  → 完成
```

---

### 场景 3: 已完成初始化

```
用户登录
  → 检测: webui_initialized = True
  → 直接跳转仪表盘
```

---

## 🎯 关键性能指标

| 指标 | 目标值 |
|------|--------|
| 配置检测耗时 | < 500ms |
| 步骤切换动画 | 300ms |
| 配置保存响应 | < 2s |
| 初始化完成总时长 | < 5min (用户操作时间) |

---

**返回**: [README](./README.md) | **下一篇**: [UI 界面设计](./ui-design.md)
