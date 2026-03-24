# personality_engine_plugin

`personality_engine_plugin` 是一个按聊天流隔离的人格演化插件。  
它会在对话推进过程中维护 MBTI + 八功能权重状态，并把当前“人格态摘要”注入到 system prompt。

## 功能概览

- 按 `stream_id` 维护人格状态（私聊/群聊/讨论组互不污染）
- 基于聊天推进自动触发人格更新
- 支持 LLM 选择当前补偿功能（可关闭，关闭后走启发式）
- 支持主辅互换 / 主变更 / 辅变更 / 重构四类反思规则
- 在 `on_prompt_build` 阶段注入人格态摘要
- 提供命令查看、手动推进、重置、设置 MBTI

## 目录结构

```text
personality_engine_plugin/
├── manifest.json
├── plugin.py
├── config.py
├── service.py
├── prompts.py
├── commands/
│   └── personality_command.py
└── components/
    └── events/
        ├── personality_scan_event.py
        └── personality_prompt_injector.py
```

## 配置文件

路径：

`config/plugins/personality_engine_plugin/config.toml`

重点配置：

- `[plugin]`
  - `enabled`: 是否启用插件
  - `inject_prompt`: 是否注入人格态到 prompt
- `[scan]`
  - `trigger_every_n_messages`: 每隔多少轮对话触发一次人格推进
  - `max_context_messages`: 推进时读取最近多少条消息
- `[model]`
  - `task_name`: 人格推进模型任务名（默认 `diary`）
  - `fallback_task_name`: 回退任务名（默认 `actor`）
  - `enable_llm_selector`: 是否启用 LLM 功能选择
- `[personality]`
  - `default_mbti`: 默认 MBTI
  - `change_weight`: 每轮补偿增量
  - `change_history_decay`: 未触发结构变化时衰减系数
  - `normalize_main_threshold`: 主功能归一化阈值
  - `max_parse_retries`: LLM 输出解析重试次数
- `[prompt]`
  - `target_prompt_names`: 允许注入的模板名
  - `prompt_title`: 注入块标题
  - `inject_detail_level`: `compact` 或 `detail`

## 运行机制

### 1) 自动推进

事件处理器 `personality_scan_event` 订阅 `ON_CHATTER_STEP_RESULT`。  
达到阈值后调用 service 推进人格状态。

### 2) Prompt 注入

事件处理器 `personality_prompt_injector` 订阅 `on_prompt_build`。  
默认对 `default_chatter_system_prompt` 的 `extra_info` 追加人格态块。

### 3) 人格更新流程

1. 收集最近消息上下文
2. 选择本轮补偿功能（LLM 或启发式）
3. 更新 `change_history`
4. 按规则执行反思分支（结构变化或衰减）
5. 落盘并返回摘要

## 命令

- `/personality view`
- `/personality advance`
- `/personality reset`
- `/personality set_mbti <MBTI>`

## 数据存储

默认路径：

- `data/personality_engine/private/<stream_id>.json`
- `data/personality_engine/group/<stream_id>.json`
- `data/personality_engine/discuss/<stream_id>.json`

状态内容包括：当前 MBTI、八功能权重、变更历史、最近补偿功能、当前假设与结构变化日志。

