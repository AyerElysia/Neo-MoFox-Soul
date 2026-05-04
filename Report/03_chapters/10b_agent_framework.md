# 第 10.5 章 · Agent 框架工程：工具设计、上下文组装与推理循环

> *"让 LLM 有手有脚，是让它能够真正行动的工程基础；让它知道自己是谁、现在在哪、心情如何，是让它能够连续存在的上下文基础。两者缺一不可。"*
> — *设计备忘录*

---

本章填补前几章未覆盖的关键工程层次：**工具设计范式**（LLM 如何获得"手脚"）与**上下文组装管线**（LLM 如何获得"自我感知"）。这两层共同构成 DFC 调用 LLM 时的完整输入——没有它们，第 4–10 章描述的所有子系统（SNN、调质、记忆、心跳）都将是"有状态但无法表达"的孤岛。

在架构上，本章描述的机制位于 `plugins/default_chatter/` 与 `src/core/` 的接缝处，是 DFC 的实现核心。

---

## 10.5.1 工具设计范式：Tool、Action、Agent 三分类

### 10.5.1.1 三类组件的哲学差异

Neo-MoFox 把 LLM 可调用的组件分为三种，背后有清晰的设计哲学：

| 类型 | 基类 | 执行方式 | 哲学定位 | 典型例子 |
|------|------|---------|---------|---------|
| **Tool** | `BaseTool` | 同步/异步函数，无副作用 | **查询**：获取信息，不向用户发消息 | `consult_nucleus`、`search_life_memory`、`calculator` |
| **Action** | `BaseAction` | 异步，有副作用 | **响应**：执行外部动作，可向用户发消息 | `action-send_text`、`action-think`、`action-send_image` |
| **Agent** | `BaseAgent` | 异步，可递归调用 LLM | **子代理**：独立推理单元，可自主调用工具 | `agent-life_memory_explorer`、`retrieve_memory` 内置 sub-agent |

这一三分类不是形式上的区分，而是工程上的**隔离设计**：Tool 不感知 ChatStream，因此不能主动向用户发消息；Action 绑定 ChatStream，但不能递归调用 LLM；Agent 可以递归，但会在独立的推理上下文中运行，不污染主 DFC 的上下文窗口。三层边界防止了常见的 Agent 失控问题（工具调用链无限递归、副作用不可控）。

### 10.5.1.2 Schema 自动生成机制

LLM 调用工具的前提是"知道工具的存在和用法"。Neo-MoFox 通过 `to_schema()` 类方法，从 `execute()` 的 **Python 类型注解**自动生成 OpenAI Tool Calling 格式的 JSON Schema，无需手动维护文档：

```python
class ConsultNucleusTool(BaseTool):
    tool_name = "consult_nucleus"
    tool_description = "向生命中枢同步查询当前状态层信息..."

    async def execute(
        self,
        query: Annotated[str, "想问中枢的状态问题，例如'最近在想什么'"],
    ) -> tuple[bool, str]:
        ...
```

`to_schema()` 通过 `inspect.get_annotations()` 提取参数名、类型和 `Annotated` 中的文档字符串，自动生成：

```json
{
  "type": "function",
  "function": {
    "name": "consult_nucleus",
    "description": "向生命中枢同步查询当前状态层信息...",
    "parameters": {
      "type": "object",
      "properties": {
        "query": {"type": "string", "description": "想问中枢的状态问题..."}
      },
      "required": ["query"]
    }
  }
}
```

这一自动生成机制有两个重要推论：
1. **工具文档即代码注解**——工具开发者只需在 `Annotated[type, "描述"]` 中写好文档，Schema 自动保持同步；
2. **强制函数签名即接口契约**——参数类型和必填项由 Python 类型注解决定，LLM 若传入错误类型，Python 类型系统会在执行前捕获。

此外，系统会自动处理一个特殊参数：`reason: Annotated[str, "..."]`。若检测到工具组件本身没有声明 `reason` 参数，但 LLM 幻觉性地在调用中附带了 `reason` 字段，`should_strip_auto_reason_argument()` 会在执行前自动剥除，避免"未知参数"报错（见 `src/core/components/utils.py`）。

