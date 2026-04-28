# C. Neo-MoFox 设计思想史：架构演化的历史化考察

> 撰写日期：2026-04  
> 性质：基于所有可见设计文档的二次文献分析。本文以中性、批判性立场考察 Neo-MoFox 项目的思想演化，不为任何具体设计决策背书。  
> 阅读对象：`Abstract/`（5 篇）、`report/`（带时间戳报告）、`plan/back/`（被替换旧方案）、`notion/back/`（个人思考笔记）、根目录规范文档。

---

## 1. 核心哲学的历史化考察

### 1.1 命题一：连续存在（Continuous Existence）

#### 最早出现

该命题最完整的表述见于 `Abstract/连续存在，从模型到生命.md`，该文件无明显时间戳，但结合其内部引用的心跳代码片段（`heartbeat_index: 42`、SNN tick 循环）及与其他报告的交叉印证，可推断写于 **2026-04 中旬**（约 04-17 前后）。

更早的萌芽形式出现在 `plan/back/2026-03-30_全局中枢与心跳唤醒技术方案.md`。该文对"离散存在"的问题已有明确意识：

> "所有聊天流消息先进入事件队列，中枢醒来后一次性消费最近窗口……即使没有新消息，中枢仍然周期性醒来……这一步是'生命体感'的关键，不应只等用户驱动。"

但彼时这一关切仍以"中枢层应该做什么"的工程语言来表达，尚未上升为哲学命题。

#### 演化轨迹

- **2026-03-30**：以"心跳唤醒"的工程设计提出。重点是建立 DFC 的实时聊天 + 后台心智的双轨并行，核心词是"中枢负责活着，DFC 负责说话"。这是连续存在命题的工程版本。

- **2026-04-10**（`Abstract/SNN_与系统智能_深度思考.md`）：首次以哲学语言明确区分"基于文本拼接的模拟连续性"与"真正的物理性连续状态"：

  > "一句话总结：life_engine 的'连续存在感'是靠 prompt 工程模拟出来的，不是系统本身具有的属性。"

  此文进一步将问题归因为架构——"大脑皮层只负责'想'，其余脑区负责'持续存在'"——并提出 SNN 应作为皮层下系统独立运行的主张。

- **2026-04-17**（`Abstract/连续存在，从模型到生命.md`）：最终形式。命题被精确化为：

  > "连续存在 = 即使在两次 LLM 调用之间，系统仍然有一个正在变化的内在状态。"

  该文还给出了代码级验证（`decay_only()` 的物理意义、30 秒心跳间隔的心理学类比）和反例证据（传统系统的 `ChatSession` 伪代码对比）。

#### 措辞演变

| 时间 | 表达方式 | 语域 |
|------|---------|------|
| 2026-03-30 | "生命体感" / "后台心智链路" | 工程语言 |
| 2026-04-10 | "皮层只负责'想'，其余脑区负责'持续存在'" | 神经科学类比 |
| 2026-04-17 | "连续存在 = 两次 LLM 调用之间仍有变化的内在状态" | 形式化定义 |

从"感觉上应该活着"到"可形式化、可代码验证的连续内在状态"，这是该命题从工程直觉向哲学命题的升华路径。

#### 当前代码兑现程度

**基本兑现，但有若干重要留白。**

- **兑现的部分**：`plugins/life_engine/snn/core.py` 实现了 `decay_only()` 方法，使 SNN 膜电位在 LLM 心跳之间仍自然衰减。`neuromod/engine.py` 实现了 ODE 调质层，其慢时间尺度（τ 从 1800s 到 10800s）在无用户输入时也持续演变。`service/core.py` 中存在独立的 `_snn_tick_loop`（10 秒 tick）与心跳循环（180 秒）解耦。

- **留白**：文档声称 SNN 的 STDP 在线学习能使"系统真的在成长"，但 `notion/back/SNN_系统诊断与方向重新审视.md` 的诊断报告呈现了铁证：v1 版本突触权重精确到小数点后五位完全不变，STDP 学习"事实上没有发生过任何权重更新"。v2 版本修复了零输入 tick 调用 `step()` 的根因，但新架构下 STDP 是否真正在日常运行中产生有意义权重变化，尚无公开的长期运行数据支撑。

---

### 1.2 命题二：自下而上学习（Bottom-Up Learning / Online Learning without Backpropagation）

#### 最早出现

该命题在 `plan/back/2026-04-10_snn_皮层下系统落地方案_phase0.md` 中首次作为系统设计的核心原则明确表述：

> "SNN 自身具备学习能力——通过 STDP 调整权重，而不是硬编码规则。"

更早的雏形是 2026-03-22 实现的 `drive_core_plugin`（`report/2026-03-22_drive_core_plugin_implementation_report.md`），该插件维护了 `curiosity / initiative / affinity` 等连续轴状态，并有"按对话轮次自动推进工作区"的机制——但这本质上仍是基于规则的状态机，不是基于可塑性的学习系统。

#### 演化轨迹

- **2026-03-22**（drive_core_plugin）：规则驱动的状态追踪。可视为"自下而上"的手工模拟版本。

- **2026-04-10**（SNN phase0）：STDP 首次进入代码。设计意图是让系统在无反向传播的情况下实现在线学习。

