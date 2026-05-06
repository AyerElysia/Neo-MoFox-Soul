# Abstract · 摘要

## 中文摘要

本报告是《智能感知与无人系统》课程报告，基于本人正在维护的开源项目 **Neo-MoFox-Soul** 改写而成。项目地址：<https://github.com/AyerElysia/Neo-MoFox-Soul>。报告不把该项目包装成一篇完整学术论文，而是把它作为一个软件形态的自主 Agent 无人系统原型，讨论它如何在持续运行、状态感知、在线学习与自主决策之间形成闭环。

工程上，Neo-MoFox 建立在 `app / core / kernel` 三层框架之上：`app` 负责运行时生命周期与插件装配，`core` 负责组件模型、管理器、消息流、Prompt 与传输抽象，`kernel` 提供配置、日志、事件总线、任务调度、数据库、存储、向量库和 LLM 客户端。`plugins/life_engine` 作为关键插件挂载在这一框架上，注册 LifeChatter、LifeEngineService、工具、Router、记忆、做梦、SNN、神经调质和 ThoughtStream。

当前 Neo-MoFox 的核心运行范式是 **LifeChatter + Life Engine** 双意识异步运行：LifeChatter 负责面向用户的社交主意识，承担对话表达、工具调用、上下文组装和行动输出；Life Engine 作为潜意识系统，以心跳循环持续推进 SNN、神经调质、记忆图、做梦巩固和 ThoughtStream。两者不是两个互不相干的 Agent，而是同一主体在不同时间尺度上的两种运行相位。

这一设计与无人系统中的核心问题相似：系统不能只在传感器数据到达的一瞬间“存在”，还需要在通信盲区、低负载窗口和长期部署过程中保持状态连续、感知自适应和策略可演化。Neo-MoFox 通过 Life Engine 心跳、运行态快照、内心独白注入、ThoughtStream 注意力同步和状态持久化，使主意识能够读取潜意识中持续演化的状态，而潜意识也能在后台维护尚未表达的关注点、梦境残影和长期兴趣。

本文的核心结论是：在工程层面，“智能不是单一模型，而是一个持续运行的系统”。Neo-MoFox 还不能被称为成熟的无人系统，也不主张具有主观体验；但它提供了一个可检查的开源样例，展示了感知-状态-决策-反馈闭环如何在软件 Agent 中被具体实现。

**关键词**：智能感知；无人系统；自主 Agent；LifeChatter；Life Engine；双意识异步运行；ThoughtStream；在线学习；脉冲神经网络；神经调质；记忆巩固；开源课程项目。

---

## English Abstract

This report is prepared for the course *Intelligent Perception and Unmanned Systems*. It is based on my open-source project **Neo-MoFox-Soul**: <https://github.com/AyerElysia/Neo-MoFox-Soul>. The goal is not to present the system as a finished research paper, but to use it as a software prototype of an autonomous Agent-style unmanned system and examine how continuous operation, state perception, online learning, and autonomous decision-making can form a closed loop.

Engineering-wise, Neo-MoFox is built on an `app / core / kernel` framework. The app layer manages runtime lifecycle and plugin assembly; the core layer manages components, managers, message streams, prompts, and transport abstractions; the kernel layer provides configuration, logging, event bus, task scheduling, database, storage, vector database, and LLM client capabilities. The `plugins/life_engine` plugin is mounted on this framework and registers LifeChatter, LifeEngineService, tools, routers, memory, dream, SNN, neuromodulation, and ThoughtStream modules.

The current Neo-MoFox runtime is organized as a **LifeChatter + Life Engine** dual-consciousness asynchronous model. LifeChatter is the social conscious mind: it handles dialogue, tool use, context assembly, and outward action. Life Engine is the subconscious process: it continuously advances heartbeat cycles, SNN dynamics, neuromodulation, memory graphs, dream consolidation, and ThoughtStreams. These are not two unrelated Agents, but two operating phases of one subject across different time scales.

This design aligns with a central concern in unmanned systems: an autonomous system should not only “exist” at the instant of sensor input, but should preserve state continuity, adaptive perception, and long-term self-adjustment during communication gaps, idle windows, and extended deployment. Neo-MoFox uses heartbeat updates, runtime snapshots, inner-monologue injection, ThoughtStream synchronization, and persistent state recovery to let the conscious dialogue layer read the evolving subconscious state.

The main conclusion is that intelligence, at the engineering level, is not a single model but a continuously operating system. Neo-MoFox is not yet a mature unmanned system and makes no claim of subjective experience, but it offers an inspectable open-source artifact for studying a perception-state-decision-feedback loop in a software Agent.

**Keywords**: intelligent perception; unmanned systems; autonomous Agent; LifeChatter; Life Engine; dual-consciousness asynchronous operation; ThoughtStream; online learning; spiking neural network; neuromodulation; memory consolidation; open-source course project.
