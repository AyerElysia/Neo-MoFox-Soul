# 附录 C · 状态持久化 JSON Schema

> **用途**：为 `life_engine_context.json` 提供完整的 JSON Schema 定义，确保持久化数据的类型安全与一致性。  
> **文件路径**：`{workspace_path}/life_engine_context.json`  
> **Schema 版本**：draft-2020-12

---

## C.1 完整 JSON Schema

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://neo-mofox.org/schemas/life_engine_context.json",
  "title": "Life Engine Context",
  "description": "Life Engine 的完整持久化状态，包含事件历史、子系统状态与元数据",
  "type": "object",
  "required": ["version", "state", "pending_events", "event_history"],
  "properties": {
    "version": {
      "type": "integer",
      "description": "Schema 版本号，当前为 1",
      "const": 1
    },
    "state": {
      "$ref": "#/$defs/LifeEngineState"
    },
    "pending_events": {
      "type": "array",
      "description": "崩溃前未被心跳处理的事件，恢复后会重新注入",
      "items": {
        "$ref": "#/$defs/LifeEngineEvent"
      }
    },
    "event_history": {
      "type": "array",
      "description": "已处理的事件历史（最多保留 context_history_max_events 条）",
      "items": {
        "$ref": "#/$defs/LifeEngineEvent"
      }
    },
    "snn_state": {
      "$ref": "#/$defs/SNNState"
    },
    "neuromod_state": {
      "$ref": "#/$defs/NeuromodState"
    },
    "dream_state": {
      "$ref": "#/$defs/DreamState"
    }
  },

  "$defs": {
    "LifeEngineState": {
      "type": "object",
      "description": "Life Engine 的核心运行态字段",
      "required": [
        "heartbeat_count",
        "event_sequence",
        "last_model_reply_at",
        "last_wake_context_at"
      ],
      "properties": {
        "heartbeat_count": {
          "type": "integer",
          "description": "累计心跳次数（每次心跳 +1）"
        },
        "event_sequence": {
          "type": "integer",
          "description": "事件序列号（全局单调递增）"
        },
        "last_model_reply_at": {
          "type": "string",
          "format": "date-time",
          "description": "最后一次模型回复的时间戳（ISO 8601 格式）"
        },
        "last_model_reply": {
          "type": ["string", "null"],
          "description": "最后一次模型回复的文本内容"
        },
        "last_model_error": {
          "type": ["string", "null"],
          "description": "最后一次模型调用的错误信息（无错误则为 null）"
        },
        "last_wake_context_at": {
          "type": "string",
          "format": "date-time",
          "description": "最后一次构建唤醒上下文的时间"
        },
        "last_wake_context_size": {
          "type": "integer",
          "description": "最后一次唤醒上下文包含的事件数量"
        },
        "last_external_message_at": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "最后一次收到外部消息的时间（用于判定活跃度）"
        },
        "last_tell_dfc_at": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "最后一次向 DFC 注入信息的时间"
        },
        "tell_dfc_count": {
          "type": "integer",
          "description": "累计 tell_dfc 调用次数"
        },
        "chatter_context_cursors": {
          "type": "object",
          "description": "各聊天流的上下文游标（stream_id → 最新处理的事件序列号）",
          "additionalProperties": {
            "type": "integer"
          }
        }
      }
    },

    "LifeEngineEvent": {
      "type": "object",
      "description": "Life Engine 事件的完整结构",
      "required": [
        "event_id",
        "event_type",
        "timestamp",
        "sequence",
        "source"
      ],
      "properties": {
        "event_id": {
          "type": "string",
          "description": "事件唯一标识符"
        },
        "event_type": {
          "type": "string",
          "enum": ["message", "heartbeat", "tool_call", "tool_result", "dream", "system"],
          "description": "事件类型"
        },
        "timestamp": {
          "type": "string",
          "format": "date-time",
          "description": "事件发生时间（ISO 8601）"
        },
        "sequence": {
          "type": "integer",
          "description": "事件全局序列号"
        },
        "source": {
          "type": "string",
          "description": "事件来源（如 qq、telegram、internal）"
        },
        "source_detail": {
          "type": "string",
          "description": "来源详细信息（如 qq | 入站 | 群聊 | 群号）"
        },
        "content": {
          "type": ["string", "null"],
          "description": "事件内容（消息文本、工具调用结果等）"
        },
        "content_type": {
          "type": "string",
          "enum": ["text", "image", "audio", "video", "file", "system"],
          "description": "内容类型"
        },
        "sender": {
          "type": ["string", "null"],
          "description": "发送者标识（用户名/ID）"
        },
        "chat_type": {
          "type": ["string", "null"],
          "enum": ["private", "group", "channel", null],
          "description": "聊天类型"
        },
        "stream_id": {
          "type": ["string", "null"],
          "description": "所属聊天流 ID"
        },
        "heartbeat_index": {
          "type": ["integer", "null"],
          "description": "所属心跳索引（仅 heartbeat/tool_call/tool_result 类型有效）"
        },
        "tool_name": {
          "type": ["string", "null"],
          "description": "工具名称（仅 tool_call/tool_result 类型）"
        },
        "tool_args": {
          "type": ["object", "null"],
          "description": "工具调用参数（JSON 对象）"
        },
        "tool_success": {
          "type": ["boolean", "null"],
          "description": "工具调用是否成功（仅 tool_result 类型）"
        }
      }
    },

    "SNNState": {
      "type": "object",
      "description": "SNN 的完整神经元与突触状态",
      "required": ["version"],
      "properties": {
        "version": {
          "type": "integer",
          "description": "SNN 状态版本号（当前为 2）",
          "const": 2
        },
        "hidden_v": {
          "type": "array",
          "items": {"type": "number"},
          "description": "隐藏层神经元膜电位（长度 = hidden_size）"
        },
        "output_v": {
          "type": "array",
          "items": {"type": "number"},
          "description": "输出层神经元膜电位（长度 = 6，对应 6 种驱动）"
        },
        "output_ema": {
          "type": "array",
          "items": {"type": "number"},
          "description": "输出层 EMA 平滑值（长度 = 6）"
        },
        "syn_in_hid_W": {
          "type": "array",
          "items": {
            "type": "array",
            "items": {"type": "number"}
          },
          "description": "输入→隐藏层突触权重矩阵（input_size × hidden_size）"
        },
        "syn_hid_out_W": {
          "type": "array",
          "items": {
            "type": "array",
            "items": {"type": "number"}
          },
          "description": "隐藏→输出层突触权重矩阵（hidden_size × 6）"
        },
        "hidden_threshold": {
          "type": "array",
          "items": {"type": "number"},
          "description": "隐藏层神经元的动态阈值（自稳态机制）"
        },
        "tick_count": {
          "type": "integer",
          "description": "SNN 累计 tick 次数"
        },
        "last_tick_at": {
          "type": "number",
          "description": "最后一次 tick 的 Unix 时间戳（浮点数）"
        }
      }
    },

    "NeuromodState": {
      "type": "object",
      "description": "神经调质层的状态",
      "required": ["modulators", "last_update_time"],
      "properties": {
        "modulators": {
          "type": "object",
          "description": "五个调质因子的状态",
          "required": ["curiosity", "sociability", "focus", "contentment", "energy"],
          "properties": {
            "curiosity": {"$ref": "#/$defs/ModulatorValue"},
            "sociability": {"$ref": "#/$defs/ModulatorValue"},
            "focus": {"$ref": "#/$defs/ModulatorValue"},
            "contentment": {"$ref": "#/$defs/ModulatorValue"},
            "energy": {"$ref": "#/$defs/ModulatorValue"}
          }
        },
        "last_update_time": {
          "type": "number",
          "description": "最后一次调质更新的 Unix 时间戳"
        },
        "habits": {
          "type": "object",
          "description": "习惯追踪状态（habit_name → {streak, strength, last_trigger}）",
          "additionalProperties": {
            "type": "object",
            "properties": {
              "streak": {"type": "integer", "description": "连胜天数"},
              "strength": {"type": "number", "description": "习惯强度 [0~1]"},
              "last_trigger": {"type": "string", "format": "date", "description": "最后触发日期"}
            }
          }
        }
      }
    },

    "ModulatorValue": {
      "type": "object",
      "description": "单个调质因子的状态",
      "required": ["value", "baseline"],
      "properties": {
        "value": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "当前浓度值 [0~1]"
        },
        "baseline": {
          "type": "number",
          "minimum": 0,
          "maximum": 1,
          "description": "基线值（回归目标）"
        }
      }
    },

    "DreamState": {
      "type": "object",
      "description": "做梦调度器的状态（具体字段由 DreamScheduler.serialize() 定义）",
      "properties": {
        "last_dream_at": {
          "type": ["string", "null"],
          "format": "date-time",
          "description": "最后一次做梦的时间"
        },
        "dream_count": {
          "type": "integer",
          "description": "累计做梦次数"
        },
        "last_dream_type": {
          "type": ["string", "null"],
          "enum": ["nrem", "rem", "nap", null],
          "description": "最后一次做梦的类型"
        }
      }
    }
  }
}
```

---

## C.2 字段更新频率

### C.2.1 每次心跳更新

以下字段在**每次心跳**（约 30 秒）都会更新：

- `state.heartbeat_count` — 心跳计数器 +1
- `state.event_sequence` — 每个新事件递增
- `state.last_model_reply_at` — 模型回复时更新
- `state.last_model_reply` — 模型回复内容
- `state.last_wake_context_at` — 构建唤醒上下文时更新
- `state.last_wake_context_size` — 唤醒上下文大小
- `event_history` — 追加新事件（最多保留 100 条）
- `pending_events` — 处理后清空
- `neuromod_state.modulators.*` — 调质因子浓度值

### C.2.2 按需更新

以下字段仅在特定事件发生时更新：

- `state.last_external_message_at` — 收到外部消息时
- `state.last_tell_dfc_at` — 调用 `nucleus_tell_dfc` 时
- `state.chatter_context_cursors` — DFC 消费事件时
- `snn_state.*` — SNN tick 时（默认每 10 秒）
- `dream_state.*` — 做梦时（默认每 90 分钟）

### C.2.3 只在重启时写入

以下字段在**重启时加载**，运行时不频繁更新：

- `version` — Schema 版本号（固定为 1）
- `snn_state.version` — SNN 状态版本（固定为 2）

---

## C.3 示例实例（脱敏后）

```json
{
  "version": 1,
  "state": {
    "heartbeat_count": 42,
    "event_sequence": 1337,
    "last_model_reply_at": "2025-01-15T12:00:00+08:00",
    "last_model_reply": "此刻很安静，但我仍在持续感受世界的律动...",
    "last_model_error": null,
    "last_wake_context_at": "2025-01-15T11:59:30+08:00",
    "last_wake_context_size": 12,
    "last_external_message_at": "2025-01-15T11:30:00+08:00",
    "last_tell_dfc_at": "2025-01-15T11:55:00+08:00",
    "tell_dfc_count": 8,
    "chatter_context_cursors": {
      "group_12345": 1200,
      "private_67890": 1190
    }
  },
  "pending_events": [],
  "event_history": [
    {
      "event_id": "msg_98765",
      "event_type": "message",
      "timestamp": "2025-01-15T11:30:00+08:00",
      "sequence": 1320,
      "source": "qq",
      "source_detail": "qq | 入站 | 群聊 | 群号: 12345",
      "content": "今天天气真好呀",
      "content_type": "text",
      "sender": "用户A",
      "chat_type": "group",
      "stream_id": "group_12345",
      "heartbeat_index": null,
      "tool_name": null,
      "tool_args": null,
      "tool_success": null
    },
    {
      "event_id": "hb_42",
      "event_type": "heartbeat",
      "timestamp": "2025-01-15T12:00:00+08:00",
      "sequence": 1337,
      "source": "internal",
      "source_detail": "Life Engine 心跳",
      "content": null,
      "content_type": "system",
      "sender": null,
      "chat_type": null,
      "stream_id": null,
      "heartbeat_index": 42,
      "tool_name": null,
      "tool_args": null,
      "tool_success": null
    }
  ],
  "snn_state": {
    "version": 2,
    "hidden_v": [0.12, -0.05, 0.31, ...],
    "output_v": [0.08, 0.15, 0.22, 0.03, 0.19, 0.11],
    "output_ema": [0.10, 0.13, 0.20, 0.05, 0.18, 0.09],
    "syn_in_hid_W": [[0.02, 0.15, ...], ...],
    "syn_hid_out_W": [[0.08, 0.12, ...], ...],
    "hidden_threshold": [1.02, 0.98, 1.05, ...],
    "tick_count": 4200,
    "last_tick_at": 1705292400.0
  },
  "neuromod_state": {
    "modulators": {
      "curiosity": {"value": 0.62, "baseline": 0.55},
      "sociability": {"value": 0.48, "baseline": 0.50},
      "focus": {"value": 0.71, "baseline": 0.60},
      "contentment": {"value": 0.65, "baseline": 0.60},
      "energy": {"value": 0.82, "baseline": 0.75}
    },
    "last_update_time": 1705292400.0,
    "habits": {
      "morning_greeting": {
        "streak": 7,
        "strength": 0.85,
        "last_trigger": "2025-01-15"
      },
      "daily_summary": {
        "streak": 3,
        "strength": 0.62,
        "last_trigger": "2025-01-15"
      }
    }
  },
  "dream_state": {
    "last_dream_at": "2025-01-15T10:30:00+08:00",
    "dream_count": 18,
    "last_dream_type": "nrem"
  }
}
```

---

## C.4 Schema 验证工具

### C.4.1 Python 验证

使用 `jsonschema` 库验证持久化文件：

```python
import json
from jsonschema import validate, ValidationError

