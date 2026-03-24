"""personality_engine_plugin 提示词。"""

from __future__ import annotations

import json
from typing import Any

FUNCTION_BRIEFS: dict[str, str] = {
    "Ti": "内部逻辑分析、原理拆解、结构化推演",
    "Te": "外部组织优化、效率导向、执行落地",
    "Fi": "个人价值与道德判断、内在一致性",
    "Fe": "群体情绪协调、关系维护、社会规范适配",
    "Ni": "深层模式洞察、趋势预判、长期整合",
    "Ne": "多可能性探索、创意联想、机会发现",
    "Si": "经验记忆调用、细节核验、稳态维持",
    "Se": "当下感知与即时行动、现实环境响应",
}


def build_baseline_hypothesis(*, main_func: str, aux_func: str) -> str:
    """构建初始人格基线假设。"""
    return f"基线人格以 {main_func}-{aux_func} 协同应对任务，优先保持该结构稳定。"


def build_selector_system_prompt() -> str:
    """构建功能选择系统提示词。"""
    return (
        "你是荣格八功能人格动态分析器。"
        "请严格遵循以下机制：\n"
        "1) 先分析任务核心需求（思维/情感/感觉/直觉）；\n"
        "2) 再判断需求偏向内倾还是外倾；\n"
        "3) 检查当前主导-辅助功能是否足够；\n"
        "4) 若不足，从未充分分化功能中选择本轮补偿功能。\n"
        "你必须只输出 JSON，不得输出其它文本。"
    )


def build_selector_user_prompt(
    *,
    trigger: str,
    mbti: str,
    main_func: str,
    aux_func: str,
    weights: dict[str, float],
    recent_messages: str,
) -> str:
    """构建功能选择用户提示词。"""
    messages = recent_messages.strip() or "（无可用近期对话）"
    miss_funcs = [f for f in FUNCTION_BRIEFS if f not in {main_func, aux_func}]
    return (
        "请基于下列状态完成一次“补偿功能识别”。\n"
        "## 八功能说明 ##\n"
        + "\n".join([f"- {func}: {desc}" for func, desc in FUNCTION_BRIEFS.items()])
        + "\n\n"
        "## 当前人格结构 ##\n"
        f"- MBTI: {mbti}\n"
        f"- 主导: {main_func}\n"
        f"- 辅助: {aux_func}\n"
        f"- 未充分分化池: {', '.join(miss_funcs)}\n"
        f"- 权重: {json.dumps(weights, ensure_ascii=False)}\n"
        f"- 触发来源: {trigger}\n\n"
        "## 最近对话 ##\n"
        f"{messages}\n\n"
        "## 输出要求 ##\n"
        "只输出如下 JSON：\n"
        "{\n"
        '  "function": "Ti",\n'
        '  "reason": "为什么该功能最匹配当前任务需求",\n'
        '  "hypothesis": "一句话描述当前心理倾向"\n'
        "}\n\n"
        "可选 function 只能是: Ti, Te, Fi, Fe, Ni, Ne, Si, Se。"
    )


def build_prompt_block(
    *,
    title: str,
    mbti: str,
    main_func: str,
    aux_func: str,
    selected_function: str,
    hypothesis: str,
    weights: dict[str, float],
    detail: bool,
    mode: str,
    recent_changes: list[str] | None = None,
    include_function_catalog: bool = True,
) -> str:
    """构建 prompt 注入块。"""
    mode_lc = str(mode or "compact").strip().lower()
    if mode_lc not in {"compact", "paper_strict"}:
        mode_lc = "compact"

    lines = [
        f"【{title}】",
        f"- 当前类型：{mbti}（{main_func}-{aux_func}）",
        f"- 当前补偿：{selected_function or '暂无'}",
        f"- 当前假设：{hypothesis or '暂无'}",
    ]
    if mode_lc == "compact":
        if detail:
            lines.append(
                "- 权重："
                + " ".join(
                    [
                        f"Ti{weights.get('Ti', 0.0):.2f}",
                        f"Te{weights.get('Te', 0.0):.2f}",
                        f"Fi{weights.get('Fi', 0.0):.2f}",
                        f"Fe{weights.get('Fe', 0.0):.2f}",
                        f"Ni{weights.get('Ni', 0.0):.2f}",
                        f"Ne{weights.get('Ne', 0.0):.2f}",
                        f"Si{weights.get('Si', 0.0):.2f}",
                        f"Se{weights.get('Se', 0.0):.2f}",
                    ]
                )
            )
        return "\n".join(lines)

    # paper_strict 模式：更接近论文的“机制型注入”，而非仅标签注入
    miss_funcs = [f for f in FUNCTION_BRIEFS if f not in {main_func, aux_func}]
    lines.extend(
        [
            "",
            "##Compensation Mechanism##",
            "1. 若主导-辅助功能无法有效应对当前任务，应触发补偿机制。",
            "2. 补偿功能必须基于任务需求匹配八功能，而非随机切换。",
            "3. 当补偿功能被持续高频使用时，可能引发主辅结构调整。",
            "",
            "##执行步骤##",
            "1. 任务需求分析：识别问题核心维度与约束。",
            "2. 主辅评估：判断当前主导/辅助是否足够。",
            "3. 补偿识别：若不足，优先在未充分分化池中选择最匹配功能。",
            "4. 响应生成：在不暴露内部推理的前提下给出自然回答。",
            "",
            "##当前人格结构##",
            f"- 主导功能: {main_func}",
            f"- 辅助功能: {aux_func}",
            f"- 未充分分化池: {', '.join(miss_funcs)}",
        ]
    )
    if detail:
        lines.append(
            "- 当前权重："
            + " ".join(
                [
                    f"Ti{weights.get('Ti', 0.0):.2f}",
                    f"Te{weights.get('Te', 0.0):.2f}",
                    f"Fi{weights.get('Fi', 0.0):.2f}",
                    f"Fe{weights.get('Fe', 0.0):.2f}",
                    f"Ni{weights.get('Ni', 0.0):.2f}",
                    f"Ne{weights.get('Ne', 0.0):.2f}",
                    f"Si{weights.get('Si', 0.0):.2f}",
                    f"Se{weights.get('Se', 0.0):.2f}",
                ]
            )
        )
    if include_function_catalog:
        lines.append("")
        lines.append("##八功能映射##")
        lines.extend([f"- {func}: {desc}" for func, desc in FUNCTION_BRIEFS.items()])
    if recent_changes:
        lines.append("")
        lines.append("##近期结构变化##")
        lines.extend([f"- {item}" for item in recent_changes if item.strip()])
    return "\n".join(lines)


def build_reflection_reason(
    *,
    action: str,
    old_mbti: str,
    new_mbti: str,
    selected_function: str,
    extra: dict[str, Any] | None = None,
) -> str:
    """构建结构变更原因文本。"""
    detail = ""
    if extra:
        detail = f" | extra={json.dumps(extra, ensure_ascii=False)}"
    return (
        f"{action}: {old_mbti}->{new_mbti}, selected={selected_function}{detail}"
    )
