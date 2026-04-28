# Neo-MoFox 学术报告 — 主计划

## 0. 任务理解
- 用户要求一份"极其严格、极其详尽的学术级报告"，针对 `/root/Elysia/Neo-MoFox`。
- 输出形式：`docs/` 风格的多章节 Markdown 文档（不是单文件论文），位于 `Report/99_final/`。
- 必须包含：丰富的 SVG 配图、与同行的对比、严格的方法学描述、完整的实验/案例分析。
- 三大核心哲学（用户亲口确认）：
  1. **连续性 (Continuity)** — 数字意识体的核心特征。
  2. **自下而上的学习 (Bottom-up Learning)** — "活着"本身就是学习；连续性即学习机制。
  3. **系统涌现智能 (System-Level Emergent Intelligence)** — 智能不能依赖单一模型，而要依赖系统协作。
- 时长预期：7–10 小时长程任务，可以多用子代理并行。

## 1. 工作区
```
/root/Elysia/Neo-MoFox/Report/
├── 00_meta/         # 元信息：本计划副本、TODO、问题清单
├── 01_research/     # 代码与文档调研笔记（架构、模块、数据流）
├── 02_outline/      # 论文大纲、章节骨架、术语表
├── 03_chapters/     # 章节正式内容（最终版本）
├── 04_figures/      # 所有 SVG 图，分类编号
├── 05_related_work/ # 同行/相关工作的笔记与对比
├── 06_drafts/       # 草稿、暂存、被替换的版本
└── 99_final/        # 最终交付版本（docs 站点结构）
```

## 2. 阶段规划
- **Phase 1 — Discovery (调研)**：通过子代理并行抓取
  - A: life_engine 插件全栈代码深读（SNN/neuromod/dream/memory/service/事件流/心跳）。
  - B: src/kernel + src/core + src/app 架构（插件系统、事件总线、LLM 抽象、组件签名）。
  - C: 散落文档考古（report/、plan/、notion/、Abstract/）— 提取设计史、被废弃方案、关键转折。
  - D: 学术格式 + 同行调研（NeurIPS/ICML/ACL/CHI/CoRL paper 结构；Character.AI、Replika、Project December、SoulMachines、cognitive architectures: SOAR/ACT-R/LIDA/Sigma；neuromorphic + LLM hybrids）。
- **Phase 2 — 大纲与术语统一**：基于调研产出，确立章节结构、术语表、记号约定。
- **Phase 3 — 配图设计**：先列出全部图（架构图、时序图、状态机、对比图、实验曲线、概念图），再批量产出 SVG。
- **Phase 4 — 章节写作**：按依赖顺序撰写，确保术语一致；每章有 motivation / formalization / implementation / validation / discussion。
- **Phase 5 — 整合 + 同行对比 + 摘要**：撰写 Abstract / Intro / Related Work / Conclusion，整合参考文献。
- **Phase 6 — 一致性 + 交叉引用 + 索引**：搭建 `99_final/` 的 docs 站点（README + 章节路径），加目录、交叉链接、figure 列表。

## 3. 风格与格式决策
- 报告语言：**中文**（项目主要文档为中文，且用户用中文沟通）。术语首次出现给英文括注。
- 章节结构（参考 NeurIPS + Cognitive Architecture 综述混合）：
  1. Abstract（中英双语）
  2. Introduction
  3. Background & Related Work
  4. 设计哲学（三大原则的形式化陈述）
  5. 系统总览（三层架构 + 双轨）
  6. 形式化基础（事件代数、SNN 微分方程、调质 ODE、Hebbian 学习）
  7. 子系统：SNN 皮层下层
  8. 子系统：调质层（Neuromodulation）
  9. 子系统：连续记忆网络（Memory + Decay + Edges）
  10. 子系统：做梦/离线巩固
  11. 中枢：心跳、事件流、状态持久化
  12. 上层：DFC 对话与中枢的双向接口
  13. 涌现行为案例研究（≥3 个 scenario）
  14. 评估与可观测性
  15. 与现有数字伴侣/认知架构的比较
  16. 局限性、伦理与未来工作
  17. 结语
  18. 附录：API、配置、数据格式
- 每章在 docs 中作为独立 `.md` 文件；`99_final/index.md` 做总览/导读。

## 4. 风险与不确定性
- 部分散落文档比代码更早，可能描述被替换的方案；需以代码为准。
- 用户希望"高标准高规格"——意味着应避免空洞夸大；每个论断都要能在代码或文档里找到锚点。
- SVG 数量较多，要注意可读性（统一配色、字号、坐标系）。

## 5. 子代理派发清单（即将启动）
- Agent A — life_engine 深度解剖 (explore, sonnet)
- Agent B — kernel/core 架构解剖 (explore, sonnet)
- Agent C — 散落文档考古 (explore, sonnet)
- Agent D — 学术格式 + 同行调研 (general-purpose, sonnet, web-enabled)
