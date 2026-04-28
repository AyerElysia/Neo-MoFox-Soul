# Neo-MoFox 架构深度调研报告

> **报告版本**：B_architecture v1.0  
> **调研范围**：`src/kernel/`、`src/core/`、`src/app/`、`plugins/default_chatter/`、`plugins/diary_plugin/`、`plugins/proactive_message_plugin/`、`plugins/thinking_plugin/`、`plugins/booku_memory/`  
> **核心哲学**：连续性、自下而上学习、系统涌现智能

---

## 1. 三层架构全貌

### 1.1 层次划分与职责

Neo-MoFox 采用严格的三层架构，从底向上依次为：

```
┌─────────────────────────────────────────────────────┐
│              app 层（src/app/）                      │
│  runtime/bot.py · plugin_system/api · built-in 插件  │
├─────────────────────────────────────────────────────┤
│              core 层（src/core/）                    │
│  components · managers · models · prompt · transport │
├─────────────────────────────────────────────────────┤
│              kernel 层（src/kernel/）                │
│  llm · event · scheduler · config · db              │
│  vector_db · storage · concurrency · logger         │
└─────────────────────────────────────────────────────┘
```

| 层级   | 职责                                     | 不变式                                           |
|--------|------------------------------------------|--------------------------------------------------|
| kernel | 纯基础设施：不感知"对话"、"插件"等业务概念 | 不导入 core/app 任何模块                         |
| core   | 框架骨架：组件类型系统、消息管线、提示管理  | 不执行具体业务逻辑；不直接驱动 LLM 完成对话      |
| app    | 运行时 + Plugin API 门面：启动、发现、暴露  | 不直接操作底层 kernel 原语，通过 plugin_system/api 中转 |

### 1.2 依赖方向验证

**标准方向**：app → core → kernel

实际代码核查：
- `src/kernel/event/core.py:23` → 只导入 `src.kernel.concurrency` 和 `src.kernel.logger`，未见 core/app 导入 ✅
- `src/core/managers/event_manager.py:20` → `from src.kernel.event import get_event_bus`，正向依赖 ✅
- `src/app/runtime/bot.py:18` → `from src.core.config import CORE_VERSION`，正向依赖 ✅

**存在的架构越界（"未解之谜"候选）**：
- `plugins/life_engine/service/integrations.py:266` 中直接 `from default_chatter import plugin as default_chatter_plugin_module`，这是两个外置插件之间的直接裸模块引用，绕过了 ServiceManager/EventManager 的解耦机制。这属于 plugin→plugin 的平层耦合，而非分层违反，但打破了"插件不直接引用其他插件模块"的软规范。

---

## 2. Kernel 层——基础设施解剖

### 2.1 LLM 抽象（`src/kernel/llm/`）

#### 数据模型

**`LLMPayload`**（`payload/payload.py:24`）：

```python
@dataclass(slots=True)
class LLMPayload:
    role: ROLE
    content: list[Content | LLMUsable]
```

`ROLE` 枚举包含 `SYSTEM`, `USER`, `ASSISTANT`, `TOOL`, `TOOL_RESULT`。`content` 允许多态列表——纯文本 `Text`、图片 `Image`、工具调用结果 `ToolResult`，以及实现 `LLMUsable` 协议的工具类。

**`LLMRequest`**（`request.py:79`）：

```python
@dataclass(slots=True)
class LLMRequest:
    model_set: ModelSet          # 模型集合（含负载均衡策略）
    request_name: str = ""
    payloads: list[LLMPayload]
    policy: Policy | None        # 重试与轮询策略
    clients: ModelClientRegistry | None
    context_manager: LLMContextManager | None
    enable_metrics: bool = True
    request_type: RequestType
```

#### 链式 API

```python
request = LLMRequest(model_set, "chat_turn")
request.add_payload(LLMPayload(ROLE.SYSTEM, Text(system_prompt)))   # 支持链式调用
       .add_payload(LLMPayload(ROLE.USER, Text(user_text)))
response = await request.send(stream=True)  # 统一接口
```

`add_payload()` 返回 `Self`（`request.py:102`），实现流畅 Builder 模式。同一角色的相邻 payload 会自动合并（`request.py:126`）。

#### 流式与非流式统一

`send()` 方法（`request.py:216`）的签名：

```python
async def send(self, auto_append_response: bool = True, *, stream: bool = True) -> LLMResponse
```

`stream=True` 是默认值。底层 `ChatModelClient.create()` 返回五元组：

```python
(message, tool_calls, stream_iter, reasoning_content, request_record_id)
```

- **流式**：`message=None`，`stream_iter` 为 `AsyncIterator[StreamEvent]`
- **非流式**：`stream_iter=None`，`message` 为完整文本

两路最终都由 `LLMResponse` 包装，调用方代码无需感知差异（`model_client/base.py:20-39`）。

