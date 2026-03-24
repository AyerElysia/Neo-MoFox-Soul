# 2026-03-24 personality_engine_plugin 实现报告

## 1. 任务目标

在不改动核心代码的前提下，将 `evolving_personality` 能力插件化接入 Neo-MoFox，形成可加载、可运行、可观测、可测试的人格引擎插件。

## 2. 实现范围

本次仅新增插件与测试文件，未改动 `src/` 核心框架代码。

新增插件目录：

- `plugins/personality_engine_plugin/`

新增核心文件：

- `plugins/personality_engine_plugin/manifest.json`
- `plugins/personality_engine_plugin/plugin.py`
- `plugins/personality_engine_plugin/config.py`
- `plugins/personality_engine_plugin/service.py`
- `plugins/personality_engine_plugin/prompts.py`
- `plugins/personality_engine_plugin/commands/personality_command.py`
- `plugins/personality_engine_plugin/components/events/personality_scan_event.py`
- `plugins/personality_engine_plugin/components/events/personality_prompt_injector.py`

新增配置文件：

- `config/plugins/personality_engine_plugin/config.toml`

新增测试：

- `test/plugins/personality_engine_plugin/test_personality_engine_service.py`
- `test/plugins/personality_engine_plugin/test_personality_prompt_injector.py`
- `test/plugins/personality_engine_plugin/test_personality_scan_event.py`

## 3. 功能说明

### 3.1 状态管理

- 按 `stream_id + chat_type` 隔离人格状态。
- 存储内容包含：`mbti`、八功能权重、`change_history`、最后补偿功能、当前假设、结构变更历史。
- 存储路径：`data/personality_engine/{private|group|discuss}/<stream_id>.json`。

### 3.2 自动推进

- 事件订阅：`ON_CHATTER_STEP_RESULT`。
- 每累计 `trigger_every_n_messages` 次有效对话触发一次人格推进。
- 推进流程：
  1. 收集最近消息窗口；
  2. 通过 LLM（可关闭）选择本轮补偿功能；
  3. 失败时启发式回退；
  4. 应用权重变化与四类结构反思；
  5. 写回状态。

### 3.3 Prompt 注入

- 事件订阅：`on_prompt_build`。
- 默认注入目标：`default_chatter_system_prompt`。
- 注入字段：`extra_info`（若是 user prompt 则注入 `extra`）。
- 注入内容包含：当前 MBTI、主辅功能、本轮补偿、当前假设（可选详细权重）。

### 3.4 命令接口

- `/personality view`
- `/personality advance`
- `/personality reset`
- `/personality set_mbti <MBTI>`

## 4. 稳定性处理

已实现以下防故障措施：

- 禁止 `eval`，仅使用 JSON 解析（含安全剪裁解析）。
- LLM 输出解析失败采用有限重试，不无限循环。
- LLM 不可用时自动启发式回退，主流程不中断。
- 权重与变更历史均做清洗和归一化，避免非法值扩散。

## 5. 测试结果

执行命令：

```bash
pytest -q -o addopts='' \
  test/plugins/personality_engine_plugin/test_personality_engine_service.py \
  test/plugins/personality_engine_plugin/test_personality_prompt_injector.py \
  test/plugins/personality_engine_plugin/test_personality_scan_event.py
```

结果：

- `4 passed`

补充检查：

- 新插件 Python 文件已通过 `py_compile`。
- 新插件模块导入通过。

## 6. 已知边界

- 当前版本将“功能选择”交给 LLM（可配置关闭），但“结构反思决策”采用规则引擎以优先保证稳定性。
- 未实现离线批量问卷实验链路（`Personality_test`），仅实现在线人格演化插件链路。

## 7. 后续建议

- 增加更多场景化回归测试（长对话稳定性、不同 MBTI 初始值切换）。
- 若后续需要更强可解释性，可在变更历史中记录更多中间阈值数据。
- 可考虑新增 `/personality history` 命令便于线上观测演化轨迹。

