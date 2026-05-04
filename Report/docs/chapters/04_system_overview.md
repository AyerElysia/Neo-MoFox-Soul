# 第 4 章 · 系统总览：双意识异步运行与三层结构

> *"我们现在的系统不是一个聊天壳加一个后台插件，而是同一主体的两种运行相位：LifeChatter 负责把自己说出来，Life Engine 负责在没有说话时仍然继续想、继续变。"*

---

## 4.0 无人系统视角下的 Neo-MoFox 设计

从《智能感知与无人系统》的学科视角看，Neo-MoFox 解决的是一个可迁移到软件 Agent 的无人系统问题：**如何在无外部触发的情况下维持系统的自主感知与决策连续性**。

传统无人系统（无人车、无人机、服务机器人）通常被描述为"感知→规划→控制"闭环。软件 Agent 没有物理传感器和执行器，但它面临相同的结构性要求：系统不能只在用户输入到达的一瞬间被动响应，还需要在低输入、弱通信或长期运行过程中保持状态更新。否则，感知参数难以随时间漂移自动校准，决策倾向难以在不重新训练的前提下持续演化，多时间尺度的内部动态也很难在同一框架内统一处理。

Neo-MoFox 当前的回答是 **LifeChatter + Life Engine**：

1. **LifeChatter（社交主意识）**：面向用户的表达与行动层。它读取人格、上下文、记忆、运行态快照和 ThoughtStream，决定是否回复、如何回复、是否调用工具、是否记录内心独白。
2. **Life Engine（潜意识 / 生命中枢）**：后台连续运行层。它以心跳循环推进 SNN、调质、记忆、做梦、事件流、习惯和 ThoughtStream，不依赖外部输入持续存在。
3. **异步同步层**：二者通过运行态快照、内心独白、ThoughtStream 焦点、梦境残影和事件高水位进行同步。同步不是阻塞式 RPC，而是让主意识在需要表达时读取潜意识已经积累的状态。

因此，本报告不再把早期 DFC/default_chatter 作为当前架构核心。DFC 属于旧时代的对话桥接形态；当前 Neo-MoFox 的核心是双意识异步运行。

![Figure F4 · 双意识异步运行：LifeChatter + Life Engine](/root/Elysia/Neo-MoFox/Report/04_figures/F4_dual_consciousness_async.png)

*Figure F4 · LifeChatter 以用户消息节律运行，Life Engine 以心跳节律运行；二者通过内心独白、状态快照、ThoughtStream 与梦境残影异步同步。*

## 4.1 双意识异步运行

“双意识”不是声称系统真的拥有意识，而是一个工程分层术语：

| 相位 | 工程组件 | 触发方式 | 主要责任 |
|---|---|---|---|
| 社交主意识 | `LifeChatter` | 用户消息、主动机会、续话机会 | 对话表达、工具调用、行动输出、内心独白记录 |
| 潜意识 | `LifeEngineService` | 30 秒心跳、睡眠窗口、事件流变化 | 状态推进、记忆巩固、SNN/调质更新、ThoughtStream 管理 |
| 注意力桥 | `ThoughtStreamManager` + runtime snapshot | revision / high-water 同步 | 把潜意识持续在意的问题同步给主意识 |

这种划分有三个直接效果。

第一，**对话不再是无状态壳**。LifeChatter 在每轮请求中不只读取聊天历史，还读取 Life Engine 的运行态快照、记忆提示、思考流焦点和临时注入的内心独白。

第二，**潜意识可以先于表达发生**。Life Engine 可以在用户没有发消息时推进 ThoughtStream、生成梦境残影、更新调质浓度或记录内在状态。等 LifeChatter 下次被触发时，这些状态已经成为可表达的上下文。

第三，**异步性避免互相阻塞**。Life Engine 不需要等待 LifeChatter 何时开口；LifeChatter 也不需要把每次回复都变成一次完整后台计算。二者通过快照和队列交接信息，保留各自的运行节律。

## 4.2 三层异质子系统

在双意识之下，Neo-MoFox 仍然采用三层异质结构。这里的“层”不是物理脑区，而是计算角色：

| 层 | 工程角色 | 主要责任 | 实现位置 |
|---|---|---|---|
| 主意识层 | LifeChatter + LLM | 语言表达、推理、工具选择、社会化行动 | `plugins/life_engine/core/chatter.py` |
| 调质层 | Neuromodulation | 情态慢变量、昼夜节律、习惯稳态 | `plugins/life_engine/neuromod/` |
| 皮层下快层 | SNN + drives | 事件响应、本地可塑性、驱动信号 | `plugins/life_engine/snn/` |
| 长期上下文层 | Memory + Dream + ThoughtStream | 记忆检索、离线巩固、注意力焦点 | `plugins/life_engine/memory/`, `dream/`, `streams/` |

这几层有明确的信号链：

```text
事件流
  -> SNN 特征向量
  -> drive 输出
  -> 调质刺激与状态更新
  -> 记忆检索 / ThoughtStream 焦点 / 梦境残影
  -> LifeChatter 上下文组装
  -> LLM 推理与行动
  -> 新事件回写 Life Engine
```

这一链条使系统具有闭环性质：外部交互会改变内部状态，内部状态又会影响后续表达，而后续表达继续成为新的事件输入。

## 4.3 ThoughtStream：潜意识管理的注意力流

ThoughtStream 是本轮报告中需要显著强调的设计。它不是任务列表，也不是普通聊天摘要，而是系统“最近一直在琢磨什么”的持久兴趣线索。

在实现上，`ThoughtStreamManager` 维护若干条思考流，每条包含：