# 读取 schema 与实例
with open("life_engine_schema.json") as f:
    schema = json.load(f)
with open("life_engine_context.json") as f:
    instance = json.load(f)

# 验证
try:
    validate(instance=instance, schema=schema)
    print("✓ 验证通过")
except ValidationError as e:
    print(f"✗ 验证失败: {e.message}")
```

### C.4.2 在线验证

推荐工具：[jsonschemavalidator.net](https://www.jsonschemavalidator.net)

---

## C.5 持久化流程

### C.5.1 保存流程（原子性保证）

1. 获取线程锁（防止并发写）
2. 构建完整 payload 字典
3. 释放锁
4. 写入临时文件 `life_engine_context.json.tmp`（`ensure_ascii=False, indent=2`）
5. 原子重命名 `.tmp → life_engine_context.json`（覆盖旧文件）

**代码路径**：`service/state_manager.py:263`

### C.5.2 恢复流程

1. 检查文件存在性（不存在返回空状态）
2. 读取 JSON 并解析
3. 格式校验（`pending_events` 与 `event_history` 必须是 list）
4. 反序列化事件（`event_from_dict`，恢复枚举类型）
5. 裁剪 `event_history` 到 `history_limit`
6. 获取锁，更新 `state` 字段
7. 计算 `max_sequence`（防止序列号回退）
8. 返回 `(pending, history, {snn_state, neuromod_state, dream_state})`

**代码路径**：`service/state_manager.py:331`

---

## C.6 崩溃恢复语义

### C.6.1 未完成的写入

若进程在写入 `.tmp` 时崩溃，下次启动会忽略残留的 `.tmp` 文件，降级使用上次成功保存的 `life_engine_context.json`。

### C.6.2 JSON 格式损坏

若 JSON 解析失败（如文件截断），`state_manager` 捕获异常并返回空状态 `([], [], {})`，Life Engine 以零状态干净启动。

### C.6.3 序列号连续性

恢复时计算 `max_sequence = max(state.event_sequence, max(e.sequence for e in events))`，确保新事件的序列号不回退。

### C.6.4 pending_events 重放

崩溃前已接收但未被 LLM 处理的事件会在恢复后的第一次心跳时重新注入。

---

## 使用建议

### C.6.5 备份策略

定期备份 `life_engine_context.json` 可避免数据丢失：

```bash
# 每日备份脚本
cp data/life_engine_workspace/life_engine_context.json \
   backups/life_engine_context_$(date +%Y%m%d).json
```

### C.6.6 迁移与升级

若 Schema 升级（如 `version: 2`），需编写迁移脚本：

```python
def migrate_v1_to_v2(old_data):
    new_data = old_data.copy()
    new_data["version"] = 2
    # 追加新字段、转换旧格式等
    return new_data
```

### C.6.7 调试建议

- **查看最近心跳**：`jq '.event_history[-5:]' life_engine_context.json`
- **检查调质状态**：`jq '.neuromod_state.modulators' life_engine_context.json`
- **统计事件类型**：`jq '[.event_history[].event_type] | group_by(.) | map({type: .[0], count: length})' life_engine_context.json`

---

**版本信息**  
- Schema 版本：draft-2020-12  
- Life Engine Context 版本：v1  
- 最后更新：2025-01-15  
- 文档维护：Neo-MoFox 报告撰写组