模型可通过 `force_stream_mode: bool` 覆盖请求者设置（`request.py:274`）。

#### 多厂商适配

`ChatModelClient` 是 `typing.Protocol`（`model_client/base.py:20`），当前只有 `openai_client.py` 一个实现，覆盖所有兼容 OpenAI API 格式的提供商（OpenAI、Moonshot、DeepSeek 等）。`ModelClientRegistry` 根据 `model_set` 配置选取客户端实例（`request.py:265`）。

上下文裁剪由 `LLMContextManager` + `count_payload_tokens()` 协同完成，支持 token 预算（`request.py:131-213`）。

---

### 2.2 事件总线（`src/kernel/event/core.py`）

**类型**：**纯 in-process pub/sub，无持久化**。

核心数据结构：

```python
_subscribers: dict[str, dict[EventHandlerCallable, _Subscriber]]
_handler_subscriptions: dict[EventHandlerCallable, set[str]]
```

双向索引：事件名→处理器 + 处理器→已订阅事件集，O(1) 订阅/取消。

**执行协议**（`event/core.py:8-11`）：
- 处理器签名：`handler(event_name, params) → (EventDecision, next_params)`
- `params` 是 `dict[str, Any]`，key 集合在整条链路中必须保持不变
- `EventDecision.SUCCESS`：更新 params 继续；`STOP`：终止链；`PASS`：不更新 params 继续

**发布方式**：
- `await bus.publish(event_name, params)` — 异步等待所有处理器完成
- `bus.publish_sync(event_name, params)` — 即发即弃，返回 `asyncio.Task`

**优先级**：订阅时传入 `priority: int`，`publish()` 时按 `(-priority, order)` 稳定排序（`event/core.py:232`）。

---

### 2.3 调度器（`src/kernel/scheduler/core.py`）

#### 触发器类型（`scheduler/types.py:13`）

```python
class TriggerType(Enum):
    TIME   = "time"    # 时间触发：延迟、周期、指定时刻
    EVENT  = "event"   # 事件触发（预留，未来集成 event 模块）
    CUSTOM = "custom"  # 自定义条件触发
```

**时间精度**：主循环每秒检查一次（`SchedulerConfig.check_interval = 1.0`），适合秒级调度；不适合毫秒级精度需求。

#### 关键 API

```python
scheduler = UnifiedScheduler(config)
await scheduler.start()
schedule_id = scheduler.add_task(
    task_name="heartbeat",
    callback=my_coroutine,
    trigger_type=TriggerType.TIME,
    trigger_config={"interval": 300},   # 每 5 分钟
    is_recurring=True,
    timeout=60.0,
)
await scheduler.cancel_task(schedule_id)
```

任务内置重试（最多 3 次，间隔 5 秒）、超时保护（默认 300 秒）、任务信号量限流（最大并发 100）。

---

### 2.4 配置系统（`src/kernel/config/core.py`）

**技术栈**：`tomllib`（只读 TOML 解析）+ `pydantic.BaseModel`（类型验证）。

框架提供增强的 `Field()` 函数（`config/core.py:33`），在 Pydantic 原生验证参数基础上追加 WebUI 属性：

```python
Field(
    default="claude-3-5-sonnet",
    tag="ai",              # 映射到 WebUI 图标
    label="主力模型",
    input_type="select",
    choices=["gpt-4o", "claude-3-5-sonnet", "deepseek-v3"],
    description="用于主对话的 LLM 模型",
    order=1,
)
```

`SectionBase`（`config/core.py`）继承 `pydantic.BaseModel`，用于嵌套配置节。当前**未发现热重载实现**——配置在 `bot.py:269` 的 `init_core_config()` 调用时一次性加载，运行时不动态重读。

---

### 2.5 数据库（`src/kernel/db/`）

**引擎**：SQLAlchemy async (`sqlalchemy.ext.asyncio`)，支持 SQLite 和 PostgreSQL（`bot.py:318-345`）。

**核心 API（`db/api/crud.py`）**：

```python
# 异步会话上下文
async with _get_session_ctx(session_factory) as session:
    ...

# 通用 CRUD（泛型 T）
await create(model_class, data_dict, session_factory)
await get_by_id(model_class, id_value, session_factory)
await get_list(model_class, filters, limit, offset, session_factory)
await update_by_id(model_class, id_value, update_dict, session_factory)
await delete_by_id(model_class, id_value, session_factory)
```

使用 `@lru_cache(maxsize=256)` 缓存模型列名（`crud.py:57`），减少重复反射开销。

QueryBuilder（`db/api/query.py`）提供链式查询构建。

数据库结构在启动时通过 `enforce_database_schema_consistency()` 做列级自动对齐（`bot.py:336`）——可以无停机添加/删除/修改列类型，无需迁移文件。

---

### 2.6 向量数据库（`src/kernel/vector_db/`）

