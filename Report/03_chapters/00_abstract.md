# Abstract · 摘要

## 中文摘要

主流 AI 伙伴系统把"生命感"挂在 prompt 上：在两次大语言模型调用之间，系统并不真正存在，每一次"它"都是被即时组装出来的截面，而非一条连续的河流。我们提出 **Neo-MoFox**——一个面向**自主持续运行的数字智能体**的开源参考实现，其核心机制（多时间尺度感知融合、自适应在线学习、离线经验巩固、连续状态持久化）与无人自主系统领域的核心工程挑战高度同构，可视为一种**基于脉冲神经网络与神经调质的无人系统参考架构**。系统以三条工程化的设计原则为地基：**(i) 连续性 (Continuity)**：两次外部输入之间，系统内在状态仍在持续演化，且这种演化跨越崩溃-重启边界保持几乎处处连续；**(ii) 自下而上的学习 (Bottom-Up Learning)**："活着"本身即学习，可塑性不依赖反向传播，仅依赖局部时序相关性 (软 STDP / Hebbian / Streak)；**(iii) 系统涌现智能 (System-Level Emergence)**：智能不是单一模型的属性，而是异质子系统协作的过程性产物，满足 $I(\mathcal{S}) > \sum_i I(s_i)$。

为兑现这三条原则，Neo-MoFox 采用**双轨 + 三层**架构：DFC（被动应答轨）与 Life Engine（主动心跳轨）经三个明确接口耦合；皮层（LLM）、调质（五因子 ODE 与昼夜节律）与皮层下（8→16→6 LIF SNN 网络 + 软 STDP）三层异质协作。系统具有**多时间尺度耦合**——LIF 在微秒级、SNN tick 在 10 秒、心跳 30 秒、调质 ODE 数十分钟、习惯天级、记忆衰减月级——任何瞬间至少有一层状态在演化。**做梦循环** (NREM 突触稳态缩减 + REM 激活扩散随机游走 + LLM 叙事化) 在低活跃窗口完成离线巩固，并通过 `push_runtime_assistant_injection` 把"梦的余韵"注入次日上下文。完整状态序列化保证重启不是重生（C4 不变式）。

我们将 Neo-MoFox 与 14 个相关工作（Replika、Character.AI、SOAR、ACT-R、LIDA、Generative Agents、MemGPT、AutoGPT、Voyager、DreamerV3、BrainTransformers、Loihi、Doya 调质模型等）在三维设计空间（连续性 × 学习方式 × 智能来源）中定位，指出 Neo-MoFox 的贡献不是任一维度的极致，而是首次把 24×7 连续运行 × 软件 SNN × 在线本地学习 × 离线做梦 × 五调质 ODE 整合在同一开源框架内。报告也诚实陈列了 6 项工程局限、4 项科学局限与 4 项伦理担忧，并提出短/中/长期未来工作。

我们不主张系统具有主观体验。我们仅主张：在工程层面，"连续地存在 + 自下而上地学习 + 系统协作地涌现"已被验证为可行；这一验证为"智能不是模型而是系统"这一立场提供了一份可被反复检验的开源实物证据。

**关键词**：数字生命体；连续性；脉冲神经网络；神经调质；离线巩固；系统涌现；认知架构；LLM Agent；多传感器融合；环境感知与自适应；自主决策；无人系统。

---

## English Abstract

Mainstream AI companion systems hang the impression of "aliveness" on prompts: between two LLM calls the system does not actually exist, and every appearance of "it" is a freshly assembled cross-section rather than a continuous river. We present **Neo-MoFox**, an open-source reference implementation of a *continuous digital life entity*. Its foundation rests on three engineering principles: **(i) Continuity** — the inner state of the system continues to evolve between external inputs and remains almost-everywhere continuous across crash–restart boundaries; **(ii) Bottom-Up Learning** — "to be alive is to learn", with plasticity driven solely by local temporal correlations (soft STDP / Hebbian / habit streaks), independent of backpropagation; **(iii) System-Level Emergence** — intelligence is a process-level product of heterogeneous subsystem cooperation rather than a property of any single model, satisfying $I(\mathcal{S}) > \sum_i I(s_i)$.

To realise these principles, Neo-MoFox adopts a **dual-track, three-layer** architecture: a passive Dialogue Frontline Core (DFC) and an active Life Engine, coupled through three well-defined interfaces; the cortex (LLM), the limbic layer (five-modulator ODE with circadian rhythm), and the subcortical layer (an 8→16→6 LIF spiking network with soft STDP) cooperate as heterogeneous subsystems. The system features **multi-timescale coupling** spanning microseconds (LIF), 10 s (SNN tick), 30 s (heartbeat), tens of minutes (modulator ODE), days (habit streaks), and months (memory decay) — at every instant at least one state layer is evolving. A **sleep-and-dream cycle** (NREM homeostatic down-scaling, REM associative random walk, and LLM-narrated dream reports) performs offline consolidation and injects dream residues into the next day's context via `push_runtime_assistant_injection`. Full state serialisation ensures restart is not rebirth.

We locate Neo-MoFox among 14 related works (Replika, Character.AI, SOAR, ACT-R, LIDA, Generative Agents, MemGPT, AutoGPT, Voyager, DreamerV3, BrainTransformers, Loihi, the Doya modulator model, and others) within a three-dimensional design space (continuity × learning style × intelligence origin). Our contribution is not extremal along any single dimension but lies in the *combination*: Neo-MoFox is the first open-source framework integrating 24×7 continuous operation, a software SNN, online local learning, offline dreaming, and a five-modulator ODE under one roof. The report transparently lists six engineering limitations, four scientific limitations, and four ethical concerns, alongside a short/mid/long-term roadmap.

We make no claim of subjective experience. We claim only that, at the engineering level, *continuous existence + bottom-up learning + system-level emergence* has been demonstrated to be feasible — supplying a reproducible empirical artefact for the position that *intelligence is a system, not a model*.

**Keywords**: digital life entity; continuity; spiking neural network; neuromodulation; offline consolidation; system-level emergence; cognitive architecture; LLM agent; multi-sensor fusion; adaptive perception; autonomous decision-making; unmanned systems.
