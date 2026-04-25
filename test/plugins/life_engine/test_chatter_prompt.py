"""life_engine 对话提示词与叙事测试。"""

from __future__ import annotations

from types import SimpleNamespace

from plugins.life_engine.core.config import LifeEngineConfig
from plugins.life_engine.core.chatter import LifeChatter
from plugins.life_engine.tools.file_tools import LifeEngineWakeDFCTool


def test_life_chatter_prompt_states_single_subject_runtime_modes() -> None:
    """LifeChatter 提示词应明确只有一个主体、多个运行模式。"""
    chat_stream = SimpleNamespace(
        bot_nickname="Neo",
        bot_id="bot-1",
        platform="qq",
        chat_type="private",
        stream_id="stream-1",
    )

    prompt = LifeChatter._build_fixed_chat_framework(chat_stream)

    assert "同一个主体" in prompt
    assert "运行模式" in prompt
    assert "不是两个意识体" in prompt
    assert "分段策略" in prompt
    assert "content: [\"第一段\", \"第二段\", ...]" in prompt
    assert "被明确点名/呼唤时优先回应" in prompt


def test_life_chatter_system_prompt_includes_memory_not_tool(tmp_path) -> None:
    """聊天态应共享 SOUL/MEMORY，但不注入 life 专属 TOOL 文档。"""
    (tmp_path / "SOUL.md").write_text("SOUL_CONTENT", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text("MEMORY_CONTENT", encoding="utf-8")
    (tmp_path / "TOOL.md").write_text("TOOL_CONTENT", encoding="utf-8")

    config = LifeEngineConfig()
    config.settings.workspace_path = str(tmp_path)
    chatter = LifeChatter.__new__(LifeChatter)
    chatter.plugin = SimpleNamespace(config=config)
    chat_stream = SimpleNamespace(
        bot_nickname="Neo",
        bot_id="bot-1",
        platform="qq",
        chat_type="private",
        stream_id="stream-1",
    )

    prompt = chatter._build_chat_system_prompt(chat_stream, service=None)

    assert "SOUL_CONTENT" in prompt
    assert "MEMORY_CONTENT" in prompt
    assert "TOOL_CONTENT" not in prompt


def test_tell_dfc_tool_description_frames_as_runtime_mode_sync() -> None:
    """nucleus_tell_dfc 的叙事应指向运行模式同步，而不是双意识。"""
    description = LifeEngineWakeDFCTool.tool_description

    assert "同一主体的表达层" in description
    assert "不是在和另一个意识体对话" in description
