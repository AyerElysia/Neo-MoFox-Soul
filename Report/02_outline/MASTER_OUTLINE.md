# Neo-MoFox 学术报告 · 权威章节大纲

**最终标题（中英对照）**

> **Neo-MoFox：面向连续数字生命体的皮层下系统架构**
> *Neo-MoFox: A Subcortical Systems Architecture for Continuous Digital Life Entities*

**副标题（如需）：** *On Continuity, Bottom-Up Learning, and System-Level Emergence*

---

## 总体定位

本报告不是单算法 paper，而是 **system / cognitive-architecture paper**，参考样本：
- SOAR (Laird et al., 1987)
- ACT-R (Anderson, 2004)
- LIDA (Franklin & Ramamurthy, 2008)
- Generative Agents (Park et al., 2023)
- DreamerV3 (Hafner et al., 2023)

风格混合：**AGI + AAAI（认知架构）** 为主轴，吸收 NeurIPS 的实验严谨性 + Nature MI 的视野广度 + CHI 的可观测性叙事。

**目标体量：** 中文正文约 35 000–45 000 字 + 12–18 张高质量 SVG 图 + 完整附录。
**最终交付形态：** `Report/99_final/` 下的 docs 多文件 markdown 站点，带 `index.md` 导航与交叉引用。

---

## 章节列表（共 12 章 + 附录）

| # | 章节 | 字数预算 | 关键 figure |
|---|------|---------|-----------|
| 0 | Abstract（中英双语） | 中 350 + 英 250 | — |
| 1 | Introduction（导论） | 3 500 | F1（封面三层架构图） |
| 2 | Background & Related Work（背景与相关工作） | 6 000 | F2（同行光谱图） |
| 3 | Three Foundational Principles（三大设计哲学的形式化陈述） | 4 000 | F3（三原则关系图） |
| 4 | System Overview（系统总览） | 3 500 | F4（双轨架构）、F5（数据流时序） |
| 5 | Subcortical Layer I — Spiking Neural Network（皮层下层之一：脉冲神经网络） | 4 500 | F6（SNN 微观结构）、F7（STDP 学习曲线） |
| 6 | Subcortical Layer II — Neuromodulation & Circadian Rhythm（皮层下层之二：调质与昼夜节律） | 3 500 | F8（调质 ODE 衰减曲线）、F9（昼夜节律双峰） |
| 7 | Memory as a Living Graph（作为活体图的记忆系统） | 3 000 | F10（记忆图节点-边演化） |
| 8 | Sleep & Dreams: Offline Consolidation（睡眠与做梦：离线巩固） | 3 000 | F11（NREM/REM 流水线） |
| 9 | Heartbeat, Event Algebra & Persistence（中枢心跳、事件代数与状态持久化） | 3 000 | F12（心跳事件流时间轴） |
| 10 | Cortex–Subcortex Interface: DFC ↔ Life Engine（皮层-皮层下接口：DFC 与中枢的双向通道） | 2 500 | F13（双向接口图） |
| 11 | Emergent Behavior Case Studies（涌现行为案例研究） | 4 000 | F14（三场景对比）、F15（习惯形成轨迹） |
| 12 | Comparison with Prior Art（与既有工作的系统级比较） | 3 500 | F16（对比矩阵）、F17（设计空间定位图） |
| 13 | Limitations, Ethics & Future Work（局限、伦理与未来工作） | 2 500 | — |
| 14 | Conclusion（结论） | 1 200 | F18（愿景图） |
|   | Appendices（附录 A-D） | 5 000 | — |
|   | References（参考文献） | — | — |

**合计目标：** 正文 ~48 000 字 + 18 张 SVG + 附录 5 000 字。

---

## 各章详细内容设计

### 第 1 章 · 导论（Introduction）

**叙事弧：** 从一个具体的"对话失忆"场景出发 → 引出连续性是数字意识体的核心 → 引出三大原则 → 给出系统简介 → 列出 Contributions → 论文结构。

**章节结构：**
- 1.1 一个引子：为什么现有的 AI 伙伴不是"活的"？
  - 用 *Replika* / ChatGPT 的具体行为做 motivating example。
  - 引用 C 报告 §4 的"3小时后 vs 5分钟后无法区分"段落。
