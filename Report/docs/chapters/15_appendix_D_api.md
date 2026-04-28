# 附录 D · 可观测性 API 端点

> **用途**：为运维、调试与监控提供完整的 API 接口文档。  
> **实现路径**：`plugins/life_engine/monitor/router.py`  
> **协议**：HTTP/REST + WebSocket（部分推送）

---

## D.1 HTTP API 端点

### D.1.1 系统状态快照

**端点**：`GET /message_timeline/api/snapshot`

**描述**：获取 Life Engine 的完整实时状态快照，包含事件历史、内部状态、流信息与摘要。

**请求参数**：无

**响应格式**：`application/json`

**响应字段**：

```json
{
  "generated_at": "ISO 8601 时间戳",
  "life": {
    "state": {
      "heartbeat_count": "心跳计数",
      "event_sequence": "事件序列号",
      "last_model_reply_at": "最后模型回复时间",
      "last_model_reply": "最后模型回复内容",
      "last_model_error": "最后错误信息（null 表示无错误）",
      "last_wake_context_at": "最后唤醒上下文时间",
      "last_wake_context_size": "唤醒上下文大小",
      "last_external_message_at": "最后外部消息时间",
      "last_tell_dfc_at": "最后 tell_dfc 时间",
      "tell_dfc_count": "tell_dfc 累计次数",
      "chatter_context_cursors": {
        "stream_id_1": "游标序列号",
        "stream_id_2": "游标序列号"
      }
    },
    "inner_state": {
      "snn_health": {
        "tick_count": "SNN tick 计数",
        "drives": {
          "arousal": "唤醒度 [0~1]",
          "valence": "情绪效价 [-1~1]",
          "social": "社交驱动 [0~1]",
          "task": "任务驱动 [0~1]",
          "exploration": "探索驱动 [0~1]",
          "rest": "休息驱动 [0~1]"
        },
        "hidden_v_mean": "隐藏层膜电位均值",
        "hidden_v_std": "隐藏层膜电位标准差",
        "output_v_mean": "输出层膜电位均值",
        "syn_in_hid_mean": "输入→隐藏突触均值",
        "syn_hid_out_mean": "隐藏→输出突触均值"
      },
      "neuromod_state": {
        "curiosity": {"value": 0.62, "baseline": 0.55},
        "sociability": {"value": 0.48, "baseline": 0.50},
        "focus": {"value": 0.71, "baseline": 0.60},
        "contentment": {"value": 0.65, "baseline": 0.60},
        "energy": {"value": 0.82, "baseline": 0.75}
      },
      "dream_state": {
        "last_dream_at": "最后做梦时间",
        "dream_count": "累计做梦次数",
        "last_dream_type": "nrem/rem/nap"
      }
    },
    "pending_events": [
      /* LifeEngineEvent 数组（待处理事件） */
    ],
    "recent_events": [
      /* 最近 N 条事件历史 */
    ],
    "latest_event": {
      /* 最新一条事件 */
    }
  },
  "streams": [
    {
      "stream_id": "唯一标识符",
      "stream_name": "流名称（如群名）",
      "platform": "平台（qq/telegram/discord）",
      "chat_type": "聊天类型（group/private/channel）",
      "is_active": "是否活跃（最近 5 分钟有消息）",
      "unread_count": "未读消息数",
      "history_count": "历史消息总数",
      "latest_message": {
        /* 最新一条消息 */
      },
      "recent_messages": [
        /* 最近 N 条消息 */
      ]
    }
  ],
  "summary": {
    "active_stream_count": "活跃流数量",
    "pending_life_events": "待处理事件数",
    "recent_life_events": "最近事件数",
    "heartbeat_count": "心跳计数"
  }
}
```

**使用示例**：

```bash
# 获取完整快照
curl http://localhost:8080/message_timeline/api/snapshot

# 提取调质状态
curl -s http://localhost:8080/message_timeline/api/snapshot | \
  jq '.life.inner_state.neuromod_state'

# 监控心跳计数
watch -n 30 'curl -s http://localhost:8080/message_timeline/api/snapshot | \
  jq .life.state.heartbeat_count'
```

---

### D.1.2 历史检索

**端点**：`GET /message_timeline/api/history_search`

**描述**：透传给 `LifeEngineFetchChatHistoryTool`，执行语义搜索或时序检索。

**请求参数**：

| 参数 | 类型 | 必需 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | 否 | `""` | 语义搜索查询（留空则按时序） |
| `stream_id` | string | 否 | `null` | 限定流 ID（留空则搜索所有流） |
| `cross_stream` | bool | 否 | `false` | 是否跨流检索 |
| `limit` | int | 否 | `20` | 返回条数上限 |
| `source_mode` | string | 否 | `auto` | `auto`/`local_db`/`napcat`，数据源选择 |
| `include_tool_calls` | bool | 否 | `false` | 是否包含工具调用事件 |