![Figure F18 · 工具注册与 Schema 生成流程](../figures/F18_tool_schema_pipeline.svg)

**图 F18** 展示了从类定义到 LLM 接收工具描述的完整流程：组件类通过 `to_schema()` 产出 JSON Schema，注册到 `ToolRegistry`，以 `ROLE.TOOL` payload 的形式随每次 LLM 请求发送。

### 10.5.1.3 上下文感知过滤：三道动态裁剪机制

注册到 `ToolRegistry` 的工具不是对 LLM 无条件全部可见的——每轮推理前，`modify_llm_usables()` 会应用三道过滤：

**① `chatter_allow` 列表**：工具可声明"只允许特定 chatter 使用"。例如 `ConsultNucleusTool` 声明 `chatter_allow = ["default_chatter"]`，防止其他 chatter（如 debug chatter）错误使用生命中枢查询。

**② `associated_types` 适配器检查**：Action 类组件可声明 `associated_types`，只有当前 ChatStream 的适配器类型匹配时才允许执行。这防止了"在不支持图片的纯文本平台上调用 send_image"之类的错误。

**③ `go_activate()` 自声明激活**：每个组件可实现 `go_activate()` 方法，在每轮推理时根据**当前上下文状态**决定自己是否应当可见。例如，一个"查询日历"工具可在检测到当前日期相关问题时激活，其他时候隐藏，减少工具列表长度，提升 LLM 决策质量。

### 10.5.1.4 MCP 外部工具统一集成

Model Context Protocol（MCP）是标准化 LLM 工具调用的外部协议。`MCPManager` 通过 `MCPToolAdapter` 将外部进程（Stdio/SSE 模式的 MCP 服务器）暴露的工具统一适配成 `BaseTool` 接口，并注册到全局 `ToolRegistry`。

这意味着：**无论工具是本地 Python 函数还是远程进程，在 DFC 和 LLM 看来是同构的**。工具列表可以在运行时通过 `MCPManager.initialize()` 动态扩展，不需要重启 Bot 主进程。

---

## 10.5.2 上下文组装管线：三层叠加架构

DFC 在每次调用 LLM 前，需要把"系统告知 LLM 它是谁"（系统层）与"告知 LLM 当前发生了什么"（用户层）组装成完整的上下文。`DefaultChatterPromptBuilder` 负责这一工作，内部分为三个逻辑层次。

### 10.5.2.1 系统 Prompt 层（静态 + 会话固定）

系统 prompt 由 `build_system_prompt()` 构建，内容在一次对话会话内几乎不变：

- **人格核心**：`personality_core`（核心性格描述）、`personality_side`（侧面描述）、`reply_style`（回复风格）、`identity`（身份定义）、`background_story`（背景故事）——均来自 `core_config.personality`，由用户在配置文件中定义
- **场景引导**：`theme_guide.private`（私聊引导）或 `theme_guide.group`（群聊引导），根据 `chat_type` 自动选择
- **会话元信息**：平台名称、Bot 昵称、Bot ID——来自 `adapter_api.get_bot_info_by_platform()`
- **技能目录**：可选的 `skill_catalog` 文本，简要说明当前可用工具集

系统 prompt 通过 `PromptTemplate`（见 §10.5.2.3）渲染，以 `ROLE.SYSTEM` payload 的形式附加到 LLM 请求头部。

### 10.5.2.2 用户 Prompt 层（动态，每轮重建）

用户 prompt 由 `build_user_prompt()` 构建，包含本轮推理所需的全部动态信息：

```
[会话名称 + 当前时间 + 平台信息]
[历史消息块 (history)]
[未读消息块 (unreads)]
[连续记忆块 (continuous_memory)]
[extra 信息块]
```

各块来源：
- **`history`**：`chat_stream.context.history_messages` 中的历史消息，按 `formatter` 格式化为"时间戳: 发送者: 内容"格式
- **`unreads`**：本轮待处理的新消息列表（`unread_msgs`），格式同上
- **`continuous_memory`**：长期运行的对话流中，跨 prompt 持续注入的记忆摘要（由 `inject_continuous_memory=True` 控制）
- **`extra`**：可插拔的额外信息块，包含负面行为提醒（`build_negative_behaviors_extra()`）、会话动态上下文（`build_runtime_context_extra()`）等

