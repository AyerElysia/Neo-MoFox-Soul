# 附录 B · 配置参数全表

> **用途**：为 Life Engine 的所有可配置参数提供完整参考，每项包含默认值、单位/范围、实际影响。  
> **配置文件路径**：`plugins/life_engine/core/config.py`  
> **加载方式**：通过 TOML 配置文件（如 `config.toml`）覆盖默认值

---

## B.1 核心设置（settings）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `enabled` | bool | `True` | — | 是否启用 Life Engine 插件，关闭时所有子系统停止 |
| `heartbeat_interval_seconds` | int | `30` | 秒（建议 10~120） | 心跳触发间隔，过小会增加 LLM 调用成本，过大会降低响应性 |
| `sleep_time` | str | `""` | `HH:MM` 格式 | 睡觉时间，留空则不主动睡眠（如 `"23:00"`） |
| `wake_time` | str | `""` | `HH:MM` 格式 | 苏醒时间，留空则不主动唤醒（如 `"07:00"`） |
| `log_heartbeat` | bool | `True` | — | 是否记录每次心跳日志到 `logs/life_engine.log` |
| `context_history_max_events` | int | `100` | 事件数 | 事件历史缓存上限，超出后最旧事件会被丢弃 |
| `workspace_path` | str | `data/life_engine_workspace` | 路径 | 持久化文件根目录（存放 `life_engine_context.json`、`dream_log.json` 等） |
| `max_rounds_per_heartbeat` | int | `3` | 轮数 | 单次心跳内工具调用的最大嵌套深度，防止死循环 |
| `idle_pause_after_external_silence_minutes` | int | `30` | 分钟（0=禁用） | 外界静默超过此时长后暂停 LLM 心跳（节省成本），设为 0 则永不暂停 |

---

## B.2 模型配置（model）

| 参数名 | 类型 | 默认值 | 含义与影响 |
|--------|------|--------|-----------|
| `task_name` | str | `"life"` | 模型任务名，用于区分不同 LLM 调用任务（与 kernel 层 `ModelSet` 配置关联） |

---

## B.3 历史检索（history_retrieval）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `enabled` | bool | `True` | — | 是否启用历史检索工具（`search_chat_history`） |
| `default_cross_stream` | bool | `False` | — | 默认是否跨流检索（跨流会扫描多个聊天流） |
| `adapter_signature` | str | `napcat_adapter...` | 组件签名 | 聊天历史适配器的组件签名，用于获取外部平台历史记录 |
| `adapter_timeout_seconds` | int | `8` | 秒 | 调用适配器的超时时间 |
| `max_candidate_streams` | int | `12` | 流数 | 跨流检索时最多扫描的流数量 |
| `max_scan_rows_per_stream` | int | `240` | 行数 | 每个流最多扫描的消息行数 |
| `tool_default_limit` | int | `20` | 条数 | 检索工具默认返回的结果条数 |
| `tool_max_limit` | int | `100` | 条数 | 检索工具允许的最大返回条数（防止 prompt 过长） |

---

## B.4 网络搜索（web）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `tavily_api_key` | str | `""` | API Key | Tavily 搜索 API 密钥（留空则无法使用网页搜索） |
| `tavily_api_keys` | list[str] | `[]` | API Keys | 多 Key 轮询列表，提高搜索请求配额 |
| `tavily_base_url` | str | `https://api.tavily.com` | URL | Tavily API 地址（支持自建镜像） |
| `search_timeout_seconds` | int | `30` | 秒 | 搜索请求超时时间 |
| `extract_timeout_seconds` | int | `60` | 秒 | 网页内容提取超时时间 |
| `default_search_max_results` | int | `5` | 条数 | 默认返回的搜索结果数量 |
| `default_fetch_max_chars` | int | `12000` | 字符数 | 网页提取的最大字符数（避免 prompt 溢出） |

---