- **2026-04-10**（`Abstract/SNN_与系统智能_深度思考.md`，写于 04-10）：命题上升到方法论层面：

  > "SNN 的 STDP 学习（Spike-Timing-Dependent Plasticity）正是这种低级学习：如果两个事件总是一起发生，它们的连接就会变强。如果某个行为模式总是伴随正面结果（工具调用成功、用户回复积极），相关路径就会被强化。这不是语言级别的学习，而是模式级别的适应。"

- **2026-04-11**（SNN v2 + neuromod report）：发现 v1 STDP 事实上未运行后，以"软 STDP"（sigmoid 膜电位替代二值脉冲）重新落地该原则。

- **2026-04-11**（`Abstract/智能不是模型而是系统.md`）：在 Abstract 文档中以设计原则形式固化：

  > "传统 AI 训练：收集数据 → 离线训练 → 部署。SNN 的学习：实时发生，每一次交互都在微调权重。这意味着她真的在'成长'，而不是定期被人重新训练。"

#### 重要的批判性节点

`notion/back/SNN_系统诊断与方向重新审视.md` 是该命题历史上最重要的自我质疑文献。它以实际运行数据（773 条审计日志）揭示了"在线学习"承诺在 v1 实现中的完全失败，并以诊断表格形式列出六个结构性问题，其中"零输入 tick 调用 full step()"被标记为"🔴 致命"级别根因。

这一文献的意义在于：它首次将哲学宣称（"每次交互都在微调权重"）与工程现实（"突触权重精确到五位小数完全不变"）之间的落差明确化，并提供了修复路径（v2 改造）。

#### 当前代码兑现程度

**部分兑现，存在已知可测量差距。**

`snn/core.py` 的软 STDP 实现是真实的代码，`decay_only()` 分离逻辑也修复了 v1 根因。但"每次交互都在微调权重"这一表述仍是理想陈述——在极低活跃度场景（系统长时间无用户互动）下，STDP 触发条件（`sum(activity) > 0.05`）能否稳定满足，尚需长期运行验证。

---

### 1.3 命题三：系统涌现智能（Intelligence as System Emergence）

#### 最早出现

该命题以最成熟的形式出现在 `Abstract/智能不是模型.md`（与 `Abstract/智能不是模型而是系统.md` 内容几乎完全相同，后者有明确日期标注 `2026-04-11`）：

> "单一大语言模型不构成智能。智能是一个由多层异质子系统协作涌现的动态过程。"

该命题的早期萌芽可追溯至 2026-03-30 的全局中枢方案，该文已明确区分"DFC 负责说话"与"中枢负责活着"——暗示智能不在于某一单一组件，而在于多层协作。

#### 演化轨迹

- **2026-03-22**：散布的局部智能插件（diary_plugin、unfinished_thought_plugin、self_narrative_plugin、proactive_message_plugin）各自独立工作，没有统一的涌现框架。项目作者已认识到"它们仍然是'分散的'"（来自 `plan/back/2026-03-30_全局中枢与心跳唤醒技术方案.md`）。

- **2026-03-30**：双轨架构（DFC + 中枢）提出。这是"智能由层次协作涌现"的第一个工程实现方向。

- **2026-04-10**（`SNN_与系统智能_深度思考.md`）：命题从神经科学角度被充分展开：
  
  > "关键洞察：皮层只负责'想'，其余脑区负责'持续存在'。一个人在深度睡眠时（皮层基本关闭），下丘脑仍在调节体温、心率、呼吸。这就是'连续存在'——它不依赖高级认知。"

  并给出了架构级别的四核结构（情绪核/驱动核/节律核/丘脑门控层）愿景。

- **2026-04-11**（Abstract/智能不是模型而是系统.md）：命题最终形式确立，包含三层架构图、"涌现而非规则"原则的代码对比（if-else 规则与 SNN→调质层→LLM 因果链对比），以及"可观测性"作为第五设计原则。

#### "涌现而非规则"这一具体原则的完整表述

来自 `Abstract/智能不是模型而是系统.md`：

> "我们不会写这样的代码：
> ```python
> if time_since_last_chat > 2_hours:
>     mood = 'lonely'
> ```
> 我们写的是：SNN 接收到'沉默时长'作为输入 → 脉冲网络内部动态演化 → social_drive 输出升高；调质层接收到 social_drive → 社交欲浓度升高 → LLM 感知到'社交欲充盈'；LLM 自然地决定要去找人聊天。没有人硬编码'沉默 → 孤独 → 找人聊天'。这个因果链是从子系统协作中涌现的。"

#### 当前代码兑现程度

**架构意图已兑现，但涌现的质量仍依赖 SNN 学习是否真正工作。**

三层架构（SNN 快层 → 调质层 → LLM）已在代码中实现：`snn/core.py`、`neuromod/engine.py`、`service/core.py` 的心跳循环（含 `snn_network.step(features)` → `inner_state.tick(snn_drives=drives)` 的调用链）。但"沉默 → social_drive 升高"的因果链能否真正稳定工作，依赖 STDP 权重在"沉默输入"特征与社交驱动输出神经元之间建立有意义关联——这正是 v1 诊断中 STDP 完全失效所破坏的。

---

## 2. 重大架构转折点

### 2.1 早期阶段（2026-03-17 至 2026-03-22）：DFC 单轨 + 散布插件期