用户 prompt 以 `ROLE.USER` payload 附加，是每轮推理的主体输入。

### 10.5.2.3 PromptTemplate 引擎：占位符替换与渲染策略

上述两层的构建均通过 `PromptTemplate` 完成，这是一个支持**链式调用**与**渲染策略**的轻量级模板引擎：

```python
prompt = await (
    tmpl
    .set("history", history_text)
    .set("unreads", unread_lines)
    .set("extra", extra_info)
    .set("stream_id", chat_stream.stream_id)  # 仅作为事件元数据，不出现在模板正文
    .build()
)
```

`build()` 在渲染前会先触发 `on_prompt_build` 事件（通过 `EventBus`），**允许任意插件订阅并修改模板的 values、template 或 policies**，然后再执行最终渲染。这是一个关键的扩展点：连续记忆插件、notice 系统、Nucleus 状态注入，都通过订阅此事件实现对 LLM 上下文的无侵入插入，而不需要修改 DFC 的核心代码。

渲染策略链（`RenderPolicy`）控制每个占位符的渲染行为：
- `optional()`：值为空时渲染为空字符串（默认）
- `trim()`：去除首尾空白
- `min_len(n)`：值长度不足 n 时抑制整块（返回空）
- `header("# ...")`：在非空值前加标题前缀

策略支持链式组合：`trim().then(min_len(5)).then(header("# 知识库内容："))`。

### 10.5.2.4 Nucleus 状态注入层（第三层）

在系统层和用户层之外，还有一层专门负责把 Life Engine 的**实时内在状态**注入 DFC 上下文，实现了第 10 章描述的双向接口中"DFC 感知 Nucleus"的部分（见图 F19）：

- **`consult_nucleus` 工具**（主动 pull）：LLM 在推理过程中若需要了解当前 drives/neuromod/TODO/日记状态，主动调用此工具。工具向 `life_engine.service.query_actor_context()` 发同步查询，返回当前内在状态文本摘要。
- **`push_runtime_assistant_injection`**（Life Engine 主动 push）：做梦循环（NREM/REM）完成后，通过此机制把"梦境余韵"或离线巩固结论注入下次 DFC 激活时的 assistant 上下文（即 `ROLE.ASSISTANT` payload），让 LLM 在次日首次被触发时"记得昨晚想了什么"。
- **`nucleus_bridge` 心跳注入**：Life Engine 心跳触发 `nucleus_wake_dfc()` 时，携带当前内在状态快照，注入 DFC 的 user extra 块，作为当次主动发言的"情绪基底"。

![Figure F19 · 上下文组装层次图](../figures/F19_context_assembly.svg)

**图 F19** 以层次图展示了三层叠加结构与 Nucleus 注入机制的关系：系统层提供静态人格定义，用户层提供动态会话信息，Nucleus 注入层通过事件总线将内在状态渗透进任意层。

---

## 10.5.3 多轮推理循环：Enhanced 模式状态机

DFC 的 Enhanced 模式（`run_enhanced()` in `runners.py`）实现了一个完整的**多轮推理循环**，是 Neo-MoFox 作为"有手有脚的 Agent"的实际运转核心。

### 10.5.3.1 状态机四态

推理循环可以抽象为四状态有限自动机（图 F20）：

| 状态 | 触发条件 | 含义 |
|------|---------|------|
| **INIT** | 新消息到达 / 心跳唤醒 | 组装 System + User Prompt，构建工具列表，发送首次 LLM 请求 |
| **TOOL_CALLING** | LLM 响应包含 ToolCall | 解析调用列表，执行工具，写回结果，继续推理（可循环） |
| **WAIT** | LLM 调用 `pass()` 控制原语 | 本轮无主动发言，挂起等待用户新消息 |
| **DONE** | LLM 无 tool calls（直接回复）/ action-only 完成 | 流式写回用户，完成本轮执行，yield `Success` |
| **STOP** | LLM 调用 `stop(minutes=N)` 控制原语 | 对话结束，N 分钟内挂起，Life Engine 心跳继续 |

