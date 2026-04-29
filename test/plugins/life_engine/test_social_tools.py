"""life_engine 主动发起话题工具测试。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from plugins.life_engine.tools.social_tools import NucleusInitiateTopicTool


@dataclass
class _DummyContext:
    system_reminders: list[tuple[str, str]] = field(default_factory=list)

    def add_system_reminder(self, text: str, source: str = "") -> None:
        self.system_reminders.append((text, source))


@dataclass
class _DummyStream:
    stream_id: str = "stream-1"
    platform: str = "qq"
    chat_type: str = "group"
    context: _DummyContext = field(default_factory=_DummyContext)


class _DummySender:
    def __init__(self) -> None:
        self.calls: list[Any] = []

    async def send_message(self, message: Any) -> bool:
        self.calls.append(message)
        return True


@pytest.mark.asyncio
async def test_initiate_topic_uses_stream_api_and_sends_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """应通过 stream_api 取流，并用正确的 Message 发送。"""
    stream = _DummyStream()
    sender = _DummySender()

    async def _fake_get_stream(_stream_id: str) -> None:
        return None

    async def _fake_build_stream_from_database(_stream_id: str) -> _DummyStream:
        return stream

    monkeypatch.setattr(
        "plugins.life_engine.tools.social_tools.stream_api.get_stream",
        _fake_get_stream,
    )
    monkeypatch.setattr(
        "plugins.life_engine.tools.social_tools.stream_api.build_stream_from_database",
        _fake_build_stream_from_database,
    )
    monkeypatch.setattr(
        "src.core.transport.get_message_sender",
        lambda: sender,
    )

    tool = NucleusInitiateTopicTool(plugin=object())
    ok, result = await tool.execute(
        content="我刚想到一个有趣的点，想直接说出来。",
        stream_id="stream-1",
        reason="测试主动发起话题发送链路",
    )

    assert ok is True
    assert isinstance(result, str)
    assert len(sender.calls) == 1

    message = sender.calls[0]
    assert message.content == "我刚想到一个有趣的点，想直接说出来。"
    assert message.processed_plain_text == "我刚想到一个有趣的点，想直接说出来。"
    assert message.stream_id == "stream-1"
    assert message.platform == "qq"
    assert message.chat_type == "group"
    assert message.extra["source"] == "nucleus_initiate_topic"
    assert message.extra["reason"] == "测试主动发起话题发送链路"


@pytest.mark.asyncio
async def test_initiate_topic_resolves_raw_group_id_to_valid_stream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """原始群号或空平台坏流应被解析成可发送的有效群聊流。"""
    broken_stream = _DummyStream(
        stream_id="956478373",
        platform="",
        chat_type="",
    )
    resolved_stream = _DummyStream(
        stream_id="hashed-stream-1",
        platform="qq",
        chat_type="group",
    )
    sender = _DummySender()

    async def _fake_get_stream(stream_id: str) -> _DummyStream | None:
        if stream_id == "956478373":
            return broken_stream
        if stream_id == "hashed-stream-1":
            return resolved_stream
        return None

    async def _fake_build_stream_from_database(_stream_id: str) -> None:
        return None

    async def _fake_find_stream_record_by_group_id(
        group_id: str,
        *,
        preferred_platform: str = "",
    ) -> dict[str, str] | None:
        assert group_id == "956478373"
        assert preferred_platform == ""
        return {
            "stream_id": "hashed-stream-1",
            "platform": "qq",
            "group_id": "956478373",
        }

    async def _fake_safe_get_stream_info(stream_id: str) -> dict[str, str] | None:
        if stream_id == "hashed-stream-1":
            return {
                "stream_id": "hashed-stream-1",
                "platform": "qq",
                "chat_type": "group",
                "group_id": "956478373",
                "group_name": "测试群",
            }
        return None

    monkeypatch.setattr(
        "plugins.life_engine.tools.social_tools.stream_api.get_stream",
        _fake_get_stream,
    )
    monkeypatch.setattr(
        "plugins.life_engine.tools.social_tools.stream_api.build_stream_from_database",
        _fake_build_stream_from_database,
    )
    monkeypatch.setattr(
        "plugins.life_engine.tools.social_tools._find_stream_record_by_group_id",
        _fake_find_stream_record_by_group_id,
    )
    monkeypatch.setattr(
        "plugins.life_engine.tools.social_tools._safe_get_stream_info",
        _fake_safe_get_stream_info,
    )
    monkeypatch.setattr(
        "src.core.transport.get_message_sender",
        lambda: sender,
    )

    tool = NucleusInitiateTopicTool(plugin=object())
    ok, result = await tool.execute(
        content="把素材直接补到群里。",
        stream_id="956478373",
        reason="测试原始群号恢复发送链路",
    )

    assert ok is True
    assert isinstance(result, str)
    assert len(sender.calls) == 1

    message = sender.calls[0]
    assert message.stream_id == "hashed-stream-1"
    assert message.platform == "qq"
    assert message.chat_type == "group"
    assert message.extra["target_group_id"] == "956478373"
    assert message.extra["target_group_name"] == "测试群"