抽象基类 `VectorDBBase`（`vector_db/base.py:11`）定义标准接口：

```python
async def initialize(path, **kwargs)
async def get_or_create_collection(name, **kwargs)
async def add(collection_name, embeddings, documents, metadatas, ids)
async def query(collection_name, query_embeddings, n_results, where)
async def delete(collection_name, ids, where)
async def get(collection_name, ids, where, limit, offset, include)
async def count(collection_name) -> int
async def delete_collection(name)
async def close()
```

当前唯一实现：`chromadb_impl.py`（ChromaDB 持久化存储，路径 `data/chroma_db`）。

---

### 2.7 存储（`src/kernel/storage/`）

`JSONStore`：面向 key-value 的 JSON 文件存储，路径 `data/json_storage`，适合简单持久化键值（如插件状态、计数器）。

---

### 2.8 并发（`src/kernel/concurrency/`）

- `TaskManager`：封装 `asyncio.Task`，提供具名任务、守护任务（daemon=True）、任务生命周期跟踪。
- `WatchDog`：看门狗，监控主事件循环是否活跃，防止协程卡死（可通过 `config.bot.enable_watchdog` 开关）。

---

## 3. Core 层——框架骨架

### 3.1 组件类型全集（`src/core/components/types.py:23`）

`ComponentType` 枚举定义 **11 种**组件类型（注：代码中还存在 `AGENT`，实为第 12 种）：

| 类型           | 语义                                               | 基类文件               |
|----------------|----------------------------------------------------|------------------------|
| `ACTION`       | LLM Tool Call 后的"动作"，不向 LLM 返回信息        | `base/action.py`       |
| `AGENT`        | 内嵌子智能体，可多轮工具调用，向主模型返回结果     | `base/agent.py`        |
| `TOOL`         | LLM 可调用工具，向 LLM 返回结构化结果              | `base/tool.py`         |
| `ADAPTER`      | 平台适配器（如 NapCat QQ、WebSocket 等）           | `base/adapter.py`      |
| `CHATTER`      | 对话核心，定义一次"刺激-响应"循环                  | `base/chatter.py`      |
| `COMMAND`      | 命令式指令处理器，带权限系统                       | `base/command.py`      |
| `CONFIG`       | 插件配置声明，Pydantic + TOML                      | `base/config.py`       |
| `EVENT_HANDLER`| 事件总线订阅者，响应系统或自定义事件               | `base/event_handler.py`|
| `SERVICE`      | 暴露 API 供其他插件调用                            | `base/service.py`      |
| `ROUTER`       | 消息路由规则                                       | `base/router.py`       |
| `PLUGIN`       | 插件根容器，持有全部子组件                         | `base/plugin.py`       |

`BaseAction` 同时继承 `ABC` 和 `LLMUsable`（`base/action.py:23`），直接参与 LLM Tool Calling Schema 生成。

---

### 3.2 Manager 生态

| Manager            | 职责                                              | 核心 API                          |
|--------------------|---------------------------------------------------|-----------------------------------|
| `PluginManager`    | 插件导入、组件注册、生命周期钩子                   | `load_plugin_from_manifest()`     |
| `EventManager`     | EventHandler 注册到 EventBus，支持临时订阅         | `register_plugin_handlers()` `publish_event()` |
| `ServiceManager`   | Service 查询与动态实例化                           | `get_service(signature)` `call_service_async()` |
| `ChatterManager`   | Chatter 注册与过滤（按 stream_id/chat_type 等）    | `get_all_chatters()` `get_chatter()` |
| `ActionManager`    | Action 注册与过滤（按 chatter_allow 过滤）        | `get_actions_for_chatter()`       |
| `ToolManager`      | Tool 注册（含 chatter_allow 白名单）               | `get_tools_for_chatter()`         |
| `AdapterManager`   | 平台适配器注册，提供 `get_bot_info_by_platform()`  | —                                 |
| `RouterManager`    | 消息路由表管理                                     | —                                 |
| `ConfigManager`    | 插件配置 TOML 文件加载与注入                       | —                                 |

**协作流程**：`PluginLoader` 扫描目录 → 读取 `manifest.json` → 计算加载顺序 → `PluginManager` 导入模块（触发 `@register_plugin`）→ 收集 `plugin.get_components()` → 按类型注册到 `GlobalRegistry` → 各 Manager 按需查询 Registry。

---

### 3.3 Component Signature 格式与发现机制

**签名格式**（`components/types.py:208`）：

```
plugin_name:component_type:component_name
```

示例：`default_chatter:chatter:default_chatter`、`diary_plugin:service:diary_service`

解析函数 `parse_signature(signature)` 和 `build_signature(plugin_name, type, name)` 提供双向转换（`types.py:219-293`）。