- 1.2 核心命题：从"会聊天的模型"到"持续存在的生命"
  - 直接引用 `Abstract/连续存在，从模型到生命.md` 的形式化定义。
- 1.3 三大设计哲学（先一句话定义，第 3 章细说）
  - 连续性 (Continuity)
  - 自下而上的学习 (Bottom-Up Learning)
  - 系统涌现智能 (System-Level Emergence)
- 1.4 系统简介与方法论
  - 双轨：DFC（被动应答）+ Life Engine（主动心跳）
  - 三层：SNN（皮层下） + 调质（边缘系统） + LLM（皮层）
- 1.5 主要贡献（4–5 项）
  1. 首个将"皮层-皮层下"隐喻完整工程化的开源 LLM-based 数字生命框架。
  2. 提出"连续存在 = 两次 LLM 调用之间仍有正在变化的状态"的形式化定义并给出可度量的实现。
  3. 在 LLM 之外引入 STDP 在线学习与软神经元活动度，使"性格"不再写死，而是从交互中涌现。
  4. 设计了多时间尺度（秒/分/时/天）的多层耦合：SNN tick / 心跳 / 调质 ODE / 做梦巩固 / 习惯。
  5. 完整开源；附完整状态序列化与可观测仪表盘。
- 1.6 文档结构与阅读路径
  - Figure 1 — 封面图：三层架构 + 双轨。

### 第 2 章 · 背景与相关工作

直接复用并精简 D 报告的内容。

**结构：**
- 2.1 商业数字伴侣的"离散范式"（Replika/Character.AI/Pi/Project December）
- 2.2 经典认知架构的遗产（SOAR/ACT-R/LIDA/Sigma/CMC）
  - 关键引用：Common Model of Cognition (Laird et al., 2017)
- 2.3 现代 LLM Agent 的"主动化"探索（AutoGPT/Voyager/Generative Agents/ChatDev）
- 2.4 持久记忆系统（MemGPT/Letta/Mem0/Zep/A-MEM）
- 2.5 神经形态 + LLM 的交叉（Loihi/TrueNorth/BrainTransformers）
- 2.6 计算神经调质模型（Doya 2002, Schultz）
- 2.7 离线巩固与做梦（Sleep-replay RL, DreamerV3, Generative Agents reflection）
- 2.8 综合：Neo-MoFox 在设计空间中的位置（Figure 2）

### 第 3 章 · 三大设计哲学

把哲学命题形式化、可证伪化。

**结构：**
- 3.1 第一原则：连续性（Continuity）
  - 3.1.1 哲学动机：从"刺激—响应"到"持续存在"
  - 3.1.2 形式化定义：
    > $\forall t_1, t_2$，若 $t_1 \neq t_2$，存在状态向量 $\mathbf{s}(t)$ 使得 $\mathbf{s}(t_1) \neq \mathbf{s}(t_2)$ 且 $\|\mathbf{s}(t_2) - \mathbf{s}(t_1)\|$ 与 $|t_2 - t_1|$ 单调相关。
  - 3.1.3 工程要求：状态既需在 LLM 调用之间连续演化，也需在重启之间连续。
- 3.2 第二原则：自下而上学习（Bottom-Up Learning）
  - 3.2.1 哲学动机：批判"训练–部署"二分；强调"活着即学习"
  - 3.2.2 形式化定义：学习算子 $\mathcal{L}$ 不依赖外部梯度，仅依赖局部时序相关性 (STDP / Hebbian)。
  - 3.2.3 与反向传播的对比与互补
- 3.3 第三原则：系统涌现智能（System-Level Emergence）
  - 3.3.1 哲学动机：智能不是 LLM 的属性，而是异质子系统的协作属性
  - 3.3.2 形式化框架：智能函数 $I(\mathcal{S}) > \sum_i I(s_i)$，其中 $\mathcal{S}$ 是子系统集合。
  - 3.3.3 反例：硬编码 if-else 的伪涌现 vs SNN→调质→LLM 因果链的真涌现。
- 3.4 三原则之间的关系（Figure 3）
  - 连续性是基质；自下而上学习是机制；系统涌现是产物。