`WAIT` 与 `STOP` 的区别微妙但重要：`WAIT` 表示 LLM 主动等待用户，随时会被新消息激活；`STOP` 表示 LLM 判断对话已自然结束，不主动等待，直到 N 分钟定时器到期（或 Life Engine 心跳触发）才允许新对话。

### 10.5.3.2 工具调用的并行调度

在 `TOOL_CALLING` 状态中，单轮内的多个 ToolCall 不总是顺序执行。`run_llm_usable_executions()` 实现了一个**门控并行调度器**：

```
所有 Tool/Agent 的执行包装对象（LLMUsableExecution）并发启动
每个对象在"准备完成"（_READY）时暂停，等待前面的对象全部完成后才继续
Action 类对象则立即执行（flush_pending_calls），不等待
```

这一设计的工程意义：Tool 类调用（查询数据库、访问 Nucleus）通常是幂等的，可以安全并行；Action 类调用（发送消息）有顺序依赖，必须等前序非 Action 调用完成后按序执行。"门控并行"在最大化并行效率的同时，保证了结果的确定性顺序。

### 10.5.3.3 think-only 保护与重试限制

LLM 有时会只调用 `action-think`（内部推理，不发消息），而不产生任何可见动作。这在连续多轮出现时通常意味着模型陷入了"思考但无动作"的循环。Enhanced 模式检测连续 think-only 调用次数，达到上限时强制注入提示："请在下一轮中给出具体回复或调用 pass/stop"，并向 TOOL_CALLING 状态的出口施压。

### 10.5.3.4 Classical 模式对比

除了 Enhanced 模式，DFC 还支持 `classical` 模式（`run_classical()`），后者在 Enhanced 的多轮循环之外做了一个限制：`break_on_send_text=True` 时，**一旦 `action-send_text` 成功执行，后续所有非 Action 调用自动跳过**，LLM 不再继续推理。

Classical 模式牺牲了多轮推理的灵活性，换来了延迟确定性——适合对响应时间有严格要求的场景。两种模式在 `plugin.mode` 配置项中切换，互不影响底层工具注册和 Schema 生成逻辑。

![Figure F20 · 多轮推理循环状态机](../figures/F20_reasoning_loop_fsm.svg)

**图 F20** 展示了 Enhanced 模式的完整状态机，包含四态转移、三个控制流出口（pass/stop/done）以及 TOOL_CALLING 的自循环推理路径。

---

## 10.5.4 工具调用的去重与顺序保证

多轮推理循环中存在一个潜在问题：LLM 可能在同一轮内对同一工具以相同参数调用两次（幻觉性重复），或跨轮对同一工具反复调用（陷入循环）。`process_tool_calls()` 提供了两层去重保护：

### 10.5.4.1 本轮去重

`seen_call_signatures`（`set[str]`）在单次 `process_tool_calls()` 调用内维护本轮已见的调用签名。签名由 `_build_call_dedupe_key()` 生成：

```python
def _build_call_dedupe_key(call_name: str, args: object) -> str:
    # 参数按 key 排序后 JSON 序列化，确保参数顺序不同但内容相同的调用被识别为重复
    serialized = json.dumps(args, sort_keys=True, separators=(",", ":"))
    return f"{call_name}:{serialized}"
```

特别地，`reason` 参数在签名计算时被剥除——`reason` 是 LLM 的自我解释字段，不影响工具语义，不应当因 `reason` 措辞不同而认为是不同调用。

当检测到重复时，系统向 response 写入 `TOOL_RESULT`："检测到同一轮重复工具调用，已自动跳过"，并继续处理后续调用。LLM 会在下一轮推理中看到这条跳过通知，通常会选择不再重复。

### 10.5.4.2 跨轮去重

`cross_round_seen_signatures`（跨轮共享的 `set[str]`）在 Enhanced 模式的多轮循环中**跨轮持续积累**。这防止了"LLM 在第一轮用 A 参数调 tool X，写回结果，第二轮忘了结果又以 A 参数调了一次"的问题。