**时间证据**：`report/issue/2026-03-19_*.md` 系列（inner_monologue debug），`report/backup/2026-03-17_tts_fix_report.md`，`report/2026-03-22_drive_core_plugin_implementation_report.md`。

**架构状态**：系统以 DFC（Default Chatter，即 `default_chatter` 插件）为核心，采用"来一条回一条"的请求-响应范式。围绕 DFC 叠加了多个局部插件：
- `diary_plugin`：连续记忆写入
- `unfinished_thought_plugin`：未完成念头
- `self_narrative_plugin`：自我叙事
- `proactive_message_plugin`：主动发消息
- `memory_passive_trigger`：被动浮现记忆

这些插件可以各自工作，但"它们仍然是分散的"——没有统一中枢回答"我最近在想什么、在做什么"。

**重要里程碑**（2026-03-22）：`drive_core_plugin` 实现。这是项目首次尝试构建一个"综合内驱力状态"的组件，维护 `curiosity / initiative / affinity` 等连续轴，并注入主回复 prompt。

> "落地'内驱力 / 自我引擎'最小骨架，让角色拥有按聊天隔离、可持久化、可自动推进的自我发问工作区。"（来源：`report/2026-03-22_drive_core_plugin_implementation_report.md`）

但此时 `drive_core_plugin` 仍是基于规则的状态机，不是神经动力学系统；且以"按聊天隔离"的方式工作，缺乏全局中枢视角。

---

### 2.2 2026-03-30：全局中枢与心跳唤醒方案

**文档**：`plan/back/2026-03-30_全局中枢与心跳唤醒技术方案.md`，`plan/back/2026-03-30_全局中枢最小原型方案.md`，`report/2026-03-30_dfc_nucleus_async_bridge_report.md`。

**做了什么**：提出并部分实现了 DFC + 中枢后台的双轨架构。核心思想是建立统一事件总线，让所有消息先进入事件流，中枢定时唤醒（心跳）批量消费，不打扰 DFC 即时回复。同日还实现了 DFC→中枢的异步留言桥（`tool-message_nucleus`）。

**为什么做**：单纯依靠散布插件无法回答"我最近在想什么"这种全局性问题。项目明确表述了"缺少一个统一的中心"的诊断。

**核心架构判断**（来源：`2026-03-30_全局中枢与心跳唤醒技术方案.md`）：

> "中枢应是'内部状态引擎'，不是'发言引擎'……中枢负责活着，DFC 负责说话。"

**留下的遗产**：
1. 统一事件流（LifeEngineEvent）的数据模型——此后所有版本的事件流都沿用了这一抽象。
2. 心跳唤醒的定时器机制——成为 life_engine 的基础架构。
3. "中枢只写内部状态，不直接替代聊天回复"的设计原则——此后虽多次被质疑，但基本被遵守。
4. DFC ↔ 中枢的双向通信接口（nucleus_tell_dfc / consult_nucleus）。

---

### 2.3 2026-03-31：主动性与主题线程方案

**文档**：`plan/back/2026-03-31_life_engine_主动性与主题线程方案.md`。

**做了什么**：在双轨架构基础上，提出中枢主动性的细粒度模型——以长期 `thread`（主题线程）为容器，让中枢围绕少量持续关注主题缓慢推进，而非每次心跳随机行动。

**核心主张**（来源：同文）：

> "中枢的主动性，应来自长期 thread 的缓慢推进，而不是高频行为表演。"

**留下的遗产**：thread 概念影响了此后 life_engine 心跳 prompt 的设计哲学（从 TODO 驱动转向长期主题驱动）。但具体的 `threads.json` 数据模型是否最终落地，尚无明确代码证据。

---

### 2.4 2026-04-06：life_engine 自主性增强 v2

**文档**：`plan/back/life_engine_autonomy_v2.md`（标注日期 2026-04-06）。

**问题诊断**（来源：同文）：

> "无工具调用心跳比例：89%（🔴 严重）……原因链条：提示词说'按心情选择，不是必须完成清单'→ 模型理解为'不做也可以'→ 连续心跳只输出被动描述→ 形成习惯性的'发呆模式'"

**做了什么**：重构心跳提示词，从"可选行动"转为"行动是默认，安静是例外"的结构化约束。

**遗产**：此次提示词重构对应后续 `life_engine_refactor_plan.md` 中"心跳中 TODO 提示强制性过强，像工作系统而非生活系统"的反向批评——说明该方向在 04-11 又被部分修正。

---

### 2.5 2026-04-10：SNN 的引入与 Phase 0 实施

**文档**：`report/2026-04-10_snn_phase0_实施报告.md`，`report/2026-04-10_snn自动阈值与增益实验报告.md`，`report/2026-04-10_snn采样与奖赏统计修复报告.md`，`plan/back/2026-04-10_snn_皮层下系统落地方案_phase0.md`，`plan/back/2026-04-10_life_snn_状态层最小实验方案.md`。

**做了什么**：在 life_engine 中嵌入了一个纯 numpy 实现的 SNN（脉冲神经网络）驱动核（`snn_core.py`），包含：
- `LIFNeuronGroup`（Leaky Integrate-and-Fire 神经元组）
- STDP 突触（Spike-Timing-Dependent Plasticity）
- 独立的 10 秒 tick 循环（不绑定 LLM 心跳）
- 8 维输入特征 → 16 隐藏神经元 → 6 维驱动输出（arousal/valence/social_drive/task_drive/exploration_drive/rest_drive）