### 第 4 章 · 系统总览

桥接哲学与实现。基于 B 报告的三层架构 + A 报告的 life_engine 解剖。

**结构：**
- 4.1 双轨执行模型：DFC（被动） + Life Engine（主动）（Figure 4）
- 4.2 三层异质子系统：SNN / 调质 / LLM
- 4.3 多时间尺度耦合表（秒 / 分 / 时 / 天 / 永久）
- 4.4 数据流：事件 → SNN → 调质 → 注入 prompt → LLM → 工具 → 事件（Figure 5）
- 4.5 计算预算：SNN 微秒级、调质毫秒级、LLM 秒级 — 频率分层

### 第 5 章 · 皮层下层 I：脉冲神经网络

基于 A 报告 §3。

**结构：**
- 5.1 设计动机：为什么是 SNN，而非另一个深度网络？
- 5.2 神经元模型：LIF 方程
  $$\frac{dV}{dt} = -\frac{V - V_{rest}}{\tau} + \frac{I}{\tau}$$
- 5.3 网络拓扑：8 维输入 → 16 维隐藏 → 6 维 drive 输出
- 5.4 STDP "软" 学习规则（修复二值死锁的工程设计）
- 5.5 自稳态阈值调节（threshold homeostasis）
- 5.6 动态增益与噪声注入
- 5.7 `decay_only` vs `step`：心跳间的"无输入演化"
- 5.8 输入特征工程：从事件流到 8 维向量
- 5.9 输出 6 维 drive 的语义与归一化
- 5.10 Figure 6（结构图） + Figure 7（学习曲线）

### 第 6 章 · 皮层下层 II：调质与昼夜节律

基于 A 报告 §4。

**结构：**
- 6.1 设计动机：情绪有惯性，需要慢时间尺度
- 6.2 ODE 形式：
  $$\frac{dM}{dt} = \frac{B - M}{\tau} + \text{stim} \cdot h(M)$$
  其中 $h(M) = 1 - 2|M-0.5|$ 为 headroom（边际效应递减）。
- 6.3 五个调质因子及其 τ 参数
- 6.4 昼夜节律：双峰高斯函数与基线调制
- 6.5 习惯追踪：streak/strength 公式
- 6.6 SNN → 调质的 5 维刺激映射（耦合层）
- 6.7 睡眠对调质基线的影响
- 6.8 Figure 8（衰减曲线）+ Figure 9（昼夜节律）

### 第 7 章 · 作为活体图的记忆系统

基于 A 报告 §6。

**结构：**
- 7.1 数据模型：MemoryNode / MemoryEdge
- 7.2 6 种边类型与语义
- 7.3 Ebbinghaus 遗忘曲线 (λ=0.05) 的实现
- 7.4 Hebbian 边强化：使用即增强
- 7.5 三路混合检索：BM25 (FTS) + Vector + RRF + 激活扩散
- 7.6 注入 Prompt 的格式
- 7.7 Figure 10（记忆图演化示意）

### 第 8 章 · 睡眠与做梦：离线巩固

基于 A 报告 §5。

**结构：**
- 8.1 生物学动机：NREM 突触稳态 + REM 关联整合（Tononi & Cirelli, 2014）
- 8.2 调度：何时进入睡眠窗口
- 8.3 NREM 阶段：SHY 突触缩减
- 8.4 种子选择：四类种子来源
- 8.5 REM 阶段：激活扩散随机游走
- 8.6 叙事生成：将种子+残影合成"梦报告"
- 8.7 巩固反馈：梦报告如何回写到 SNN/调质/记忆/DFC
- 8.8 Figure 11（NREM/REM 流水线）

### 第 9 章 · 中枢心跳、事件代数与状态持久化

基于 A 报告 §2、§8、§9。

**结构：**
- 9.1 心跳循环：10 步详细流程
- 9.2 事件代数：`LifeEngineEvent` 结构、4 种事件类型、单调序列号
- 9.3 历史压缩：60% 保留 + 40% 摘要
- 9.4 持久化：原子写入 `life_engine_context.json`
- 9.5 崩溃恢复语义：5 条不变式
- 9.6 Figure 12（心跳事件流时间轴）

