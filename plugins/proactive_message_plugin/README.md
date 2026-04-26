# 主动消息插件 (Proactive Message Plugin)

让 `life_chatter` 在外界长时间沉默时，获得一次“要不要自然开口”的主动机会。

这份文档描述的是当前架构：`proactive_message_plugin` 不再维护一套私有的内心独白 Prompt，也不再把独白伪装成聊天历史消息；主动机会、延迟续话、内心独白都统一回到 `life_chatter` 主链路处理。

## 当前设计

- `proactive_message_plugin` 负责：
  - 计时
  - 触发主动机会 / 延迟续话机会
  - 调度后续检查
- `life_chatter` 负责：
  - 用统一的人设 / SOUL / MEMORY / 运行态上下文做判断
  - 决定回复还是继续等待
  - 在主动机会轮次先调用 `action-record_inner_monologue`
- `life_engine` 负责：
  - 把这类独白写入统一事件流
  - 在后续轮次按流增量同步给 `life_chatter`

## 核心变化

### 1. 不再有私有 `inner_monologue.py`

旧设计里，主动插件会单独起一套 Prompt 生成“内心独白 + 决策”，这会导致：

- 独白和对外说话不是同一个主体上下文
- 上下文缓存不友好
- 独白容易和 `life_chatter` 当前状态脱节

现在这条链路已经移除。主动插件只负责创造机会，不再自己思考。

### 2. 不再把独白写进 `history_messages`

旧设计会把独白作为 `is_inner_monologue=True` 的消息塞进聊天历史。这样会污染真实对话链，也容易在长连接中反复重复。

现在独白改为写入 `life_engine` 事件流：

- 类型：`HEARTBEAT`
- `content_type="chatter_inner_monologue"`
- 按 `stream_id` 归属到具体会话

这样它既能被后续轮次看到，又不会破坏聊天历史的形状。

### 3. 主动机会轮次强制先记录独白

当主动机会或延迟续话机会唤醒 `life_chatter` 时，提示会明确要求：

1. 先调用 `action-record_inner_monologue`
2. 再决定：
   - 回复用户
   - 或 `action-life_pass_and_wait`

如果本轮跳过了 `action-record_inner_monologue`，`life_chatter` 会进行有限重试提醒。

## 工作流程

```text
收到外界消息
    ↓
proactive 插件开始计时
    ↓
到达首次等待阈值 / 延迟续话阈值
    ↓
写入一条“主动机会”或“续话机会”触发消息
    ↓
唤醒 life_chatter
    ↓
life_chatter 先记录 action-record_inner_monologue
    ↓
再决定：回复 / 继续等待
    ↓
独白写入 life_engine 事件流，供后续轮次增量同步
```

## 配置

配置文件：`config/plugins/proactive_message_plugin/config.toml`

```toml
[settings]
enabled = true

# 兼容旧配置保留字段。当前统一由 chatter 处理，建议保持 chatter。
decision_mode = "chatter"

# 收到外界消息后，多久触发第一次主动机会
first_check_minutes = 10

# 当本轮选择继续等待时，最小等待间隔
min_wait_interval_minutes = 5

# 最长等待上限，避免无限拖延
max_wait_minutes = 180

# 主动发出消息后，如果对方仍没回复，多久再给一次机会
post_send_followup_minutes = 10

# 对话器拿到主动机会但决定不回复后，下次再检查的间隔
declined_opportunity_wait_minutes = 30

# 是否允许登记“过一会儿再补一句”
followup_enabled = true
followup_min_delay_seconds = 20
followup_max_delay_seconds = 90
followup_max_chain_count = 2
followup_cooldown_minutes = 10

# 已废弃，仅兼容旧配置，不再生效
monologue_history_limit = 5

ignored_chat_types = ["group"]
```

## 暴露给模型的动作

### `action-record_inner_monologue`

由 `life_chatter` 调用，把当前轮新的心理推进记录回 `life_engine`。

参数：

- `thought`: 独白正文
- `mood`: 当前情绪，可选
- `intent`: 当前倾向，可选
- `topic`: 围绕话题，可选

### `schedule_followup_message`

登记一条延迟续话计划。不会立刻发消息，只会在稍后给 `life_chatter` 一次新的机会。

参数：

- `delay_seconds`
- `thought`
- `topic`
- `followup_type`

### `wait_longer`

当这一轮决定先不说话，继续等待时使用。

## 上下文可见性

当前可见性分为两层：

1. **聊天历史**
   - 只保留真实的对外消息
   - 不包含主动机会触发消息
   - 不包含延迟续话触发消息
   - 不包含旧式“伪聊天消息”的内心独白

2. **life 运行态上下文**
   - 包含本流尚未被 `life_chatter` 看过的事件
   - 包含主动机会、延迟续话、工具结果、`chatter_inner_monologue`
   - 通过高水位游标做增量同步，避免整段历史反复注入

## 项目结构

```text
proactive_message_plugin/
├── actions/
│   └── schedule_followup_message.py
├── config.py
├── manifest.json
├── plugin.py
├── README.md
├── service.py
└── tools/
    └── wait_longer.py
```

## 设计边界

- 这个插件不再负责“私有思考”
- 这个插件不再直接生成内心独白文本
- 这个插件不再把独白注入聊天历史
- 真正的说与不说，统一由 `life_chatter` 决定

## 调试建议

排查主动链路时，重点看三类内容：

- `proactive_message_plugin` 是否按时注入了主动机会 / 续话机会
- `life_chatter` 是否先调用了 `action-record_inner_monologue`
- `life_engine` 事件流里是否出现了 `content_type="chatter_inner_monologue"`

如果第三步缺失，后续轮次就看不到这次内在推进。