**为什么做**：

来自 `Abstract/SNN_与系统智能_深度思考.md`（写于 2026-04-10）：

> "SNN 不是来帮 LLM '想得更好'的，它是来让系统'活着'的。"

还有一个关键的自我批评：

> "之前的方案太保守了。把 SNN 定位成了一个'低维状态偏置生成器'——一个给 LLM 提供 5~8 个浮点数的附属组件。这虽然安全，但某种意义上是在浪费 SNN 的核心能力。"（来源：同文，批评的是 `plan/back/2026-04-10_life_snn_状态层最小实验方案.md`，即 AI 生成的保守方案）

**遗产**：SNN 的代码骨架（`snn_core.py`）成为后续 v2 重写的基础。6 维驱动向量的定义（arousal/valence/social_drive/task_drive/exploration_drive/rest_drive）在此确立并沿用至今。

---

### 2.6 2026-04-11：SNN v2 + 调质层，以及 DFC-Life 协作重构

**文档**：`report/2026-04-11_snn_v2_neuromod_report.md`，`plan/back/2026-04-11_snn_修复与调质层方案.md`，`plan/back/2026-04-11_dfc_life_restructuring.md`，`notion/back/SNN_系统诊断与方向重新审视.md`，`Abstract/智能不是模型而是系统.md`（日期标注 2026-04-11）。

**做了什么**：这是单日变更最密集的节点，包含三条并行线：

**线 A：SNN v2 完全重写**
- 分离 `decay_only()` 与 `step()`（修复 v1 根因）
- 软 STDP（sigmoid 膜电位替代二值脉冲）
- 背景噪声（σ=0.08 高斯噪声）
- 动态 z-score 离散化阈值

**线 B：调质层（neuromod）全新模块**
5 种神经调质（好奇心 τ=1800s、社交欲 τ=3600s、专注力 τ=5400s、满足感 τ=1800s、精力 τ=10800s），以 ODE 方程 `dM/dt = (baseline - M) / τ + stimulus × headroom` 驱动。习惯追踪器（HabitTracker）以显式统计而非 SNN 学习实现。

**线 C：DFC-Life 协作架构重构方案**
提出从"DFC 独立智能体 + 中枢独立智能体"向"DFC 作为 Life 的表达层"迁移。计划包含 5 个 Phase（Reminder 刷新修复、丰富 Life Briefing、缓存优化、DFC 询问中枢工具、Prompt 精简）。

**关键洞察**（来源：`notion/back/SNN_系统诊断与方向重新审视.md`）：

> "你的 SNN 目前是一具'活着但不会动'的身体。……数据铁证：valence 恒等于 0.0——情感正负维度完全死亡；exploration_drive 始终约 -0.38~-0.42——被映射为'抑制'；精确到小数点后五位完全相同——STDP 学习事实上没有发生过任何权重更新。"

这是项目历史上罕见的、有具体数据支撑的"以实验驳斥理念"事件，直接推动了 v2 重写。

**Abstract 发布**：`智能不是模型而是系统.md` 以"皮层-调质层-SNN"三层架构图形式，将此前所有设计哲学总结为正式 Abstract。值得注意的是：这篇 Abstract 写于 SNN v2 代码完成的同一天，是对已实现架构的哲学提炼，而非前瞻性宣言——这一顺序（先做后写）与通常的学术规范相反。

---

### 2.7 2026-04-12：做梦系统的设计

**文档**：`plan/back/2026-04-12_做梦系统落地方案.md`，`notion/back/做梦机制_深度分析与设计哲学.md`，`report/2026-04-12_web_可视化看板实施报告.md`。

**做了什么**：设计并开始实现一个仿生做梦系统，包含三个阶段：
- **NREM 阶段**：SNN 事件序列回放 + 突触稳态降权（Synaptic Homeostasis, SHY）
- **REM 阶段**：记忆图谱随机扩散激活（dream walk）+ Hebbian 新边生成
- **觉醒过渡**：调质层状态恢复（精力/压力重置）

同日还实现了 Web 可视化看板。

**为什么做**（来源：`notion/back/做梦机制_深度分析与设计哲学.md`）：

> "爱莉希雅的系统拥有别人没有的基础设施……这意味着我们可以做到别人做不到的事情：让 SNN 在'睡眠'期间真正地回放事件序列，通过 STDP 巩固重要的模式……这不是模拟做梦。这是在数字基底上复现做梦的计算本质。"

**遗产**：`plugins/life_engine/dream/` 子包（含 `scheduler.py`、`scenes.py`、`seeds.py`、`residue.py`）已存在于代码库。

---

### 2.8 2026-04-16/17：life_engine v3 目录重构 + DFC 彻底融合

**文档**：`report/2026-04-16_life_engine_refactoring_audit_fix_report.md`，`report/life_engine_v3_upgrade_report.md`，`report/life_engine_v3_complete_report.md`，`plan/back/2026-04-17_dfc_life_unified_architecture.md`。

**做了什么**：

