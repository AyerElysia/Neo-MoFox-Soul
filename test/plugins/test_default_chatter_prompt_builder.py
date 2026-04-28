"""default_chatter.prompt_builder 模块测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from plugins.default_chatter.config import DefaultChatterConfig
from plugins.default_chatter.prompt_builder import DefaultChatterPromptBuilder
from src.core.models.stream import ChatStream


def test_get_mode_returns_configured_value() -> None:
    """应返回配置中的 mode。"""
    config = DefaultChatterConfig.from_dict({"plugin": {"mode": "classical"}})
    assert DefaultChatterPromptBuilder.get_mode(config) == "classical"


def test_get_mode_fallbacks_to_enhanced() -> None:
    """配置不可用时应回退为 enhanced。"""
    assert DefaultChatterPromptBuilder.get_mode(None) == "enhanced"


def test_build_negative_behaviors_extra_disabled_returns_empty() -> None:
    """未启用强化时应返回空字符串。"""
    config = DefaultChatterConfig.from_dict(
        {"plugin": {"reinforce_negative_behaviors": False}}
    )
    assert DefaultChatterPromptBuilder.build_negative_behaviors_extra(config) == ""


def test_build_negative_behaviors_extra_enabled_returns_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """启用强化且存在约束时应返回提醒文本。"""
    config = DefaultChatterConfig.from_dict(
        {"plugin": {"reinforce_negative_behaviors": True}}
    )
    monkeypatch.setattr(
        "plugins.default_chatter.prompt_builder.get_core_config",
        lambda: SimpleNamespace(
            personality=SimpleNamespace(negative_behaviors=["不要骂人", "不要编造"])
        ),
    )

    result = DefaultChatterPromptBuilder.build_negative_behaviors_extra(config)

    assert "行为提醒" in result
    assert "不要骂人" in result
    assert "不要编造" in result


def test_build_system_prompt_uses_private_theme(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """私聊场景应使用 private theme guide。"""
    config = DefaultChatterConfig.from_dict(
        {"plugin": {"theme_guide": {"private": "PRIVATE_THEME", "group": "GROUP_THEME"}}}
    )
    stream = ChatStream(
        stream_id="s1",
        platform="qq",
        chat_type="private",
        bot_id="100",
        bot_nickname="fox",
    )

    class _FakeTemplate:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def set(self, key: str, value: str):
            self.values[key] = value
            return self

        async def build(self) -> str:
            return f"theme={self.values.get('theme_guide', '')}"

    fake_template = _FakeTemplate()
    monkeypatch.setattr(
        "plugins.default_chatter.prompt_builder.get_prompt_manager",
        lambda: SimpleNamespace(
            get_template=lambda _name: fake_template,
        ),
    )

    prompt = asyncio.run(
        DefaultChatterPromptBuilder.build_system_prompt(config, stream)
    )

    assert prompt == "theme=PRIVATE_THEME"


def test_build_runtime_context_extra_uses_private_theme() -> None:
    """动态会话上下文应包含 private 场景引导。"""
    config = DefaultChatterConfig.from_dict(
        {"plugin": {"theme_guide": {"private": "PRIVATE_THEME", "group": "GROUP_THEME"}}}
    )
    stream = ChatStream(
        stream_id="s1",
        platform="qq",
        chat_type="private",
        bot_id="100",
        bot_nickname="fox",
    )

    extra = DefaultChatterPromptBuilder.build_runtime_context_extra(config, stream)

    assert "平台：qq" in extra
    assert "聊天类型：private" in extra
    assert "PRIVATE_THEME" in extra


def test_build_runtime_context_extra_uses_group_theme() -> None:
    """动态会话上下文应包含 group 场景引导。"""
    config = DefaultChatterConfig.from_dict(
        {"plugin": {"theme_guide": {"private": "PRIVATE_THEME", "group": "GROUP_THEME"}}}
    )
    stream = ChatStream(
        stream_id="s2",
        platform="qq",
        chat_type="group",
        bot_id="101",
        bot_nickname="fox",
    )

    extra = DefaultChatterPromptBuilder.build_runtime_context_extra(config, stream)

    assert "聊天类型：group" in extra
    assert "GROUP_THEME" in extra


def test_build_runtime_context_extra_discuss_without_theme() -> None:
    """非 private/group 场景默认不追加主题引导。"""
    config = DefaultChatterConfig.from_dict(
        {"plugin": {"theme_guide": {"private": "PRIVATE_THEME", "group": "GROUP_THEME"}}}
    )
    stream = ChatStream(
        stream_id="s3",
        platform="qq",
        chat_type="discuss",
        bot_id="102",
        bot_nickname="fox",
    )

    extra = DefaultChatterPromptBuilder.build_runtime_context_extra(config, stream)

    assert "聊天类型：discuss" in extra
    assert "PRIVATE_THEME" not in extra
    assert "GROUP_THEME" not in extra


def test_build_system_prompt_prefers_bot_name_for_platform_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """系统提示词应优先使用适配器返回的 bot_name 填充平台昵称。"""
    stream = ChatStream(
        stream_id="s2",
        platform="qq",
        chat_type="group",
        bot_id="100",
        bot_nickname="fox-stream",
    )

    class _FakeTemplate:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def set(self, key: str, value: str):
            self.values[key] = value
            return self

        async def build(self) -> str:
            return (
                f"platform_name={self.values.get('platform_name', '')}|"
                f"platform_id={self.values.get('platform_id', '')}"
            )

    fake_template = _FakeTemplate()
    monkeypatch.setattr(
        "plugins.default_chatter.prompt_builder.get_prompt_manager",
        lambda: SimpleNamespace(
            get_template=lambda _name: fake_template,
        ),
    )
    async def _fake_get_bot_info(_platform: str) -> dict[str, str]:
        return {"bot_id": "3602291932", "bot_name": "MoFox"}

    monkeypatch.setattr(
        "src.app.plugin_system.api.adapter_api.get_bot_info_by_platform",
        _fake_get_bot_info,
    )

    prompt = asyncio.run(
        DefaultChatterPromptBuilder.build_system_prompt(None, stream)
    )

    assert prompt == "platform_name=MoFox|platform_id=3602291932"


def test_build_system_prompt_falls_back_to_stream_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """系统提示词在 bot_name 缺失时应回退到 chat_stream。"""
    stream = ChatStream(
        stream_id="s3",
        platform="qq",
        chat_type="group",
        bot_id="stream-id",
        bot_nickname="stream-name",
    )

    class _FakeTemplate:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def set(self, key: str, value: str):
            self.values[key] = value
            return self

        async def build(self) -> str:
            return (
                f"platform_name={self.values.get('platform_name', '')}|"
                f"platform_id={self.values.get('platform_id', '')}"
            )

    fake_template = _FakeTemplate()
    monkeypatch.setattr(
        "plugins.default_chatter.prompt_builder.get_prompt_manager",
        lambda: SimpleNamespace(
            get_template=lambda _name: fake_template,
        ),
    )
    async def _fake_get_bot_info(_platform: str) -> dict[str, str]:
        return {}

    monkeypatch.setattr(
        "src.app.plugin_system.api.adapter_api.get_bot_info_by_platform",
        _fake_get_bot_info,
    )

    prompt = asyncio.run(
        DefaultChatterPromptBuilder.build_system_prompt(None, stream)
    )

    assert prompt == "platform_name=stream-name|platform_id=stream-id"


def test_build_user_prompt_injects_runtime_platform_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """用户提示词应注入每轮动态时间与平台身份信息。"""
    stream = ChatStream(
        stream_id="s_user",
        platform="qq",
        chat_type="group",
        bot_id="stream-id",
        bot_nickname="stream-name",
    )

    class _FakeTemplate:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def set(self, key: str, value: str):
            self.values[key] = value
            return self

        async def build(self) -> str:
            return (
                f"time={bool(self.values.get('current_time'))}|"
                f"platform={self.values.get('platform', '')}|"
                f"chat_type={self.values.get('chat_type', '')}|"
                f"platform_name={self.values.get('platform_name', '')}|"
                f"platform_id={self.values.get('platform_id', '')}"
            )

    fake_template = _FakeTemplate()
    monkeypatch.setattr(
        "plugins.default_chatter.prompt_builder.get_prompt_manager",
        lambda: SimpleNamespace(get_template=lambda _name: fake_template),
    )

    async def _fake_get_bot_info(_platform: str) -> dict[str, str]:
        return {"bot_id": "3602291932", "bot_name": "MoFox"}

    monkeypatch.setattr(
        "src.app.plugin_system.api.adapter_api.get_bot_info_by_platform",
        _fake_get_bot_info,
    )

    prompt = asyncio.run(
        DefaultChatterPromptBuilder.build_user_prompt(
            stream,
            history_text="history",
            unread_lines="unread",
        )
    )

    assert prompt == (
        "time=True|platform=qq|chat_type=group|"
        "platform_name=MoFox|platform_id=3602291932"
    )


def test_build_system_prompt_skips_bot_lookup_when_platform_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """platform 为空时不应调用适配器查询，避免直接抛错。"""
    stream = ChatStream(
        stream_id="s4",
        platform="",
        chat_type="group",
        bot_id="stream-id",
        bot_nickname="stream-name",
    )

    class _FakeTemplate:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def set(self, key: str, value: str):
            self.values[key] = value
            return self

        async def build(self) -> str:
            return (
                f"platform_name={self.values.get('platform_name', '')}|"
                f"platform_id={self.values.get('platform_id', '')}"
            )

    fake_template = _FakeTemplate()
    monkeypatch.setattr(
        "plugins.default_chatter.prompt_builder.get_prompt_manager",
        lambda: SimpleNamespace(
            get_template=lambda _name: fake_template,
        ),
    )

    def _should_not_be_called(_platform: str) -> dict[str, str]:
        raise AssertionError("platform 为空时不应查询 bot_info")

    monkeypatch.setattr(
        "src.app.plugin_system.api.adapter_api.get_bot_info_by_platform",
        _should_not_be_called,
    )

    prompt = asyncio.run(
        DefaultChatterPromptBuilder.build_system_prompt(None, stream)
    )

    assert prompt == "platform_name=stream-name|platform_id=stream-id"


def test_build_system_prompt_always_injects_all_persona_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """系统提示词应始终注入所有人设字段。"""
    config = DefaultChatterConfig.from_dict({})
    stream = ChatStream(
        stream_id="persona-disabled-stream",
        platform="qq",
        chat_type="private",
        bot_id="100",
        bot_nickname="fox",
    )

    class _FakeTemplate:
        def __init__(self) -> None:
            self.values: dict[str, str] = {}

        def set(self, key: str, value: str):
            self.values[key] = value
            return self

        async def build(self) -> str:
            return (
                f"core={self.values.get('personality_core', '')}|"
                f"side={self.values.get('personality_side', '')}|"
                f"style={self.values.get('reply_style', '')}|"
                f"identity={self.values.get('identity', '')}|"
                f"story={self.values.get('background_story', '')}"
            )

    fake_template = _FakeTemplate()
    monkeypatch.setattr(
        "plugins.default_chatter.prompt_builder.get_prompt_manager",
        lambda: SimpleNamespace(get_template=lambda _name: fake_template),
    )
    monkeypatch.setattr(
        "plugins.default_chatter.prompt_builder.get_core_config",
        lambda: SimpleNamespace(
            personality=SimpleNamespace(
                personality_core="CORE",
                personality_side="SIDE",
                reply_style="STYLE",
                identity="IDENTITY",
                background_story="STORY",
            )
        ),
    )

    prompt = asyncio.run(
        DefaultChatterPromptBuilder.build_system_prompt(config, stream)
    )

    assert prompt == "core=CORE|side=SIDE|style=STYLE|identity=IDENTITY|story=STORY"