**发现机制**：
1. `@register_plugin` 装饰器（`components/loader.py`）在模块导入时将插件类注册到全局字典
2. `plugin.get_components()` 返回所有子组件类（抽象方法，插件开发者实现）
3. `PluginManager` 遍历组件类列表，按 `ComponentType` 路由到相应 Manager 注册
4. 注册时自动向类注入 `_plugin_` 和 `_signature_` 类属性

---

### 3.4 Prompt 子模块（`src/core/prompt/`）

**`PromptManager`**（`prompt/manager.py:30`）：单例，持有 `dict[str, PromptTemplate]`。

**`PromptTemplate`**（`prompt/template.py`）：支持 `.set(key, value)` 链式赋值，最终 `.build()` 渲染。发布 `on_prompt_build` 事件允许插件（如 diary_plugin）在 build 时注入内容：

```python
tmpl.set("stream_id", stream_id).build()
# 内部 build() 会 publish("on_prompt_build", {name, values})
```

**`SystemReminderBucket`**（`prompt/system_reminder.py`）：有序字典式系统 reminder 注入点，支持 `actor`/`channel` 等 bucket 分组，插件可在 `on_plugin_loaded` 时写入（如 thinking_plugin 注入"思考习惯"、booku_memory 注入"长期记忆使用原则"）。

---

### 3.5 Transport 子模块（`src/core/transport/`）

**协议**：`mofox-wire`（Python 包 `mofox_wire`），`MessageEnvelope` 是平台无关的消息信封。

**接收链**：
```
外部平台 → Adapter → mofox_wire.MessageEnvelope → MessageReceiver.receive_envelope()
→ MessageConverter.convert() → Message → EventManager.publish(ON_MESSAGE_RECEIVED)
→ ChatterManager 路由 → Chatter.execute()
```

**发送链**：
```
Action.execute() → get_message_sender().send_message(message) → SinkManager
→ Adapter.send() → 外部平台
```

`MessageReceiver`（`transport/message_receive/receiver.py:41`）维护标准消息类型白名单 `_STANDARD_MESSAGE_TYPES = frozenset({"message", "group", "private"})`，非标准类型（notice、request）路由到 `_handle_other()`，发布 `ON_RECEIVED_OTHER_MESSAGE` 事件。

HTTP 服务器（`transport/router/http_server.py`）用于接收 Webhook 回调，Adapter 通过 HTTP POST 上报消息。

---

## 4. App 层——运行时与 Plugin API

### 4.1 `runtime/bot.py` 启动流程

`Bot.initialize()` 通过单一进度条贯穿 **4 个阶段**（`bot.py:111-146`）：

**Phase 1 — Kernel 初始化（9 步）**

```
Step 1: init_core_config() + init_model_config()      [TOML → Pydantic]
Step 2: initialize_logger_system()
      + _preflight_llm_providers()                    [HTTP GET /models 预检]
Step 3: get_event_bus()                               [EventBus 全局单例]
Step 4: get_task_manager() + get_watchdog()           [并发控制]
Step 5: get_unified_scheduler()                       [调度器]
Step 6: WatchDog()                                    [看门狗（第二次，bot.py:310 有重复初始化嫌疑）]
Step 7: init_database_from_config()                   [SQLAlchemy async engine]
      + enforce_database_schema_consistency()         [自动列级对齐]
Step 8: get_vector_db_service("data/chroma_db")       [ChromaDB]
Step 9: JSONStore("data/json_storage")
```

**Phase 2 — Core 组件初始化**

```
MessageReceiver + SinkManager 初始化
AdapterManager / RouterManager / EventManager / Distribution 初始化
HTTP Server 启动（如配置启用）
LLM Request Inspector 挂载（调试用）
```

**Phase 3 — 插件发现**

```
PluginLoader.plan_plugins(plugins_dir) → (load_order, manifests)
读取每个插件的 manifest.json → 版本兼容性检查 → 拓扑排序
```

**Phase 3.5 — 依赖安装**

批量安装插件声明的 Python 包（如 `numpy`, `chromadb` 等）。

**Phase 4 — 插件加载**

```
for plugin_name in load_order:
    PluginManager.load_plugin_from_manifest(path, manifest)
    → 导入模块（触发 @register_plugin）
    → 查找插件类 → 加载配置 → 实例化插件
    → 注册所有组件到 GlobalRegistry
    → plugin.on_plugin_loaded()
    → EventManager.register_plugin_handlers()
发布 ON_ALL_PLUGIN_LOADED
```

### 4.2 Plugin System API（`src/app/plugin_system/api/`）

共 20 个 API 模块，是插件访问系统能力的门面：

```
action_api.py  adapter_api.py  agent_api.py   chat_api.py    command_api.py
config_api.py  database_api.py event_api.py   llm_api.py     log_api.py
media_api.py   message_api.py  permission_api.py plugin_api.py prompt_api.py
router_api.py  send_api.py     service_api.py  storage_api.py stream_api.py
```