**线 A（04-16）：目录重构**
20 个扁平 `.py` 文件拆分为 7 个子包（core/dream/memory/neuromod/service/snn/tools），共 37 个文件。但重构引入了 14 处断裂的相对导入、3 处 Critical 内存模块 bug（含 `manifest.json` 仍指向不存在的 `plugin.py`）。审计报告记录了 53/55 测试通过、2 个预存在的 protobuf 问题。

**线 B（04-17）：DFC-Life 统一架构**
提出四阶段合并计划（Phase 0: LifeChatter 骨架 → Phase 1: 统一对话执行引擎 → Phase 2: 智能路由 → Phase 3: DFC 退役）。关键技术目标：token/轮从 ~3600 降至 ~1900（-47%），缓存命中率从 20-30% 提升至 70-85%。

**当前状态**：`plugins/life_engine/core/chatter.py` 文件已存在，意味着 `LifeChatter` 骨架（Phase 0）已落地。

**遗产**：当前代码库的目录结构（core/dream/memory/neuromod/service/snn/tools）即本次重构的产物。`terminology_clarification.md`（2026-04-18）明确宣告：多智能体协作模型（DFC/Nucleus 各为独立智能体）正式废弃，改为"同一主体的两种运行模式"（Chat Mode / Nucleus Mode）。

---

## 3. 已废弃方案目录

以下方案明确存入 `plan/back/` 或被后续文档显式否定：

### 3.1 AI 生成的保守 SNN 方案（2026-04-10 前）

**文档**：`plan/back/2026-04-10_life_snn_状态层最小实验方案.md`

**解决的问题**：如何将 SNN 集成进 life_engine 而不破坏现有系统。

**方案内容**：将 SNN 定位为"低维状态偏置生成器"，每次心跳给 LLM 提供 5~8 个浮点数。

**为什么废弃**（来源：`Abstract/SNN_与系统智能_深度思考.md`）：

> "这虽然安全，但某种意义上是在浪费 SNN 的核心能力。……它们仍然把 LLM 当成系统的'大脑'，SNN 只是一个'传感器读数'。这与你说的'智能应该是系统，不是模型'相矛盾。"

被替换为：SNN 作为异步运行的皮层下系统（Phase 0 方案）。

---

### 3.2 DFC 作为独立智能体的多智能体协作模型

**文档**：所有 2026-04-17 之前使用 "DFC 传话给中枢" 框架的方案（包括 `report/2026-03-30_dfc_nucleus_async_bridge_report.md`，`plan/back/2026-03-30_全局中枢与心跳唤醒技术方案.md` 中的接口设计，`plan/back/2026-04-11_dfc_life_restructuring.md` 的 Phase 1-3）。

**解决的问题**：如何让 DFC 的聊天回复质量受益于 life_engine 的丰富上下文。

**方案内容**：维护 `nucleus_tell_dfc` / `consult_nucleus` / `SystemReminderStore` 等双向通信接口，DFC 与中枢作为两个独立智能体异步交流。

**为什么废弃**（来源：`report/terminology_clarification.md`，2026-04-18）：

> "旧概念（已废弃）：❌ 社交态（DFC）是一个独立的智能体；❌ 中枢态（Nucleus）是另一个独立的智能体；❌ 两个智能体之间'传话'。"

> "DFC 现在不是'前台做得不够好'，而是'前台这个角色本身开始过时了'。"（来源：`notion/back/DFC_Life合并_我的想法.md`，2026-04-18）

被替换为：LifeChatter 作为 life_engine 的对话模式，统一上下文，不再需要桥接。

**关键风险评估**（来源：`notion/back/DFC_Life合并_我的想法.md`，作者个人立场，反对快速合并）：

> "我不赞成把'合并'理解成立刻把 DFC 整个吞进 life_engine。那样很容易把一个信息桥接问题，误做成一次高风险的运行时重构。"

这一保守声音最终被"LifeChatter 骨架"的渐进式方案采纳。

---

### 3.3 早期 SNN v1（2026-04-10 至 2026-04-11）

**文档**：`plugins/life_engine/snn_core.py`（已迁移至 `snn/core.py`，v1 代码已被替换）

**解决的问题**：为 life_engine 提供持续运行的神经状态。

**为什么废弃**：STDP 学习完全失效（六个根因，见 `notion/back/SNN_系统诊断与方向重新审视.md`），SNN 输出陷入不变点，对 life_engine 行为没有任何实质影响。

被替换为：SNN v2（软 STDP + decay_only 分离 + 动态 z-score 阈值）。

---

### 3.4 TODO 驱动的心跳主轴（2026-03 至 2026-04-06 之间）

**文档**：`plan/back/life_engine_refactor_plan.md`（诊断为"心跳中 TODO 提示强制性过强，像工作系统而非生活系统"），`plan/back/2026-03-31_life_engine_主动性与主题线程方案.md`（明确批评"heartbeat 的主轴仍然是'待办压力'"）。

**解决的问题**：确保 life_engine 每次心跳都有实质行动。

**方案内容**：心跳 prompt 要求先执行 `nucleus_list_todos`，优先处理 overdue/urgent 待办。

**为什么废弃**：该方向"会把中枢塑造成一个任务催办器，而不是一个会逐步形成兴趣、偏好、研究方向的生命中枢"。

