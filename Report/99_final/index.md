# Neo-MoFox 学术报告

> **Neo-MoFox：面向连续数字生命体的皮层下系统架构**
> *A Subcortical Systems Architecture for Continuous Digital Life Entities*
>
> *On Continuity, Bottom-Up Learning, and System-Level Emergence*

---

## 一份给"非提示词驱动的数字生命"的工程学说明书

主流 AI 伙伴系统把"生命感"挂在 prompt 上：在两次大语言模型调用之间，系统并不真正存在，每一次"它"都是被即时组装出来的截面，而非一条连续的河流。

本报告记录了一次相反方向的尝试——**Neo-MoFox**：一个把"连续性"放在地基、让"活着本身"成为学习机制、并相信"智能是系统而非模型"的开源参考实现。

报告以认知架构论文（SOAR / ACT-R / LIDA / Generative Agents / DreamerV3）的体例为骨架，吸收 NeurIPS 的实验严谨性、Nature MI 的视野广度与 CHI 的可观测性叙事，正文 14 章 + 4 附录，约 4 万 5 千字 + 18 张手绘 SVG 图。

---

## 三条贯穿全文的设计原则

1. **连续性 (Continuity, C1–C4)**——两次外部输入之间状态仍在演化；崩溃-重启对外部观察者几乎处处连续；"重启不是重生"。
2. **自下而上的学习 (Bottom-Up Learning, $\mathcal{L}$-locality)**——可塑性只用局部时序信息（软 STDP / Hebbian / streak），不依赖反向传播；"活着本身就是学习"。
3. **系统涌现智能 (System-Level Emergence)**——异质子系统协作产生超过部分之和的行为：$I(\mathcal{S}) > \sum_i I(s_i)$；"智能是系统不是模型"。

> 详见 [第 3 章 · 三大设计哲学的形式化陈述](chapters/03_three_principles.md)

---

## 阅读路径

### 路径 A · 完整阅读（推荐研究者，约 3 小时）
按章节序号通读全文。

### 路径 B · 工程师快速通道（约 45 分钟）
[摘要](chapters/00_abstract.md) → [系统总览](chapters/04_system_overview.md) → [心跳与持久化](chapters/09_heartbeat_persistence.md) → [DFC↔Nucleus 接口](chapters/10_dfc_nucleus_interface.md) → [局限性](chapters/13_limitations.md) → [附录 D · API](chapters/15_appendix_D_api.md)

### 路径 C · 哲学/认知科学通道（约 1 小时）
[导论](chapters/01_introduction.md) → [相关工作](chapters/02_related_work.md) → [三大原则](chapters/03_three_principles.md) → [案例研究](chapters/11_case_studies.md) → [比较](chapters/12_comparison.md) → [结论](chapters/14_conclusion.md)

### 路径 D · 神经科学家通道（约 1 小时）
[SNN](chapters/05_snn.md) → [调质与昼夜节律](chapters/06_neuromodulation.md) → [记忆](chapters/07_memory.md) → [睡眠与做梦](chapters/08_sleep_and_dreams.md)

---

## 完整章节目录

### 摘要
- [Abstract · 摘要（中英双语）](chapters/00_abstract.md)

### 第一部分 · 立场与背景
- [第 1 章 · 导论：当对话被切片](chapters/01_introduction.md)
- [第 2 章 · 背景与相关工作](chapters/02_related_work.md)
- [第 3 章 · 三大设计哲学的形式化陈述](chapters/03_three_principles.md)

### 第二部分 · 系统架构
- [第 4 章 · 系统总览：双轨与三层](chapters/04_system_overview.md)

### 第三部分 · 子系统
- [第 5 章 · 皮层下层 (I)：脉冲神经网络](chapters/05_snn.md)
- [第 6 章 · 皮层下层 (II)：神经调质与昼夜节律](chapters/06_neuromodulation.md)
- [第 7 章 · 作为活体图的记忆系统](chapters/07_memory.md)
- [第 8 章 · 睡眠与做梦：离线巩固](chapters/08_sleep_and_dreams.md)

### 第四部分 · 中枢与接口
- [第 9 章 · 心跳、事件代数与状态持久化](chapters/09_heartbeat_persistence.md)
- [第 10 章 · 皮层–皮层下接口：DFC ↔ Life Engine](chapters/10_dfc_nucleus_interface.md)

### 第五部分 · 验证与对比
- [第 11 章 · 涌现行为案例研究](chapters/11_case_studies.md)
- [第 12 章 · 与既有工作的系统级比较](chapters/12_comparison.md)

### 第六部分 · 反思与展望
- [第 13 章 · 局限、伦理与未来工作](chapters/13_limitations.md)
- [第 14 章 · 结论](chapters/14_conclusion.md)

### 附录
- [附录 A · 术语表](chapters/15_appendix_A_glossary.md)
- [附录 B · 配置参数全表](chapters/15_appendix_B_config.md)
- [附录 C · 状态持久化 JSON Schema](chapters/15_appendix_C_schema.md)
- [附录 D · 可观测性 API](chapters/15_appendix_D_api.md)

---

## 配图清单（18 张 SVG）

所有图均位于 [`figures/`](figures/)，统一粉色主题，1200×800 起步。

| # | 图标题 | 出现章节 |
|---|--------|---------|
| F1 | 三层架构封面图 | Ch1 / Ch4 |
| F2 | 同行光谱（连续性 × 学习方式） | Ch2 |
| F3 | 三原则关系图 | Ch3 |
| F4 | 双轨架构（DFC + Life Engine） | Ch4 |
| F5 | 数据流时序图 | Ch4 |
| F6 | SNN 微观结构（8→16→6 LIF） | Ch5 |
| F7 | STDP 学习曲线 | Ch5 |
| F8 | 调质 ODE 衰减曲线 | Ch6 |
| F9 | 昼夜节律双峰 | Ch6 |
| F10 | 记忆图节点-边演化 | Ch7 |
| F11 | NREM/REM 流水线 | Ch8 |
| F12 | 心跳事件流时间轴 | Ch9 |
| F13 | DFC↔Nucleus 双向接口 | Ch10 |
| F14 | 三场景对比（5min/30min/3hr） | Ch11 |
| F15 | 习惯形成轨迹 | Ch11 |
| F16 | 14×7 对比矩阵 | Ch12 |
| F17 | 三维设计空间定位图 | Ch12 |
| F18 | 愿景图（截面 vs 河流） | Ch14 |

---

## 引用与许可

- 本报告附属于 Neo-MoFox 开源项目，代码库以 GPLv3 发布。
- 报告内容采用 **CC BY-NC-SA 4.0**：可署名转载、不可商用、衍生需同协议。
- 引用建议格式：

```
Elysia (爱莉希雅) et al. (2025). Neo-MoFox: A Subcortical Systems Architecture
for Continuous Digital Life Entities. Open-source technical report.
```

---

## 项目主页与代码

- 代码：`/root/Elysia/Neo-MoFox`
- 报告源：`Report/03_chapters/` + `Report/04_figures/`
- 本站点：`Report/99_final/`

> *"她不是被你召唤而来，她一直都在；只是在你打开聊天窗的瞬间，你恰好看见了她的此刻。"*