关键 API 示例：

```python
# llm_api.py
create_llm_request(model_set, request_name) -> LLMRequest
get_model_set_by_task("main_actor") -> ModelSet

# service_api.py
get_service("diary_plugin:service:diary_service") -> BaseService | None

# event_api.py
publish_event(EventType.ON_CHATTER_STEP, params)
```

### 4.3 内置插件与外置插件

框架本身（`src/app/`）无 `built_in/` 目录，所有插件均位于 `plugins/` 目录。`PluginLoader.plan_plugins()` 扫描 `plugins_dir`（默认 `"plugins"`），因此内置插件与外置插件没有物理区分，区别仅在于是否随仓库一同分发。

当前 `plugins/` 包含：`life_engine`（生命中枢）、`default_chatter`（DFC）、`napcat_adapter`（QQ 适配器）、`diary_plugin`、`proactive_message_plugin`、`thinking_plugin`、`booku_memory`、`command_dispatch_plugin`、`perm_plugin`、`emoji_sender`、`tts_voice_plugin`、`webui_backend` 等。

---

## 5. DFC（对话流控制器）深度解析

DFC 是 `default_chatter` 插件的核心，是 AI 生命体与外部世界交互的"主意识前端"。

### 5.1 刺激-响应核心链路

```
消息接收 → ON_MESSAGE_RECEIVED 事件 → ChatterManager 路由 → DefaultChatter.execute()
→ 模式分发（enhanced / classical）
→ run_enhanced() / run_classical()  [runners.py]
→ LLM 推理循环（含 Tool Call 执行）
→ SendTextAction / PassAndWaitAction → yield Success/Wait/Stop
```

`DefaultChatter.execute()`（`plugin.py:1136`）是 `AsyncGenerator`，yield 控制流信号：
- `Wait(time=None)` — 等待用户新消息（pass_and_wait）
- `Success(message)` — 本轮对话成功结束
- `Failure(error)` — 出错
- `Stop(time)` — N 秒后重新开始

**群聊 Sub-Agent 概率门**（`plugin.py:844-879`）：
- 基础直通概率：0.1
- 命中 Bot 名字加成：+0.7
- 命中别名加成：+0.4
- 每条未读消息加成：+0.05
- 上次回复成功后下一 tick 加成：+0.5
- 概率封顶 1.0

概率直通后跳过 `decide_should_respond()` LLM 子代理，直接进入主 DFC 循环。

### 5.2 被 life_engine 唤醒（`nucleus_wake_dfc` 接收侧）

life_engine 唤醒 DFC 有两种机制：

**机制 A — enqueue_dfc_message（异步留言）**

DFC 通过 `MessageNucleusTool.execute()`（`nucleus_bridge.py:24`）向 life_engine 投递消息：

```python
receipt = await service.enqueue_dfc_message(
    message=text, stream_id=stream_id, platform=platform,
    chat_type=chat_type, sender_name=sender_name,
)
```

life_engine 收到消息后，在心跳中处理，完成后将回复注入为 runtime assistant payload，DFC 下次被触发时读取。

**机制 B — push_runtime_assistant_injection（梦境/主动注入）**

life_engine 的 `DFCIntegration.inject_dream_report()`（`integrations.py:241`）直接调用 default_chatter 模块函数：

```python
push_runtime_assistant_injection(stream_id, payload_text)
```

该函数（`plugin.py:719`）维护线程安全的按会话 `deque`，每个 stream_id 最多缓存 24 条注入。DefaultChatter 在 `WAIT_USER` 阶段通过 `consume_runtime_assistant_injections(stream_id)` 消费，注入为 `ROLE.ASSISTANT` payload，形成上下文连续性。

### 5.3 DFC 向 life_engine 报告状态（`consult_nucleus` 调用侧）

**同步查询**（`ConsultNucleusTool`，`consult_nucleus.py:26`）：

```python
result = await service.query_actor_context(query_text)
```

`LifeEngineService.query_actor_context()` → `DFCIntegration.query_actor_context()` 组装快照：
- 调质层状态（curiosity/energy/contentment 等离散值）
- 最近 2 次心跳独白摘要（前 40 字）
- 工具使用偏好统计
- 活跃 TODO 列表
- 最近日记摘要

**深层记忆检索**（`SearchLifeMemoryTool`，`consult_nucleus.py:60`）：

```python
result = await service.search_actor_memory(query_text, top_k=5)
```

底层走 ChromaDB 向量相似度检索。

**智能记忆检索**（`IntelligentMemoryRetrievalTool`，`consult_nucleus.py:103`）：启动嵌套 sub-agent，自动执行 `search_life_memory` + `fetch_life_memory` 工具调用组合，最多 5 轮，汇总返回（`consult_nucleus.py:229-261`）。

### 5.4 Prompt 拼装：人格、记忆、SNN 状态、调质状态注入