## B.5 脉冲神经网络（snn）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `enabled` | bool | `False` | — | 是否启用 SNN（默认关闭，实验性功能） |
| `shadow_only` | bool | `True` | — | 影子模式：SNN 运行但不注入 prompt（仅用于调试/数据收集） |
| `tick_interval_seconds` | float | `10.0` | 秒 | SNN 独立 tick 间隔（与心跳异步） |
| `inject_to_heartbeat` | bool | `False` | — | 是否将驱动信号注入心跳 prompt（需 `shadow_only=False` 时才有效） |
| `feature_window_seconds` | float | `600.0` | 秒 | 特征提取窗口（从事件历史中提取最近 10 分钟的特征） |

**注意**：SNN 默认不启用（`enabled=False`），生产环境下作为研究性功能。

---

## B.6 神经调质（neuromod）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `enabled` | bool | `True` | — | 是否启用调质层（控制 `curiosity/sociability/focus/contentment/energy` 五因子） |
| `inject_to_heartbeat` | bool | `True` | — | 是否将调质状态注入心跳 prompt（默认启用，显著影响行为决策） |
| `habit_tracking` | bool | `True` | — | 是否启用习惯追踪系统（记录日常行为的 streak 与 strength） |

---

## B.7 做梦系统（dream）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `enabled` | bool | `True` | — | 是否启用做梦系统 |
| `nrem_replay_episodes` | int | `3` | 集数 | NREM 阶段回放的事件片段数 |
| `nrem_events_per_episode` | int | `20` | 事件数 | 每集事件片段包含的事件数量 |
| `nrem_speed_multiplier` | float | `5.0` | 倍率 | NREM 回放时 SNN 的加速倍率（快速巩固） |
| `nrem_homeostatic_rate` | float | `0.02` | 比例 | SHY 突触稳态缩减比例（2% 全局缩减） |
| `rem_walk_rounds` | int | `2` | 轮数 | REM 阶段激活扩散游走的轮数 |
| `rem_seeds_per_round` | int | `5` | 种子数 | 每轮游走的起始种子数量 |
| `rem_max_depth` | int | `3` | 跳数 | 激活扩散的最大深度 |
| `rem_decay_factor` | float | `0.6` | 衰减因子 | 每跳激活强度的衰减系数 |
| `rem_learning_rate` | float | `0.05` | 学习率 | REM 阶段 Hebbian 强化的学习率 |
| `rem_edge_prune_threshold` | float | `0.08` | 阈值 | REM 后弱边修剪的阈值（强度 < 0.08 的边会被删除） |
| `dream_interval_minutes` | int | `90` | 分钟 | 两次做梦之间的最小间隔 |
| `idle_trigger_heartbeats` | int | `10` | 次数 | 白天空闲超过此心跳数时触发小憩做梦（需 `nap_enabled=True`） |
| `nap_enabled` | bool | `True` | — | 是否启用白天小憩做梦 |

---

## B.8 阈值设定（thresholds）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `external_active_minutes` | int | `5` | 分钟 | 外部消息的"活跃窗口"，用于判断最近是否有外部交互 |
| `idle_warning_threshold` | int | `5` | 次数 | 空闲心跳次数达到此值时触发警告级别（日志/内部状态） |
| `idle_critical_threshold` | int | `12` | 次数 | 空闲心跳次数达到此值时触发严重警告（可能暂停 LLM） |
| `todo_urgent_days` | int | `3` | 天数 | TODO 截止日期小于此天数时标记为"紧急" |

---

## B.9 记忆算法（memory_algorithm）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `rrf_k` | int | `60` | RRF 常数 | 倒数排名融合公式的常数 k（`score = 1/(k+rank)`） |
| `spread_decay` | float | `0.7` | 衰减因子 | 激活扩散每跳的衰减系数 |
| `spread_threshold` | float | `0.3` | 阈值 | 激活扩散停止条件（激活强度 < 0.3 时停止传播） |
| `decay_lambda` | float | `0.05` | 衰减系数 | Ebbinghaus 遗忘曲线的衰减参数 λ（每天衰减 5%） |
| `prune_threshold` | float | `0.1` | 阈值 | 边强度低于此值时执行剪枝（删除弱边） |
| `dream_learning_rate` | float | `0.05` | 学习率 | 做梦时记忆边的 Hebbian 学习率 |

---