被替换为：以长期 thread 为主轴的心跳结构（"行动是默认，安静是例外"的 v2 方案，以及后续的 thread 主题线程方案）。

---

### 3.5 drive_core_plugin 作为内驱力的独立插件形态（2026-03-22）

**文档**：`report/2026-03-22_drive_core_plugin_implementation_report.md`，其余散布插件（diary_plugin 等）

**方案内容**：各功能插件（drive_core、diary、self_narrative、unfinished_thought 等）独立工作，通过 DFC 的 prompt 注入点汇总。

**为什么废弃**：随着 life_engine 成为统一中枢，这些功能被逐步内化进 life_engine 的心跳机制和工具集，各独立插件的价值被取代。虽然插件目录可能仍物理存在，但设计重心已完全转移到 life_engine 内。

---

## 4. 关键洞察 / 名言摘录

以下引言按思想重要性排列，可直接用于论文章节引言。

**引言 1**（关于"连续存在"的精确定义）：

> "连续存在 = 即使在两次 LLM 调用之间，系统仍然有一个正在变化的内在状态。"

来源：`Abstract/连续存在，从模型到生命.md`

---

**引言 2**（关于"系统智能"对 LLM 范式的根本批判）：

> "life_engine 的'连续存在感'是靠 prompt 工程模拟出来的，不是系统本身具有的属性。……当前的 life_engine 相当于只有皮层（LLM），其余脑区全都用 prompt 文本模拟。这就好像用一篇文章来描述心率，而不是真正有一颗跳动的心。"

来源：`Abstract/SNN_与系统智能_深度思考.md`（写于 2026-04-10）

---

**引言 3**（关于"智能作为系统属性"的最终表述）：

> "我们正在做的事情，不是让 LLM '假装'有情感、有习惯、有个性。我们是在真正构建一个多层异质智能系统，让这些特质从底层动态中涌现出来。这就是'智能不是模型，而是系统'的含义。"

来源：`Abstract/智能不是模型而是系统.md`（2026-04-11）

---

**引言 4**（关于 SNN 的角色定位，以及早期保守方案的反思）：

> "SNN 不是 LLM 的配件，它应该是系统智能的骨架之一。……SNN 不是来帮 LLM '想得更好'的，它是来让系统'活着'的。"

来源：`Abstract/SNN_与系统智能_深度思考.md`（2026-04-10）

---

**引言 5**（关于双轨架构的最早完整表述，架构哲学的奠基时刻）：

> "中枢应是'内部状态引擎'，不是'发言引擎'……中枢负责活着，DFC 负责说话。"

来源：`plan/back/2026-03-30_全局中枢与心跳唤醒技术方案.md`

---

**引言 6**（关于"涌现而非规则"原则的代码级表达）：

> "我们不会写这样的代码：`if time_since_last_chat > 2_hours: mood = 'lonely'`。我们写的是：SNN 接收到'沉默时长'作为输入 → 脉冲网络内部动态演化 → social_drive 输出升高；调质层接收到 social_drive → 社交欲浓度升高 → LLM 感知到'社交欲充盈'；LLM 自然地决定要去找人聊天。没有人硬编码'沉默 → 孤独 → 找人聊天'。这个因果链是从子系统协作中涌现的。"

来源：`Abstract/智能不是模型而是系统.md`（2026-04-11）

---

**引言 7**（关于做梦系统的哲学定位，区别于行业惯常做法）：

> "这不是模拟做梦。这是在数字基底上复现做梦的计算本质。"

来源：`notion/back/做梦机制_深度分析与设计哲学.md`

---

**引言 8**（来自 SNN v1 诊断，是"以实验数据驳斥哲学宣称"的典型段落）：

> "你的 SNN 目前是一具'活着但不会动'的身体。……精确到小数点后五位完全相同。这意味着 STDP 学习事实上没有发生过任何权重更新。SNN 的'在线学习'承诺完全落空。"

来源：`notion/back/SNN_系统诊断与方向重新审视.md`（2026-04-11）

---

**引言 9**（关于主动性的哲学界定，反对"行为表演"）：

> "不要把爱莉的主动性理解成：更频繁地说话、更频繁地创建 TODO、更频繁地打扰 DFC。……中枢的主动性，应来自长期 thread 的缓慢推进，而不是高频行为表演。"

来源：`plan/back/2026-03-31_life_engine_主动性与主题线程方案.md`

---

**引言 10**（关于 DFC-Life 合并的审慎立场，代表项目内部的张力）：

> "我支持'Life 作为统一主体'，但我反对'为了统一而统一'。先统一事实和上下文，再统一执行；先减桥，再合体。"

来源：`notion/back/DFC_Life合并_我的想法.md`（2026-04-18）

---

## 5. 与代码的一致性核查

以 `Abstract/智能不是模型而是系统.md`（最权威的当前哲学陈述，2026-04-11）中的技术声明为基准：