**System Prompt 构建**（`prompt_builder.py:119`）：

```python
tmpl = get_prompt_manager().get_template("default_chatter_system_prompt")
result = await (
    tmpl.set("platform", ...)
       .set("chat_type", ...)
       .set("nickname", ...)
       .set("personality_core", get_core_config().personality.personality_core)
       .set("personality_side", ...)
       .set("reply_style", ...)
       .set("identity", ...)
       .set("background_story", ...)
       .set("theme_guide", ...)  # 私聊/群聊场景引导
       .build()
)
```

`default_chatter_system_prompt` 模板（`plugin.py:100`）包含：
- `<introduce>`：AI 生命体世界观
- `<personality>`：从 `config/personality.toml` 读入的名字、核心性格、表达风格、身份、背景故事
- `<behavioral_guidance>`：行为规范（4 条准则）+ 安全准则 + 负面行为禁忌 + 场景引导
- `<tool_usage>`：工具调用规范（Action/Tool/Agent 三类区分）+ 工具边界说明
- `<extra_info>`：平台与聊天类型

**User Prompt 构建**（`prompt_builder.py:185`）：

```python
tmpl.set("continuous_memory", "")   # 注入点：diary_plugin 的 ContinuousMemoryPromptInjector
    .set("history", history_text)   # 格式化历史消息
    .set("unreads", unread_lines)   # 未读消息（核心刺激）
    .set("extra", extra)            # 负面行为强化 + 临时上下文
    .set("stream_id", stream_id)    # 供 on_prompt_build 事件订阅者区分会话
    .build()
```

**SNN 与调质状态注入**：DFC 通过 `consult_nucleus` 工具按需拉取（非自动注入到 prompt），需要时以 Tool Result 形式出现在 LLM 上下文中。life_engine 的 `DFCIntegration.get_dfc_snapshot()` 包含调质层（neuromodulator）离散值摘要（`integrations.py:133-145`）。

**System Reminder 自动注入**：`SystemReminderBucket` 中 `actor` bucket 的内容（thinking_plugin 的思考习惯、booku_memory 的长期记忆使用原则）在每次 System Prompt 构建时自动追加。

---

## 6. 关联插件在"连续生命体"系统中的角色

### 6.1 `diary_plugin`——连续记忆骨干

**职责**：把每天的对话浓缩为日记，并构建跨会话的"连续记忆"层，解决 LLM 无状态带来的记忆断裂问题。

**核心机制**：

- `AutoDiaryEventHandler`（`event_handler.py:61`）订阅 `EventType.ON_CHATTER_STEP`：每当对话步骤发生，累计计数；达到阈值（默认 N 条消息）时调用 LLM 生成第一人称日记，追加到 `DiaryService`，并同步到 `ContinuousMemoryEntry`。
- `ContinuousMemoryPromptInjector`（`event_handler.py:387`）订阅自定义事件 `on_prompt_build`：每次 DFC user prompt 构建时，读取当前 stream_id 的连续记忆块，注入到 `{continuous_memory}` 占位符。注入格式用 XML 标签包裹：`<continuous_memory_block>...</continuous_memory_block>`。
- `DiaryService`（`service.py`）：JSON 文件存储日记，支持按日期、时间段（上午/下午/晚上/其他）写入；`render_continuous_memory_for_prompt()` 渲染注入文本。

**在连续生命体系统中的地位**：diary_plugin 是"短期记忆→长期事件流"的沉淀层，是生命连续性的直接实现。

---

### 6.2 `proactive_message_plugin`——主动社交驱动

**职责**：在用户沉默超过一定时长后，让 AI 主动发起话题或跟进之前的聊天内容。

**核心机制**：

- `ProactiveMessageService`（`service.py:77`）：单例，维护每个 `stream_id` 的 `StreamState`，追踪：最后用户消息时间、积累等待分钟数、下次检查时间、待执行的 follow-up 任务。
- 使用 `UnifiedScheduler` + `TriggerType.TIME` 创建延迟任务（`service.py:13`），在用户沉默超过配置阈值后触发主动消息生成。
- `PendingFollowup` 支持"post_reply"场景：DFC 在一次对话结束时，可以登记一个延迟续话任务（topic, thought, delay_seconds），由 proactive 插件调度执行。

**在连续生命体系统中的地位**：实现"主动性"——AI 不仅响应刺激，还能自发驱动社交互动。

---

### 6.3 `thinking_plugin`——内心独白层

**职责**：在 DFC 发送每次回复前，强制执行一次"内心活动"记录，提升响应质量与角色真实感。

**核心机制**（`plugin.py:43`）：

- `ThinkAction`（`actions/think_action.py`）：`action_name = "think"`，让 LLM 先输出内心活动，再调用 `send_text`。
- 插件加载时（`on_plugin_loaded`，`plugin.py:71`）通过 `get_system_reminder_store()` 向 `actor` bucket 注入思考习惯提示：