## B.10 对话模式（chatter）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `enabled` | bool | `False` | — | 是否启用 DFC 的对话模式（Life Engine 主要通过工具与 DFC 交互，此项一般关闭） |
| `mode` | str | `"enhanced"` | `enhanced/classical` | 对话模式：`enhanced` 支持工具调用，`classical` 仅纯文本 |
| `max_rounds_per_chat` | int | `5` | 轮数 | 单轮对话的最大工具调用轮数 |
| `initial_history_messages` | int | `30` | 消息数 | 对话首轮注入的历史消息数量 |

---

## B.11 思考流（streams）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `enabled` | bool | `True` | — | 是否启用思考流系统 |
| `max_active_streams` | int | `5` | 流数 | 活跃思考流的上限（超出后最旧的流会休眠） |
| `dormancy_threshold_hours` | int | `24` | 小时 | 思考流未更新超过此时长后自动休眠 |
| `inject_to_heartbeat` | bool | `True` | — | 是否将活跃思考流的摘要注入心跳 prompt |

---

## B.12 冲动引擎（drives）

| 参数名 | 类型 | 默认值 | 单位/范围 | 含义与影响 |
|--------|------|--------|-----------|-----------|
| `enabled` | bool | `True` | — | 是否启用冲动引擎（将调质因子转化为行动倾向） |
| `inject_to_heartbeat` | bool | `True` | — | 是否将冲动状态注入心跳 prompt |
| `curiosity_threshold` | float | `0.65` | 阈值 [0~1] | `curiosity` 超过此值时触发探索冲动 |
| `sociability_threshold` | float | `0.6` | 阈值 [0~1] | `sociability` 超过此值时触发社交冲动 |
| `silence_trigger_minutes` | int | `30` | 分钟 | 外界静默超过此时长时增强社交冲动 |

---

## 使用建议

### B.12.1 生产环境推荐配置

**基础配置**（适合初次部署）：
```toml
[life_engine.settings]
heartbeat_interval_seconds = 30
idle_pause_after_external_silence_minutes = 60  # 1小时后暂停
context_history_max_events = 100

[life_engine.neuromod]
enabled = true
inject_to_heartbeat = true

[life_engine.dream]
enabled = true
dream_interval_minutes = 120  # 2小时一次

[life_engine.snn]
enabled = false  # 生产环境建议保持关闭
```

**高频交互配置**（适合活跃社群）：
```toml
[life_engine.settings]
heartbeat_interval_seconds = 20  # 更快响应
idle_pause_after_external_silence_minutes = 0  # 永不暂停

[life_engine.drives]
curiosity_threshold = 0.55  # 更易触发探索
sociability_threshold = 0.5  # 更易发起社交
```

### B.12.2 参数调优指南

1. **性能调优**
   - `heartbeat_interval_seconds`：减小值提升响应性，但会增加 LLM 成本
   - `max_rounds_per_heartbeat`：增大允许更复杂推理，但可能超时
   - `idle_pause_after_external_silence_minutes`：合理设置可显著降低成本

2. **行为调优**
   - `curiosity_threshold/sociability_threshold`：降低阈值使系统更主动
   - `dream_interval_minutes`：过短会频繁做梦，过长会导致记忆整合延迟
   - `inject_to_heartbeat`（多处）：关闭某些注入可简化 prompt，但会失去相应能力

3. **记忆调优**
   - `decay_lambda`：增大加速遗忘，减小保持长期记忆
   - `prune_threshold`：增大会删除更多弱边（保持图稀疏），减小保留更多关联
   - `rrf_k`：增大会降低排名差异的权重

### B.12.3 配置热重载

当前配置**不支持热重载**，修改后需重启 Life Engine：
```bash
# 停止服务
systemctl stop neo-mofox

# 编辑配置
vim config.toml

# 启动服务
systemctl start neo-mofox
```

### B.12.4 配置验证

修改配置后建议通过日志验证：
```bash
# 查看启动日志
tail -f logs/life_engine.log | grep "Config loaded"

# 查看心跳日志（确认参数生效）
tail -f logs/life_engine.log | grep "heartbeat_interval"
```

---

**版本信息**  
- 参数总数：72 项  
- 配置文件版本：v1.0  
- 最后更新：2025-01-15  
- 文档维护：Neo-MoFox 报告撰写组