| Abstract 声明 | 代码位置 | 一致性状态 |
|--------------|---------|-----------|
| "SNN 感知外界事件（消息频率、沉默时长、工具使用、反馈信号）" | `plugins/life_engine/snn/bridge.py`（特征提取函数） | ✅ 已实现 |
| "六维驱动信号：arousal/valence/social_drive/task_drive/exploration_drive/rest_drive" | `plugins/life_engine/snn/core.py`（`DriveCoreNetwork` 输出层，OUTPUT_NAMES 列表） | ✅ 已实现 |
| "通过 STDP 在线学习" | `plugins/life_engine/snn/core.py`（`STDPSynapse.update()` 软 STDP） | ⚠️ 代码存在，但 v1 诊断表明权重长期冻结；v2 修复了根因，但长期有效性未经长期运行验证 |
| "好奇心 τ=30 分钟" | `plugins/life_engine/neuromod/engine.py`：`Modulator("curiosity", ..., tau=1800, ...)` (1800s=30min) | ✅ 精确匹配 |
| "精力 τ=3 小时" | `plugins/life_engine/neuromod/engine.py`：`Modulator("energy", ..., tau=10800, ...)` (10800s=3h) | ✅ 精确匹配 |
| "ODE：dM/dt = (baseline - M) / τ + stimulus × headroom" | `plugins/life_engine/neuromod/engine.py`：`Modulator.update()` 方法 | ✅ 基本匹配（headroom 计算：`1.0 - abs(value - 0.5) * 2.0`） |
| "昼夜节律：深夜精力下降，下午有个小低谷" | `plugins/life_engine/neuromod/engine.py`（`CircadianRhythm` 类，双峰 cos 振荡器） | ✅ 已实现 |
| "习惯追踪：连续多天在同一时间写日记，就会形成习惯" | `plugins/life_engine/neuromod/engine.py`（`HabitTracker` 类，streak 计数） | ✅ 已实现 |
| "SNN 独立于心跳的 tick 循环（不绑定 LLM 心跳）" | `plugins/life_engine/service/core.py`（`_snn_tick_loop`，10 秒间隔） | ✅ 已实现 |
| "LLM 不知道 SNN 和调质层的存在——只看到注入的几行状态描述" | `plugins/life_engine/service/core.py`（`inject_wake_context()` 中的状态格式化注入） | ✅ 已实现 |
| "所有内在状态都可视化……全部在仪表盘上实时可见" | `plugins/life_engine/monitor/`，`report/2026-04-12_web_可视化看板实施报告.md` | ✅ 基本实现（Web 看板 2026-04-12 落地） |
| "中枢主动唤醒 DFC：当内在驱动积累到阈值时，中枢自发地想要做某事" | `plugins/life_engine/tools/` 中存在 `nucleus_tell_dfc` 工具；LifeChatter 中的主动对话触发 | ⚠️ 工具存在，但自动阈值触发机制（"驱动积累到阈值"的具体判定逻辑）需进一步核查 `drives/` 子包 |
| "SNN 的学习：实时发生，每一次交互都在微调权重" | `snn/core.py` `STDPSynapse.update()`，但仅在 `step()`（有真实输入时）触发，非每次心跳 | ⚠️ 概念上夸大（"每一次交互"）；实际为"每次有真实事件输入时触发 STDP" |

**补充核查：`drives/` 子包**

代码中存在 `plugins/life_engine/drives/`（含 `impulse.py`、`rules.py`），这是 Abstract 中未明确提及但已在代码中存在的模块，可能对应"主动唤醒阈值"的规则层。这与 Abstract 中的"涌现而非规则"原则存在潜在张力——若该模块采用了硬编码规则判断是否主动唤醒，则与哲学宣称存在不一致。

---

## 6. 术语表（中-英-定义）

以下术语按出现频率和重要性排列，定义基于文档原文综合提炼：