**响应格式**：`application/json`

**响应字段**：

```json
{
  "results": [
    {
      "event_id": "事件ID",
      "timestamp": "ISO 8601 时间戳",
      "sender": "发送者",
      "content": "消息内容",
      "stream_id": "流ID",
      "platform": "平台",
      "score": "相似度分数（语义搜索时有效）"
    }
  ],
  "total_count": "结果总数",
  "query_time_ms": "查询耗时（毫秒）"
}
```

**使用示例**：

```bash
# 语义搜索"天气"相关消息
curl -G http://localhost:8080/message_timeline/api/history_search \
  --data-urlencode "query=天气" \
  --data-urlencode "limit=10"

# 获取特定流的最近 50 条消息
curl -G http://localhost:8080/message_timeline/api/history_search \
  --data-urlencode "stream_id=group_12345" \
  --data-urlencode "limit=50"

# 跨流检索
curl -G http://localhost:8080/message_timeline/api/history_search \
  --data-urlencode "query=项目进度" \
  --data-urlencode "cross_stream=true"
```

---

## D.2 WebSocket 端点

### D.2.1 记忆系统实时推送

**端点**：`WS /memory/ws`

**描述**：实时推送记忆图谱变化事件（节点激活、边强化、新边创建等）。

**实现路径**：`plugins/life_engine/memory/router.py`

**消息格式**：

```json
{
  "event_type": "node_activated | edge_strengthened | edge_created | node_created",
  "timestamp": "ISO 8601 时间戳",
  "payload": {
    /* 根据 event_type 变化 */
  }
}
```

**事件类型说明**：

| 事件类型 | payload 字段 | 说明 |
|---------|-------------|------|
| `node_activated` | `{"node_id": "...", "activation": 0.85}` | 节点被检索/激活 |
| `edge_strengthened` | `{"from": "node_a", "to": "node_b", "old_strength": 0.5, "new_strength": 0.65}` | 边权重增强 |
| `edge_created` | `{"from": "node_a", "to": "node_b", "edge_type": "RELATES_TO", "strength": 0.3}` | 新边创建 |
| `node_created` | `{"node_id": "...", "node_type": "CONCEPT", "content": "..."}` | 新节点创建 |

**使用示例**（Python）：

```python
import asyncio
import websockets
import json

async def monitor_memory():
    uri = "ws://localhost:8080/memory/ws"
    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            event = json.loads(message)
            print(f"[{event['event_type']}] {event['payload']}")

asyncio.run(monitor_memory())
```

---

## D.3 CLI 工具

### D.3.1 快照查看工具

**命令**：`python -m plugins.life_engine.tools.cli snapshot`

**功能**：在终端中格式化显示系统快照。

**输出示例**：

```
=== Life Engine 快照 ===
生成时间: 2025-01-15 12:00:00

[核心状态]
- 心跳计数: 42
- 事件序列号: 1337
- 最后模型回复: "此刻很安静..."
- 最后外部消息: 30 分钟前

[调质状态]
- 好奇心: 0.62 (基线: 0.55) ↑
- 社交欲: 0.48 (基线: 0.50) ↓
- 专注度: 0.71 (基线: 0.60) ↑
- 满足感: 0.65 (基线: 0.60) ↑
- 能量: 0.82 (基线: 0.75) ↑

[驱动信号]
- 唤醒度: 0.45
- 情绪效价: 0.32
- 社交: 0.28
- 任务: 0.51
- 探索: 0.38
- 休息: 0.19

[活跃流]
- group_12345 (QQ 群 - 技术讨论组): 3 条未读
- private_67890 (QQ 私聊 - 用户A): 0 条未读
```

---

### D.3.2 事件流查看工具

**命令**：`python -m plugins.life_engine.tools.cli events [--limit N] [--type TYPE]`

**功能**：查看事件历史。

**选项**：

- `--limit N`：限制显示条数（默认 20）
- `--type TYPE`：过滤事件类型（`message`/`heartbeat`/`tool_call`/`dream`）

**输出示例**：

```
=== 事件历史（最近 10 条）===

[1337] 2025-01-15 12:00:00 | heartbeat | Life Engine 心跳
[1336] 2025-01-15 11:59:58 | tool_result | search_memory 成功
[1335] 2025-01-15 11:59:57 | tool_call | search_memory(query="最近有哪些...")
[1320] 2025-01-15 11:30:00 | message | [group_12345] 用户A: 今天天气真好呀
...
```

---

## D.4 健康检查端点

### D.4.1 服务健康检查

