"""proactive_message_plugin 消息发送归一化测试。"""

from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

PLUGIN_ROOT = Path("/root/Elysia/Neo-MoFox/plugins")
if str(PLUGIN_ROOT) not in sys.path:
    sys.path.insert(0, str(PLUGIN_ROOT))

from plugins.proactive_message_plugin.plugin import ProactiveMessagePlugin  # noqa: E402


class _FakeSender:
    """最小化消息发送器。"""

    def __init__(self) -> None:
        self.messages = []

    async def send_message(self, message) -> bool:
        self.messages.append(message)
        return True


def test_send_message_normalizes_list_content_before_persisting(monkeypatch: pytest.MonkeyPatch) -> None:
    """列表内容应拆成多条字符串消息，避免 list 进入数据库层。"""
    fake_sender = _FakeSender()
    monkeypatch.setattr(
        "src.core.transport.message_send.get_message_sender",
        lambda: fake_sender,
    )

    plugin = ProactiveMessagePlugin()
    chat_stream = SimpleNamespace(
        stream_id="sid_001",
        platform="qq",
        chat_type="private",
        bot_id="bot_001",
        bot_nickname="爱莉",
    )

    ok = asyncio.run(
        plugin._send_message(
            chat_stream,
            ["  第一段  ", "", "第二段"],
        )
    )

    assert ok is True
    assert [msg.content for msg in fake_sender.messages] == ["第一段", "第二段"]
    assert [msg.processed_plain_text for msg in fake_sender.messages] == ["第一段", "第二段"]
    assert all(isinstance(msg.content, str) for msg in fake_sender.messages)
    assert all(isinstance(msg.processed_plain_text, str) for msg in fake_sender.messages)


def test_send_message_splits_newlines_before_persisting(monkeypatch: pytest.MonkeyPatch) -> None:
    """主动消息中的换行应被拆成多条消息，而不是原样发送。"""
    fake_sender = _FakeSender()
    monkeypatch.setattr(
        "src.core.transport.message_send.get_message_sender",
        lambda: fake_sender,
    )

    plugin = ProactiveMessagePlugin()
    chat_stream = SimpleNamespace(
        stream_id="sid_001",
        platform="qq",
        chat_type="private",
        bot_id="bot_001",
        bot_nickname="爱莉",
    )

    ok = asyncio.run(
        plugin._send_message(
            chat_stream,
            "第一段\n\n第二段\\n第三段",
        )
    )

    assert ok is True
    assert [msg.content for msg in fake_sender.messages] == ["第一段", "第二段", "第三段"]


def test_chatter_mode_generates_inner_monologue_before_waking_chatter(monkeypatch: pytest.MonkeyPatch) -> None:
    """chatter 决策模式也应保留内心独白，只是不由私有独白流程直接发消息。"""
    calls: list[tuple[str, object]] = []

    async def fake_generate_inner_monologue_thought(**kwargs):
        calls.append(("generate", kwargs))
        return "等了这么久，心里有点想轻轻确认一下他的状态。"

    async def fake_inject(self, chat_stream, thought):
        calls.append(("inject", thought))

    fake_module = types.ModuleType("plugins.proactive_message_plugin.inner_monologue")
    fake_module.generate_inner_monologue_thought = fake_generate_inner_monologue_thought
    monkeypatch.setitem(sys.modules, "plugins.proactive_message_plugin.inner_monologue", fake_module)
    monkeypatch.setattr(ProactiveMessagePlugin, "_inject_inner_monologue", fake_inject)

    plugin = ProactiveMessagePlugin()
    chat_stream = SimpleNamespace(
        stream_id="sid_001",
        platform="qq",
        chat_type="private",
        bot_id="bot_001",
        bot_nickname="爱莉",
        context=SimpleNamespace(history_messages=[]),
    )

    asyncio.run(
        plugin._generate_and_inject_chatter_monologue(
            chat_stream,
            elapsed_minutes=12.0,
            user_name="Ayer",
        )
    )

    assert calls[0][0] == "generate"
    assert calls[1] == ("inject", "等了这么久，心里有点想轻轻确认一下他的状态。")