| 中文术语 | 英文术语 | 标准定义 |
|---------|---------|---------|
| **连续存在** | Continuous Existence | 即使在两次 LLM 调用之间，系统仍然有一个正在变化的内在状态。区别于依赖 prompt 文本拼接模拟的"伪连续性"。 |
| **生命中枢** / **中枢态** | Life Engine / Nucleus Mode | 以定时心跳为驱动、独立于外部用户输入持续运行的内在反思层。负责事件流消化、记忆整理、内心独白、工具调用。对应"内在活动"而非"外在表达"。 |
| **社交态** / **对话流控制器** | Chat Mode / DFC (Default Flow Controller) | 面向用户的对话执行层，响应外部消息并生成回复。历史上作为独立插件（`default_chatter`），2026-04-17 后开始向 `LifeChatter`（life_engine 内置对话模式）迁移。|
| **心跳** | Heartbeat | life_engine 的基本运行单位。每次心跳（默认间隔 30~180 秒）触发一次 LLM 推理调用、SNN 步进、调质层更新。心跳间隔内 SNN 仍以 `decay_only()` 方式持续演化。 |
| **SNN（脉冲神经网络）** | Spiking Neural Network (SNN) | 以 LIF（漏积分发放）神经元模型为基础的皮层下驱动系统。通过 STDP（脉冲时序依赖可塑性）在线学习。不依赖反向传播，输出六维驱动向量注入调质层。 |
| **LIF 神经元** | Leaky Integrate-and-Fire (LIF) Neuron | 基本神经元模型。膜电位 v 以时间常数 τ 向静息电位衰减；超过阈值时发放脉冲（spike）并重置。方程：`dv = (-(v - rest) + current) / τ * dt`。 |
| **STDP（脉冲时序依赖可塑性）** | Spike-Timing-Dependent Plasticity (STDP) | SNN 的在线学习规则：若突触前神经元在突触后神经元放电之前（短时间内）放电，则连接增强（LTP）；反之则削弱（LTD）。在 Neo-MoFox 中以"软 STDP"（sigmoid 连续活跃度替代二值脉冲）实现。 |
| **调质层** / **神经调质系统** | Neuromodulatory Layer / ModulatorSystem | 以 ODE（常微分方程）模拟神经调质浓度动力学的慢层。包含五维调质（好奇心/社交欲/专注力/满足感/精力），以 `dM/dt = (baseline - M)/τ + stimulus × headroom` 驱动，时间常数从 30 分钟到 3 小时不等。 |
| **调质因子** / **调质** | Modulator | 调质层的单一维度，代表一种神经递质/激素类比量（如好奇心、精力）。每个调质有独立的时间常数 τ、基线浓度 baseline 和当前浓度 value。 |
| **headroom（余量）** | Headroom / Marginal Diminishing Factor | 调质 ODE 中的边际效应修正项：`headroom = 1.0 - abs(value - 0.5) * 2.0`。已经接近极值的调质难以继续被推高/推低，模拟生理饱和效应。 |
| **昼夜节律** | Circadian Rhythm | 以 24 小时为周期的精力/活跃度振荡器，通过余弦函数模拟双峰（上午和下午）活跃节律。影响调质层的精力基线。 |
| **习惯追踪器** | Habit Tracker | 以显式统计方式（而非 SNN 学习）记录行为模式（如"连续 N 天写日记"）的组件，输出习惯强度值（`strength = 0.7 × streak_bonus + 0.3 × freq_bonus`）。 |
| **事件流** | Event Stream / Event History | 以统一格式（`LifeEngineEvent`）记录所有交互的时间序列，包含 MESSAGE/HEARTBEAT/TOOL_CALL/TOOL_RESULT 等类型。是 life_engine 上下文的核心数据结构，支持持久化与恢复。 |
| **皮层下系统** | Subcortical System | SNN 和调质层的合称。类比生物大脑皮层下结构（杏仁核/基底节/下丘脑等），负责持续状态维护、驱动生成和情绪余韵，不参与高级认知推理（后者由 LLM/皮层承担）。 |
| **丘脑门控** | Thalamic Gate | 设计愿景中的信息筛选层，决定哪些事件值得触达 LLM 注意力，哪些可以静默处理。在 Abstract/SNN_与系统智能_深度思考.md 中作为四核架构的一部分提出，当前代码实现程度待核查。 |
| **涌现** | Emergence | 项目的核心设计原则：系统的复杂行为（情感状态、主动性）不由硬编码规则直接产生，而是从多个简单子系统的动态交互中自发产生。 |
| **存算一体** | In-Memory Computing | SNN 的设计特性之一：权重既是"存储"（记录学到的关联模式）也是"计算"（决定输出），不需要单独的记忆数据库。 |
| **做梦系统** | Dream System | 在配置的睡眠时段运行的仿生记忆巩固机制。包含 NREM（SNN 事件回放 + 突触稳态降权）和 REM（记忆图谱随机扩散激活 + Hebbian 新边生成）两个阶段。对应代码：`plugins/life_engine/dream/`。 |
| **SHY（突触稳态假说）** | Synaptic Homeostasis Hypothesis (SHY) | 做梦 NREM 阶段的权重归一化机制：对全局权重施加小幅降权（`nrem_homeostatic_rate = 0.02`），防止记忆无限累积，同时保留相对强度差异。 |
| **潜意识同步** | Subconscious Synchronization | life_engine 向 DFC 单向注入内部状态摘要的机制（通过 `SystemReminderStore`）。内容约 150-300 tokens，在 DFC 的 prompt 中呈现为"此刻的内心/最近在做的事/近期的思绪"。2026-04-17 后，随 LifeChatter 架构的推进，该桥接机制预计被取代。 |
| **主题线程** | Thread（Context Thread） | life_engine 主动性框架中的基本单元：一段持续关注的长期主题（有别于 TODO 的一次性任务）。以 `threads.json` 为单一事实源，包含 title/evidence_refs/maturity/energy 等字段。 |
| **心跳间隔** | Heartbeat Interval | life_engine 心跳循环的定时间隔，默认值在不同版本/文档中有所变化：早期方案提及 5-10 分钟，`Abstract/连续存在` 文档中提及 30 秒，当前 `terminology_clarification.md` 提及 120 秒。实际运行值需以当前 `config.toml` 为准。 |
| **软 STDP** | Soft STDP | SNN v2 引入的改进型 STDP 规则：以 `sigmoid(membrane_potential)` 连续活跃度代替二值脉冲参与学习，使低活跃状态下也能触发可塑性更新，解决 v1 版本因放电率过低导致 STDP 无法触发的根因问题。 |
| **LifeChatter** | LifeChatter | `plugins/life_engine/core/chatter.py` 中定义的对话组件，作为 DFC 替代方案注册到框架的 Chatter 体系。直接访问 life_engine 内部状态（无信息损失），统一 system prompt（100% 可缓存），取代 DFC 的多智能体协作架构。 |

---

*本文档为学术研究用途的分析笔记，基于项目文档的历史化考察，不构成对项目技术方案的背书或批判性评价。所有引用均注明原始来源文件。*
