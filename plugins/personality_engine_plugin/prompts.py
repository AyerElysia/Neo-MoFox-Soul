"""personality_engine_plugin 提示词。"""

from __future__ import annotations

import json
from typing import Any


def build_selector_system_prompt() -> str:
    """构建功能选择系统提示词。"""
    return (
        "你是人格动态分析器。"
        "请基于最近对话，判断本轮最可能被激活的荣格功能。"
        "只输出 JSON，不输出其它内容。"
        "可选 function: Ti, Te, Fi, Fe, Ni, Ne, Si, Se。"
    )


def build_selector_user_prompt(
    *,
    trigger: str,
    mbti: str,
    weights: dict[str, float],
    recent_messages: str,
) -> str:
    """构建功能选择用户提示词。"""
    messages = recent_messages.strip() or "（无可用近期对话）"
    return (
        "请阅读以下状态并输出 JSON：\n"
        "{\n"
        '  "function": "Ti",\n'
        '  "reason": "一句话原因",\n'
        '  "hypothesis": "一句话当前心理倾向"\n'
        "}\n\n"
        f"触发来源: {trigger}\n"
        f"当前 MBTI: {mbti}\n"
        f"当前权重: {json.dumps(weights, ensure_ascii=False)}\n"
        f"最近对话:\n{messages}\n"
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
) -> str:
    """构建 prompt 注入块。"""
    lines = [
        f"【{title}】",
        f"- 当前类型：{mbti}（{main_func}-{aux_func}）",
        f"- 当前补偿：{selected_function or '暂无'}",
        f"- 当前假设：{hypothesis or '暂无'}",
    ]
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