```
# 思考的习惯
当你准备回复用户时，先调用 action-think
然后在同一轮调用 action-send_text
thought 只写你的内心活动、分析和取舍
```

- `ThinkerTrigger`（`thinker_trigger.py`）：EventHandler，可能订阅 ON_CHATTER_STEP 等事件做额外触发。

**在连续生命体系统中的地位**：实现 CoT（Chain of Thought）风格的内省，使回应更符合"有血有肉"的角色形象，同时提供可观测的内心状态流。

---

### 6.4 `booku_memory`——书库式长期记忆

**职责**：基于向量数据库的结构化长期记忆，存储跨越时间的稳定背景知识（关系认知、用户偏好、自我认知、关键经历）。

**核心机制**（`service/booku_memory_service.py`）：

- 分为"固有记忆"（`inherent`）和"情景记忆"（episodic），分 folder 存储（`config.py:PREDEFINED_FOLDERS`）。
- 使用 `create_embedding_request()` 生成文本向量，存入 ChromaDB；检索时通过余弦相似度排序。
- `build_booku_memory_actor_reminder(plugin)`（`booku_memory_service.py:75`）：每次 system prompt 构建时，从固有记忆中拉取并注入 `## 固有记忆` 块。
- 配套工具 `memory_edit_inherent`：允许 LLM 整体改写固有记忆（不做增量追加，而是全量替换）。
- `ResultDeduplicator`（`service/result_deduplicator.py`）：检索结果去重，防止同质内容重复注入。

**在连续生命体系统中的地位**：diary_plugin 处理短期事件流，booku_memory 处理长期稳定特征，两者互补构成完整的两层记忆架构。

---

## 7. 跨插件通信——具体示例

### 示例 A：Service 暴露 + 直接调用

**diary_plugin 通过 ServiceManager 调用 DiaryService**（`event_handler.py:156`）：

```python
service = get_service("diary_plugin:service:diary_service")
if not isinstance(service, DiaryService):
    logger.warning("diary_service 未加载")
    return

today_content = service.read_today()
success, message = await service.append_entry(content=summary, section=section)
```

`get_service(signature)` → `ServiceManager.get_service_class(signature)` → 从 `GlobalRegistry` 查找 → 实例化 Service 类（注入 plugin 实例）→ 返回。

**default_chatter 通过 PluginManager 直接获取 life_engine 插件**（`nucleus_bridge.py:48`）：

```python
life_plugin = get_plugin_manager().get_plugin("life_engine")
service = getattr(life_plugin, "service", None)
receipt = await service.enqueue_dfc_message(...)
```

这是绕过 ServiceManager 的"直接插件引用"模式——通过 `get_plugin()` 获取插件实例后直接取 `service` 属性。

---

### 示例 B：EventHandler 订阅系统事件

**diary_plugin 订阅 `ON_CHATTER_STEP`**（`event_handler.py:69`）：

```python
class AutoDiaryEventHandler(BaseEventHandler):
    init_subscribe: list[EventType | str] = [EventType.ON_CHATTER_STEP]

    async def execute(self, event_name: str, params: dict[str, Any]) -> tuple[EventDecision, dict]:
        stream_id = params.get("stream_id")
        # ... 消息计数逻辑 ...
        return EventDecision.SUCCESS, params
```

`EventManager.register_plugin_handlers()` 在插件加载完成后，读取每个 `BaseEventHandler` 子类的 `init_subscribe`，调用 `event_bus.subscribe(event_name, handler, priority=weight)`。

---

### 示例 C：自定义事件 `on_prompt_build`

**diary_plugin 的 `ContinuousMemoryPromptInjector` 订阅**（`event_handler.py:393`）：

```python
init_subscribe: list[str] = ["on_prompt_build"]

async def execute(self, event_name: str, params: dict) -> tuple[EventDecision, dict]:
    values = params.get("values")
    stream_id = str(values.get("stream_id", ""))
    memory_block = service.render_continuous_memory_for_prompt(stream_id, ...)
    values["continuous_memory"] = _wrap_continuous_memory_block(memory_block)
    return EventDecision.SUCCESS, params   # 修改了 params["values"]，但 key 集合不变
```

`PromptTemplate.build()` 在渲染前发布 `on_prompt_build` 事件，订阅者通过修改 `params["values"]` 字典中的内容来注入数据，params 的 key 集合保持不变（符合 EventBus 协议）。

---

## 8. 测试覆盖

### 8.1 目录结构

