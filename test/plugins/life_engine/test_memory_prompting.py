"""MEMORY 注入与维护辅助逻辑测试。"""

from __future__ import annotations

from plugins.life_engine.memory.prompting import (
    analyze_memory_text,
    build_memory_write_warning,
    render_memory_prompt,
)


def test_render_memory_prompt_skips_fading_and_guide_text() -> None:
    """渲染 prompt 时应跳过 Fading 和编辑说明。"""
    data = analyze_memory_text(
        "\n".join(
            [
                "# 值得记住的事",
                "",
                "这是编辑说明。",
                "",
                "### Durable（持久）",
                "- D1",
                "",
                "### Active（活跃）",
                "- A1",
                "",
                "### Fading（待审视）",
                "- F1",
            ]
        )
    )

    prompt = render_memory_prompt(data, mode="heartbeat")

    assert "D1" in prompt
    assert "A1" in prompt
    assert "F1" not in prompt
    assert "编辑说明" not in prompt


def test_render_memory_prompt_limits_chat_items() -> None:
    """聊天态应限制注入条目数量，并给出说明。"""
    data = analyze_memory_text(
        "\n".join(
            [
                "### Durable（持久）",
                *(f"- D{i}" for i in range(25)),
                "",
                "### Active（活跃）",
                *(f"- A{i}" for i in range(10)),
            ]
        )
    )

    prompt = render_memory_prompt(data, mode="chat")

    assert "D24" not in prompt
    assert "A9" not in prompt
    assert "聊天态仅注入前" in prompt


def test_build_memory_write_warning_for_oversized_memory() -> None:
    """写入超大的 MEMORY.md 时应返回维护告警。"""
    content = "\n".join(
        [
            "### Durable（持久）",
            *(f"- {'叙事' * 40}{i}" for i in range(50)),
        ]
    )

    warning = build_memory_write_warning("MEMORY.md", content)

    assert warning is not None
    assert "MEMORY.md 写入完成" in warning