跨轮去重的设计取舍：它假设同参数调用在同一完整推理会话内只需执行一次；对于需要刷新的查询（如时间、随机数），工具实现者应确保参数中包含时间戳或随机性，使签名自然不同。

### 10.5.4.3 结果顺序保证

`run_tool_call()` 的返回列表与输入 `calls` 列表**严格保持顺序一致**。即使内部使用并行调度，结果写回 `response` 的顺序也由原始调用顺序决定。这一设计防止 LLM 在下一轮推理时因上下文乱序而产生混乱（"我先调了 A 再调 B，但上下文里 B 的结果出现在 A 前面"）。

### 10.5.4.4 Watchdog 喂狗

工具调用可能耗时较长（例如 sub-agent 递归调用 LLM）。`process_tool_calls()` 在处理每个 call 前调用 `get_watchdog().feed_dog(stream_id)`，防止 Watchdog 将"正在执行工具"误判为"推理超时"并强制中断会话。

---

## 10.5.5 上下文窗口压缩：确定性摘要机制

LLM 的上下文窗口有限，长时间运行的对话流必然需要丢弃早期的 payload。Neo-MoFox 使用**确定性压缩钩子**（`build_default_chatter_compression_hook()`），在丢弃 payload 前将其转换为摘要文本。

### 10.5.5.1 触发机制

当 LLM 请求的 payload 总长度超过上下文窗口限制时，框架按会话组（`group`，即一轮完整的用户消息 + LLM 响应 + 工具调用）从最旧开始丢弃。每批被丢弃的组会传入压缩钩子。

### 10.5.5.2 摘要生成策略

压缩钩子的核心参数：

| 参数 | 值 | 含义 |
|-----|---|------|
| `_MAX_SUMMARY_GROUPS` | 8 | 最多汇总最近 8 组被丢弃的会话 |
| `_MAX_SUMMARY_CHARS` | 3200 | 摘要总长度上限 |
| `_MAX_TEXT_CHARS` | 220 | 单条 assistant/user 文本截断长度 |
| `_MAX_TOOL_RESULT_CHARS` | 220 | 单条 TOOL_RESULT 截断长度 |
| `_MAX_TOOL_ARGS_CHARS` | 900 | 工具调用参数截断长度 |

摘要格式将被丢弃的会话组渲染为结构化文本，以 `ROLE.USER` payload 注入到保留 payload 序列的最前面，形如：

```
[历史摘要，已压缩 N 组]
第1组：用户说"..." → 助手执行了 tool_X(参数) → 结果: "..."
第2组：助手说"..."
...
```

LLM 在新一轮推理中仍能"看到"这些被压缩的历史，以摘要形式保留了关键语义，而不会因为上下文滚动而完全失忆。这是 Neo-MoFox 连续性原则（C2 不变式：状态不可突变清除）在上下文管理层面的工程实现。

---

## 10.5.6 Nucleus 状态注入的三种工具及使用边界

第 10 章描述了 DFC ↔ Life Engine 的三种接口；本节从**工具实现**角度深入其中 LLM 可直接调用的部分。

### 10.5.6.1 `consult_nucleus`：当前状态摘要

最轻量的一种：LLM 主动调用，向 `life_engine.service.query_actor_context(query)` 发同步请求，返回当前内在状态的文本摘要（drives 值、neuromod 浓度、活跃 TODO、最近日记片段）。

**设计约束**：此工具不做历史记忆检索，不翻文件——它只返回"此刻"的状态。若 LLM 误用它来反复查询过去发生的事，工具描述中有明确警告："不要拿它反复追问同一个历史主题"。

### 10.5.6.2 `search_life_memory`：关键词记忆检索

做轻量的记忆索引检索：接收 `query`（主题/关键词）和 `top_k`（返回条数），向 Life Engine 的记忆索引发请求，返回 top_k 条记忆节点的摘要文本。

适用场景：用户问"你还记得我们上次聊的那件事吗？"LLM 应先调 `search_life_memory` 拿到摘要，再决定是否需要调 `fetch_life_memory` 拿完整内容。

### 10.5.6.3 `retrieve_memory`：sub-agent 智能检索