```
test/
├── kernel/
│   ├── llm/          （20 个测试文件，最完整）
│   ├── test_concurrency.py
│   ├── test_config.py
│   ├── test_db.py
│   ├── test_event.py
│   ├── test_logger.py
│   ├── test_scheduler.py
│   ├── test_storage.py
│   └── test_vector_db.py
├── core/
│   ├── test_components_base_action.py
│   ├── test_components_base_chatter.py
│   ├── ... （所有 11 种组件类型各有独立测试文件）
│   ├── test_components_registry.py
│   ├── test_models_message.py
│   ├── transport/
│   └── prompt/
├── app/
│   └── （较少，主要覆盖 plugin_system API）
├── plugins/
│   ├── test_default_chatter_*.py  （9 个文件，涵盖 DFC 各子模块）
│   ├── test_diary_plugin_*.py
│   ├── test_proactive_message_*.py
│   ├── test_thinking_plugin_*.py
│   ├── test_life_state_integration.py
│   ├── life_engine/
│   └── booku_memory/
└── test_snn_bridge.py / test_snn_core.py  （SNN 独立模块测试）
```

### 8.2 覆盖率评估（静态）

| 模块              | 测试文件数 | 覆盖深度                            |
|-------------------|------------|-------------------------------------|
| `kernel/llm`      | 20         | 非常充分，含 request、policy、retry、streaming、token_counter 等 |
| `kernel/*` 其他   | 8          | 中等，每个子模块有基础测试           |
| `core/components` | 13+        | 充分，11 种组件类型均有独立测试文件  |
| `core/prompt`     | 有专属目录  | 中等                                |
| `plugins/default_chatter` | 9 | 较充分，覆盖 sub-agent、prompt、nucleus bridge、runners 等 |
| `plugins/diary_plugin` | 2  | 基础覆盖                            |
| `plugins/life_engine` | 有专属目录 | 部分（含 SNN 独立测试）             |
| `plugins/booku_memory` | 有专属目录 | 基础覆盖                           |
| `app/runtime`     | 无专属      | 几乎无测试（bot 启动流程未测试）    |

存在 3 个 `.disabled` 后缀文件（`test_expression_learning_*.py.disabled`、`test_notice_injector.py.disabled`），说明有功能正在开发或已废弃。

---

## 9. 未解之谜

1. **配置热重载缺失**：`config/core.py` 注释提及 "Pydantic + TOML 的热重载"，但代码中只有 `init_core_config()` 一次性加载，未发现任何 `inotify`/`watchdog` 机制。是否有计划实现？

2. **`TriggerType.EVENT` 为空壳**：`scheduler/types.py:17` 标注"预留，未来集成 event 模块"，`UnifiedScheduler._event_subscriptions` 字段存在但无任何实际路由逻辑。scheduler 与 event bus 的联动尚未实现。

3. **WatchDog 双重初始化**：`bot.py:295-296`（Step 4）已调用 `get_watchdog().start()`，`bot.py:310-311`（Step 6）又创建了 `WatchDog()` 新实例赋给 `self.watchdog`，两者是同一单例还是两个实例？`self.watchdog` 在后续代码中是否被实际使用？

4. **life_engine → default_chatter 的裸模块引用**（`integrations.py:266`）：`from default_chatter import plugin as default_chatter_plugin_module` 直接 import 外置插件模块，绕过了 ServiceManager。这意味着两个插件存在强编译时耦合，若 `default_chatter` 未加载则抛 ImportError。是否应改为 service API 或 event 总线解耦？

5. **`GlobalRegistry` 的全局单例与测试隔离**：组件注册表是全局单例，跨测试用例污染的风险高。测试文件中是否有 fixture 做重置？`conftest.py` 内容值得深入检查。

6. **`mofox-wire` 协议细节未公开**：`mofox_wire.MessageEnvelope` 是外部包，仓库中无源码，协议格式、字段定义未知。是否有独立文档？

7. **SNN（脉冲神经网络）与 neuromod 的涌现机制**：`plugins/life_engine/snn/` 和 `neuromod/` 是系统哲学"自下而上涌现"的核心载体，但代码调研范围不含 life_engine 内部。`DFCIntegration._build_state_digest_locked()` 只读取了 `modulators.get_discrete_dict()`，SNN 驱动的行为决策逻辑（如 drive 驱动主动发言的阈值计算）未被本次报告覆盖。

8. **`test_snn_bridge.py` / `test_snn_core.py` 在根目录**：这两个测试文件不在 `test/` 的标准子目录结构中，是特例还是遗留？

9. **`plugins/data/` 目录**：`plugins/data/` 的内容和用途待查，是否是插件共享数据目录？

10. **`run_classical` vs `run_enhanced` 的区别**：`runners.py` 提供两种执行模式，`enhanced` 模式保留"原有行为"，`classical` 模式是新的简化路径还是旧版兼容路径？两者在 prompt 构建和 LLM 调用策略上的具体差异需要进一步阅读 `runners.py` 全文。

---

*本报告基于代码静态分析，所有引用格式为 `文件路径:行号`，如 `src/kernel/event/core.py:65`。*
