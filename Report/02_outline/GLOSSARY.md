# Neo-MoFox 报告 · 术语表（Glossary）

> 全部术语在第一次出现时给出"中文（English）"形式；本表用于附录 A 与作者间一致性参考。

## A. 哲学层术语

| 中文 | English | 定义 | 来源 |
|------|---------|------|------|
| 连续性 | Continuity | 即使在两次 LLM 调用之间，系统仍保持正在演化的内在状态 | Abstract/连续存在.md |
| 自下而上的学习 | Bottom-Up Learning | 不依赖外部梯度，而是基于局部时序相关性的在线学习 | 用户口述 + Abstract/智能不是模型.md |
| 系统涌现智能 | System-Level Emergence | 智能不是单一模型的属性，而是异质子系统协作的属性 | Abstract/智能不是模型.md |
| 离散存在 | Discrete Existence | 仅在被调用瞬间存在、调用之间空白的传统范式 | Abstract/连续存在.md |
| 数字生命体 | Digital Life Entity | 具备连续性、自学习与系统涌现智能的 AI 系统 | README.md |
| 皮层下系统 | Subcortical System | 类比生物大脑皮层下脑区的低层计算系统（SNN + 调质） | Abstract/SNN_与系统智能.md |

## B. 架构层术语

| 中文 | English | 定义 |
|------|---------|------|
| 中枢 / 生命中枢 | Nucleus / Life Engine | `plugins/life_engine` 插件，负责心跳、SNN/调质/做梦/记忆的统一调度 |
| 对话流控制器 | DFC (Dialogue Flow Controller) | `default_chatter` 插件，负责被动应答 |
| 双轨架构 | Dual-Track Architecture | DFC（被动）+ Life Engine（主动）并行运行 |
| 心跳 | Heartbeat | Life Engine 每 30 秒触发的内省+决策循环 |
| 事件流 | Event Stream | `LifeEngineEvent` 的全局有序序列 |
| 唤醒上下文 | Wake Context | 注入到心跳 LLM 的事件历史 + 状态摘要 |

## C. SNN 层术语

| 中文 | English | 定义 |
|------|---------|------|
| 脉冲神经网络 | SNN (Spiking Neural Network) | 以离散脉冲传递信息的神经网络 |
| 漏电积分发放神经元 | LIF (Leaky Integrate-and-Fire) | 经典脉冲神经元模型 |
| 脉冲时序依赖可塑性 | STDP (Spike-Timing-Dependent Plasticity) | 基于脉冲时序差的局部学习规则 |
| 软 STDP | Soft STDP | 用 sigmoid(膜电位) 替代二值发放参与学习的工程改造 |
| 自稳态 | Homeostasis | 通过动态阈值使发放率维持在目标水平的机制 |
| 衰减步 | Decay-Only Step | 仅膜电位泄漏、不学习的低开销 tick |
| 驱动 | Drive | SNN 输出的 6 维生命冲动信号（arousal/valence/social/task/exploration/rest） |
| 动态增益 | Dynamic Gain | 根据输入分布自适应调整的输入缩放因子 |

## D. 调质层术语

| 中文 | English | 定义 |
|------|---------|------|
| 调质（神经调质） | Neuromodulation | 影响神经元/网络整体激活水平的化学/动力学过程 |
| 调质因子 | Modulator | 项目中实现的浓度变量（curiosity/sociability/focus/contentment/energy） |
| 时间常数 | Time Constant (τ) | ODE 中决定回归基线速度的参数 |
| 基线 | Baseline | 调质因子的稳态目标值 |
| 边际效应递减 | Headroom | 公式 $h(M) = 1 - 2|M-0.5|$；浓度越极端越难再变 |
| 昼夜节律 | Circadian Rhythm | 24 小时周期的内在时钟 |
| 习惯 | Habit | 由 streak 与 strength 表征的天级行为稳定化 |
| 习惯连胜 | Streak | 习惯连续触发的天数 |

## E. 记忆层术语

| 中文 | English | 定义 |
|------|---------|------|
| 记忆节点 | MemoryNode | 知识图中的实体/事件/概念 |
| 记忆边 | MemoryEdge | 节点之间的关联，6 种类型 |
| Ebbinghaus 衰减 | Ebbinghaus Decay | 记忆强度按指数衰减，$\lambda \approx 0.05$ |
| Hebbian 强化 | Hebbian Reinforcement | "一起激活的神经元/边一起强化" |
| 倒数排名融合 | RRF (Reciprocal Rank Fusion) | 多路检索结果的融合算法 |
| 激活扩散 | Activation Spreading | 沿边权重传播激活的检索增强方法 |

## F. 做梦层术语

| 中文 | English | 定义 |
|------|---------|------|
| NREM | NREM Sleep | 非快速眼动睡眠，对应突触稳态缩减阶段 |
| REM | REM Sleep | 快速眼动睡眠，对应关联整合阶段 |
| 突触稳态 | SHY (Synaptic Homeostasis Hypothesis) | Tononi & Cirelli 2014 假说 |
| 种子 | Seed | 做梦的起始记忆/事件 |
| 残影 | Residue | 做梦后留下的可被巩固的产物 |
| 场景 | Scene | 由场景生成器产出的梦境片段 |

## G. 工程层术语

| 中文 | English | 定义 |
|------|---------|------|
| 组件 | Component | 插件系统的可发现单元（Action/Tool/Chatter 等 12 种） |
| 组件签名 | Component Signature | `plugin:type:name` 格式 |
| 唤醒 DFC | nucleus_wake_dfc | 中枢主动让 DFC 在某会话发起对话 |
| 咨询中枢 | consult_nucleus | DFC 同步拉取中枢状态摘要 |
| 告知 DFC | nucleus_tell_dfc | 中枢异步注入信息给 DFC |
| 运行时注入 | Runtime Injection | 把外部生成的内容写入 DFC 下一轮 prompt |
| 状态序列化 | State Serialization | 完整 SNN/调质/记忆/事件历史的 JSON 持久化 |