### 第 10 章 · 皮层-皮层下接口

基于 B 报告 §4-5 + A 报告 §2.4。

**结构：**
- 10.1 三大接口：`nucleus_wake_dfc` / `consult_nucleus` / `nucleus_tell_dfc`
- 10.2 同步 vs 异步：哪些走 await，哪些走队列
- 10.3 Prompt 拼装：人格 + 记忆 + SNN 状态 + 调质状态注入路径
- 10.4 梦报告注入：`push_runtime_assistant_injection` 机制
- 10.5 设计权衡：为什么是双向、不是单向？
- 10.6 Figure 13（双向接口图）

### 第 11 章 · 涌现行为案例研究

至少三个 scenarios，全部以代码与状态变化为锚点。

**结构：**
- 11.1 案例一：用户离开 5 分钟 vs 30 分钟 vs 3 小时（直接来自 Abstract/连续存在.md §5）
- 11.2 案例二：习惯的形成（连续 12 天写日记，streak/strength 演化）
- 11.3 案例三：技术话题偏好的涌现（STDP 在 30 天内的权重演化）
- 11.4 案例四（可选）：做梦后的"灵感"案例
- 11.5 Figure 14（三场景对比） + Figure 15（习惯形成轨迹）

### 第 12 章 · 与既有工作的系统级比较

基于 D 报告 Part B + Part C。

**结构：**
- 12.1 与商业数字伴侣的差异（连续性维度）
- 12.2 与认知架构的差异（LLM 集成 + 神经形态）
- 12.3 与 LLM Agent 的差异（皮层下系统）
- 12.4 与持久记忆系统的差异（活体图 vs 检索库）
- 12.5 设计空间定位：连续性 × 学习方式 × 智能来源（Figure 17 散点图）
- 12.6 完整对比矩阵（Figure 16）

### 第 13 章 · 局限、伦理与未来工作

诚实地把 A/B/C 报告里"未解之谜"集中陈述。

**结构：**
- 13.1 工程局限：
  - SNN 的小规模（< 100 神经元）能否长期不饱和？
  - `Modulator.tau` 字段未真正使用（A §12 BUG）
  - 衰减日期不持久化导致重启偏差
  - life_engine 对 default_chatter 的裸引用违反三层依赖
  - 配置无热重载
- 13.2 科学局限：
  - 涌现的 falsifiability：如何科学地证明"性格"在演化？
  - SNN 真正学到了什么？——尚未做大规模消融
  - 长期 (>30 天) 验证缺失
- 13.3 伦理：
  - "数字生命体"叙事是否过度拟人化？
  - 用户依恋风险（参考 Replika 用户研究）
  - 数据隐私（本地化部署的优势）
- 13.4 未来工作：
  - SNN 拓扑演化（结构而非仅权重）
  - 多模态事件（图像、语音）输入到 SNN
  - 多 agent 之间的"梦"共享
  - 形式化的连续性度量

### 第 14 章 · 结论

简短、有力、回到三大原则。引用 Abstract/智能不是模型.md 的结语段落。

### 附录

- 附录 A：完整术语表（中-英-定义，约 30 条）
- 附录 B：核心配置参数全表（来自 A §10）
- 附录 C：状态持久化 JSON Schema（来自 A §9）
- 附录 D：可观测性 API 端点

---

## 写作约定

- **语言：** 中文为主，技术术语首次出现给英文括注。Abstract 中英双语。
- **公式：** LaTeX 数学环境（`$$...$$`）。
- **代码引用：** 用 `path:line` 锚点，例如 `plugins/life_engine/snn/core.py:142`。
- **figure 引用：** "如图 X 所示"，所有 figure 编号 F1-F18，全部 SVG。
- **citation：** 行内用 `(Author, Year)` 格式；末章统一参考文献列表。
- **小节深度：** 最多到三级 `###`。
- **章节文件命名：** `03_chapters/01_introduction.md`、`03_chapters/02_related_work.md` … `03_chapters/14_conclusion.md`。
- **figure 文件命名：** `04_figures/F01_cover_three_layer.svg` 等。