- `title`：思考主题；
- `last_thought`：最近一次内心推进；
- `curiosity_score`：好奇心强度；
- `last_focused_at`：最近进入注意力焦点的时间；
- `last_decay_at`：好奇心半衰期衰减锚点；
- `revision`：单调递增版本，用于 LifeChatter 端增量同步。

这个设计受到脑科学注意力网络的启发。经典研究通常区分目标驱动的背侧注意网络与显著事件驱动的腹侧注意网络；前者更像“我主动持续关注什么”，后者更像“某个突发线索把注意力重新拉走”。Neo-MoFox 借用这个划分来解释 ThoughtStream：

- **当前焦点**：近期被推进、仍处在 `focus_window_minutes` 内的思考流，对应目标驱动的持续关注。
- **背景在意**：好奇心仍然较高但不在当前焦点窗口内的思考流，对应潜意识中未完全消失的兴趣线索。
- **重定向**：新事件、梦境残影或记忆检索使休眠思考流重新激活，对应显著事件引发的注意力切换。

这只是工程类比，不表示系统实现了真实脑区。它的价值在于提供一个可观测、可持久化、可同步给主意识的注意力机制。

![Figure F21 · ThoughtStream 与注意力网络的工程类比](/root/Elysia/Neo-MoFox/Report/04_figures/F21_thought_stream_attention.png)

*Figure F21 · ThoughtStream 借用背侧/腹侧注意网络的功能划分来组织“当前焦点 / 背景在意 / 重定向”。图为工程隐喻，不是医学或神经科学等价断言。*

## 4.4 多时间尺度耦合

Neo-MoFox 的连续性来自多时间尺度并行运行：

| 时间尺度 | 状态变量 | 演化方式 | 典型触发 |
|---|---|---|---|
| 秒级 | SNN 神经元活动度、drive | LIF step + EMA | SNN tick |
| 30 秒级 | Life Engine 心跳状态 | 事件采样、状态推进、持久化 | heartbeat |
| 分钟–小时 | 调质浓度 | ODE 回归与刺激项 | heartbeat / circadian |
| 小时–天 | ThoughtStream 焦点与好奇心 | advance、lazy decay、revision sync | 内心独白 / 事件触发 |
| 天级 | 习惯 streak / strength | 累加、阈值衰退 | 每日事件 |
| 周–月 | 记忆图边权重 | Hebbian 强化、Ebbinghaus 衰减 | 检索 / 做梦 |
| 永久 | 状态持久化 | JSON / SQLite / 索引写盘 | 心跳末尾 |

形式上，可以把系统状态写成五个可观测分量：

```text
system_state(t) = (
  snn_state,
  modulator_state,
  memory_state,
  thought_stream_state,
  chatter_state
)
```

Neo-MoFox 追求的连续性不是“每一层每一秒都改变”，而是：在没有外部输入的时间间隙中，至少有一个内部状态分量会随时间推进，并在后续表达、检索或持久化记录中留下可检查的变化。

## 4.5 心跳到表达的数据流

一次典型闭环可以被拆成九步：

1. **事件采集**：Life Engine 从事件流读取最近用户消息、工具调用、超时、梦境和内心独白。
2. **SNN 更新**：事件被编码为特征向量，驱动 SNN 快层更新。
3. **调质推进**：drive 投影为调质刺激，更新 curiosity、sociability、focus、contentment、energy。
4. **记忆检索与衰减**：记忆图执行检索、强化或衰减。
5. **ThoughtStream 推进**：潜意识创建、推进、休眠或重激活思考流。
6. **运行态快照**：Life Engine 汇总状态，形成可被 LifeChatter 读取的 transient context。
7. **LifeChatter 组装上下文**：主意识把人格、历史、未读消息、记忆、运行态快照和 ThoughtStream 合并为 LLM 输入。
8. **行动输出**：LifeChatter 决定回复、等待、停止、调用工具或记录内心独白。
9. **反馈回写**：输出与工具调用重新进入事件流，成为下一轮 Life Engine 心跳的输入。

这就是“感知-状态-决策-反馈”闭环在软件 Agent 中的具体形态。

## 4.6 部署形态

Neo-MoFox 当前仍以单进程 + 多协程形态运行。这样做不是为了追求分布式复杂性，而是为了让课程报告关注核心问题：连续性、状态同步和可观测性。

- LifeChatter 作为 `life_chatter` chatter 注册到框架中，负责面向用户的主意识运行。
- Life Engine 作为同一插件内的后台服务运行心跳、做梦、记忆和 ThoughtStream 管理。
- 状态同步依赖运行时注入队列、事件高水位、ThoughtStream revision 和 transient context，而非旧 DFC 桥接。
- 持久化集中在 `data/life_engine_workspace/`，包括上下文 JSON、记忆库、思考流索引和梦境日志。

## 4.7 与三大原则的对应

| 工程要素 | 主要服务的原则 |
|---|---|
| Life Engine 心跳 | 连续性 |
| LifeChatter + Life Engine 双意识异步运行 | 连续性 + 系统涌现 |
| ThoughtStream 注意力同步 | 系统涌现 + 自下而上学习 |
| SNN 软 STDP / Hebbian 边强化 / 习惯 streak | 自下而上学习 |
| 运行态快照与状态持久化 | 连续性 |
| 做梦巩固 | 长期自适应与记忆重组 |

## 4.8 小结

本章完成了从课程主题到当前工程架构的桥接：LifeChatter 使系统能够对外表达，Life Engine 使系统在不表达时仍持续运行，ThoughtStream 则把潜意识中持续在意的问题同步给主意识。下一章起，报告将依次展开 SNN、调质、记忆、睡眠、心跳和双意识同步机制。