最重量级的选项：内部启动一个独立的 LLM sub-agent（使用 `sub_actor` 模型集），sub-agent 有权限访问 `search_life_memory` 和 `fetch_life_memory` 两个工具，并根据 `detail_level`（brief/normal/detailed/auto）自主决定是否需要进一步拉取完整文件。主 DFC 的 LLM 调用 `retrieve_memory` 并等待结果，最终获得经 sub-agent 整合的检索报告。

三工具的使用层次构成了一个**从轻到重的检索梯度**：当 LLM 判断问题与历史无关时不调任何工具；当问题涉及当前内在状态时调 `consult_nucleus`；当问题涉及过去记忆摘要时调 `search_life_memory`；当问题需要完整历史上下文时调 `retrieve_memory`。这一梯度设计避免了"每轮都全量拉取记忆"的上下文污染问题。

---

## 10.5.7 设计对比：Neo-MoFox 与 LangChain/AutoGPT 的工具哲学差异

| 维度 | LangChain / AutoGPT | Neo-MoFox |
|------|---------------------|-----------|
| **工具定义** | 函数或类，Schema 手动编写或装饰器注入 | `BaseTool` 子类，Schema 由 `Annotated` 类型注解自动推导 |
| **工具执行** | 顺序执行，部分框架支持并行 | 门控并行调度（Tool 并行，Action 顺序，结果保序写回）|
| **上下文状态** | 通常无状态（每轮重建）或依赖外部 Memory 模块 | 上下文中包含 SNN/调质/心跳等**连续演化的内在状态**，经 Nucleus 注入层渗透 |
| **工具过滤** | 通常全量注册，无动态裁剪 | `chatter_allow` + `associated_types` + `go_activate()` 三层过滤 |
| **上下文压缩** | 通常靠 `ConversationBufferWindowMemory` 简单截断 | 确定性摘要钩子，保留语义摘要而非简单截断 |
| **工具副作用隔离** | 不区分查询和动作 | Tool（无副作用）/ Action（有副作用）/ Agent（可递归）三类严格隔离 |
| **内在状态感知** | 无（LLM 不感知 Agent 自身状态） | 通过 `consult_nucleus` / `push_runtime_injection` / 心跳注入，LLM 感知 SNN 激活度、调质浓度、习惯强度 |

这一对比揭示了 Neo-MoFox 工程选择的深层逻辑：它的工具框架不是为了"让 LLM 完成任务"，而是为了"让 LLM 在连续演化的内在状态中行动"。工具是 LLM 与外部世界和自身状态交互的窗口，上下文是它每轮推理时的"记忆快照"，而推理循环则是两次心跳之间 LLM 感知-决策-执行的闭环。

---

## 10.5.8 小结

本章从工程层面补全了 Neo-MoFox Agent 框架的内部实现：

1. **工具设计**：Tool/Action/Agent 三类组件边界清晰；Schema 由类型注解自动生成；三道过滤机制保证工具列表的上下文相关性；MCP 适配器统一外部工具接口。
2. **上下文组装**：三层叠加（系统层/用户层/Nucleus 注入层）；`PromptTemplate` 引擎支持策略渲染和事件钩子，实现对 LLM 上下文的无侵入扩展。
3. **推理循环**：Enhanced 模式实现四态状态机；门控并行调度保证并行效率与顺序确定性；两层去重防止工具调用循环；Watchdog 喂狗保证长调用的稳定性。
4. **上下文压缩**：确定性摘要钩子在滚动丢弃历史时保留语义摘要，工程化实现了连续性原则在上下文管理层面的约束。
5. **Nucleus 注入梯度**：三种工具（`consult_nucleus` / `search_life_memory` / `retrieve_memory`）构成轻-中-重三档检索梯度，在上下文效率与信息完整性之间取得平衡。

从连续性原则（C1–C4）的角度看，上述机制共同保证了"LLM 在每一轮推理时，都不是从空白状态出发，而是从一个包含历史摘要、内在状态快照、当前会话上下文的连续状态快照出发"——这正是 Neo-MoFox 区别于普通 LLM chatbot 的核心工程差异。