**端点**：`GET /health`

**描述**：检查 Life Engine 服务是否正常运行。

**响应格式**：`application/json`

**响应字段**：

```json
{
  "status": "healthy | degraded | unhealthy",
  "checks": {
    "life_engine": "ok | error",
    "snn": "ok | disabled | error",
    "neuromod": "ok | disabled | error",
    "dream": "ok | disabled | error",
    "memory": "ok | error"
  },
  "uptime_seconds": "运行时长（秒）",
  "last_heartbeat_at": "最后心跳时间"
}
```

**状态判定规则**：

- `healthy`：所有启用的子系统正常
- `degraded`：部分非核心子系统异常（如 SNN 禁用）
- `unhealthy`：核心子系统异常（如心跳停止超过 2 分钟）

**使用示例**：

```bash
# 监控服务健康
curl http://localhost:8080/health

# Prometheus 集成
curl http://localhost:8080/health | jq -r '.status' | \
  awk '{if ($1=="healthy") exit 0; else exit 1}'
```

---

## D.5 日志接口

### D.5.1 日志文件路径

| 日志类型 | 路径 | 说明 |
|---------|------|------|
| 主日志 | `logs/life_engine.log` | Life Engine 完整日志 |
| 心跳日志 | `logs/heartbeat.log` | 心跳专用日志（可配置关闭） |
| SNN 日志 | `logs/snn.log` | SNN 运行日志（仅启用时有效） |
| 做梦日志 | `data/life_engine_workspace/dream_log.json` | 做梦场景记录（JSON 格式） |

### D.5.2 日志级别

通过环境变量 `LOG_LEVEL` 配置：

```bash
# 调试模式（显示所有日志）
LOG_LEVEL=DEBUG python main.py

# 生产模式（仅显示 INFO 及以上）
LOG_LEVEL=INFO python main.py
```

---

## D.6 Prometheus 指标（规划中）

当前版本**未实现** Prometheus 指标导出，计划在未来版本中提供以下指标：

| 指标名 | 类型 | 说明 |
|--------|------|------|
| `life_engine_heartbeat_count` | Counter | 累计心跳次数 |
| `life_engine_event_sequence` | Gauge | 当前事件序列号 |
| `life_engine_pending_events` | Gauge | 待处理事件数 |
| `life_engine_active_streams` | Gauge | 活跃流数量 |
| `life_engine_model_call_duration_seconds` | Histogram | 模型调用耗时 |
| `life_engine_snn_tick_count` | Counter | SNN tick 次数 |
| `life_engine_dream_count` | Counter | 累计做梦次数 |

**端点**：`GET /metrics`（规划中）

---

## 使用建议

### D.6.1 监控策略

**基础监控**（必需）：

1. **健康检查**：每 30 秒调用 `/health`，检查 `status` 字段
2. **心跳监控**：每 5 分钟调用 `/api/snapshot`，确认 `heartbeat_count` 递增
3. **错误监控**：监控 `last_model_error` 字段，非 null 时告警

**进阶监控**（可选）：

1. **调质监控**：跟踪 `neuromod_state` 的 5 个因子，观察异常波动
2. **驱动监控**：跟踪 `snn_health.drives`，观察系统倾向变化
3. **流活跃度**：跟踪 `streams[].is_active`，发现静默流

### D.6.2 调试技巧

**快速定位最后一次错误**：

```bash
curl -s http://localhost:8080/message_timeline/api/snapshot | \
  jq -r '.life.state.last_model_error'
```

**查看最近 5 次心跳的工具调用**：

```bash
curl -s http://localhost:8080/message_timeline/api/snapshot | \
  jq '[.life.recent_events[] | select(.event_type=="tool_call")] | .[-5:]'
```

**监控调质因子变化趋势**（需结合脚本）：

```bash
# 每 30 秒记录一次
while true; do
  curl -s http://localhost:8080/message_timeline/api/snapshot | \
    jq -r '.life.inner_state.neuromod_state | to_entries | .[] | "\(.key): \(.value.value)"' | \
    ts '%Y-%m-%d %H:%M:%S' >> neuromod_trend.log
  sleep 30
done
```

### D.6.3 性能优化

**减少快照调用频率**：

- `/api/snapshot` 返回完整状态（可能数百 KB），避免高频轮询
- 建议间隔 ≥ 30 秒，或通过 WebSocket 订阅实时事件

**跨流检索优化**：

- `cross_stream=true` 会扫描多个流（耗时），仅在必要时使用
- 优先使用 `stream_id` 限定单流检索

---

**版本信息**  
- API 版本：v1.0  
- 最后更新：2025-01-15  
- 文档维护：Neo-MoFox 报告撰写组
