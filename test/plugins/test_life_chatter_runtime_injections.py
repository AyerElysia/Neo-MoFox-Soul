"""life_chatter runtime assistant injection tests."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from plugins.life_engine.core.config import LifeEngineConfig
from plugins.life_engine.core.chatter import (
    LifeChatter,
    consume_runtime_assistant_injections,
    push_runtime_assistant_injection,
)
from src.core.models.message import Message, MessageType
from src.kernel.llm import LLMPayload, ROLE, Text


class _FakeResponse:
    def __init__(self, payloads: list[LLMPayload] | None = None) -> None:
        self.payloads = payloads or []

    def add_payload(self, payload: LLMPayload) -> None:
        self.payloads.append(payload)


def _payload_text(payload: Any) -> str:
    content = getattr(payload, "content", [])
    if isinstance(content, list) and content:
        return "\n".join(str(getattr(part, "text", part)) for part in content)
    return str(content)


def _message(index: int, content: str) -> Message:
    return Message(
        message_id=f"m{index}",
        time=1_700_000_000 + index,
        content=content,
        processed_plain_text=content,
        message_type=MessageType.TEXT,
        sender_id=f"u{index}",
        sender_name=f"user{index}",
        sender_role="user",
        platform="qq",
        chat_type="private",
        stream_id="stream_history",
    )


def test_life_chatter_runtime_queue_is_per_stream() -> None:
    push_runtime_assistant_injection("stream_a", "[内心独白] A")
    push_runtime_assistant_injection("stream_b", "[内心独白] B")

    assert consume_runtime_assistant_injections("stream_a") == ["[内心独白] A"]
    assert consume_runtime_assistant_injections("stream_a") == []
    assert consume_runtime_assistant_injections("stream_b") == ["[内心独白] B"]


def test_life_chatter_injects_runtime_context_after_existing_user_payload() -> None:
    stream = SimpleNamespace(stream_id="stream_with_user")
    response = _FakeResponse([LLMPayload(ROLE.USER, Text("previous user"))])
    chatter = LifeChatter.__new__(LifeChatter)

    push_runtime_assistant_injection(stream.stream_id, "[内心独白] 等一等再说")

    runtime_context = chatter._format_runtime_context_text(
        chatter._consume_runtime_assistant_context(stream)
    )
    dynamic_context, high_water = asyncio.run(
        chatter._build_dynamic_context_text(
            stream,
            service=None,
            runtime_context_text=runtime_context,
        )
    )

    assert high_water == 0
    assert "[内心独白] 等一等再说" in dynamic_context

    chatter._append_transient_context(response, dynamic_context)
    assert response.payloads[-1].role == ROLE.USER
    assert "<transient_life_context>" in _payload_text(response.payloads[-1])
    assert "[内心独白] 等一等再说" in _payload_text(response.payloads[-1])


def test_life_chatter_keeps_runtime_context_for_first_user_prompt() -> None:
    stream = SimpleNamespace(stream_id="stream_without_user")
    response = _FakeResponse([LLMPayload(ROLE.SYSTEM, Text("sys"))])
    chatter = LifeChatter.__new__(LifeChatter)

    push_runtime_assistant_injection(stream.stream_id, "[内心独白] 先记下来")

    runtime_context = chatter._format_runtime_context_text(
        chatter._consume_runtime_assistant_context(stream)
    )
    dynamic_context, high_water = asyncio.run(
        chatter._build_dynamic_context_text(
            stream,
            service=None,
            runtime_context_text=runtime_context,
        )
    )

    prompt = chatter._build_chat_user_prompt(
        SimpleNamespace(stream_id=stream.stream_id, stream_name="test"),
        unread_lines="用户: hi",
    )

    assert high_water == 0
    assert "[内心独白] 先记下来" in dynamic_context
    assert "<life_runtime_context>" in dynamic_context
    assert "[内心独白] 先记下来" not in prompt

    chatter._append_transient_context(response, dynamic_context)
    assert _payload_text(response.payloads[-1]) == "sys"
    assert consume_runtime_assistant_injections(stream.stream_id) == []


def test_life_chatter_history_text_can_keep_short_tail_after_first_merge() -> None:
    stream = SimpleNamespace(
        context=SimpleNamespace(
            history_messages=[
                _message(1, "第一条旧消息"),
                _message(2, "第二条旧消息"),
                _message(3, "刚刚真正讨论的重点"),
                _message(4, "上一句追问"),
            ]
        )
    )

    full_history = LifeChatter._build_history_text(stream, max_messages=None)
    tail_history = LifeChatter._build_history_text(stream, max_messages=2)

    assert "第一条旧消息" in full_history
    assert "刚刚真正讨论的重点" in tail_history
    assert "上一句追问" in tail_history
    assert "第二条旧消息" not in tail_history


def test_life_chatter_initial_history_limit_reads_config() -> None:
    config = LifeEngineConfig()
    config.chatter.initial_history_messages = 4
    chatter = LifeChatter.__new__(LifeChatter)
    chatter.plugin = SimpleNamespace(config=config)

    assert chatter._get_initial_history_message_limit() == 4


def test_life_chatter_initial_history_limit_supports_legacy_field() -> None:
    config = LifeEngineConfig()
    config.chatter.initial_history_messages = 30
    config.chatter.recent_history_tail_messages = 6
    chatter = LifeChatter.__new__(LifeChatter)
    chatter.plugin = SimpleNamespace(config=config)

    assert chatter._get_initial_history_message_limit() == 6

# ---- 新增：salient tail 过滤 + thought delta cursor 去重 -------------------


import pytest  # noqa: E402

from plugins.life_engine.service.core import LifeEngineService  # noqa: E402
from plugins.life_engine.service.event_builder import (  # noqa: E402
    EventType,
    LifeEngineEvent,
)


def _make_event(seq: int, **kwargs) -> LifeEngineEvent:
    base = dict(
        event_id=f"e{seq}",
        event_type=EventType.HEARTBEAT,
        timestamp="2026-04-25T22:00:00+08:00",
        sequence=seq,
        source="life_engine",
        source_detail="hb",
        content=f"content-{seq}",
    )
    base.update(kwargs)
    return LifeEngineEvent(**base)


@pytest.mark.asyncio
async def test_build_chatter_runtime_filters_plain_heartbeats() -> None:
    """普通 HEARTBEAT 不应进入 salient tail。"""
    service = LifeEngineService(SimpleNamespace(config=None))
    chat = SimpleNamespace(stream_id="stream-x")
    service._event_history = [
        _make_event(1, content="HB_NOISE", heartbeat_index=1),
        _make_event(
            2,
            event_type=EventType.AGENT_RESULT,
            content="AGENT_DONE",
            tool_name="planner",
            tool_success=True,
            source_detail="agent",
        ),
        _make_event(
            3,
            event_type=EventType.TOOL_CALL,
            content="tool_args_blob",
            tool_name="search",
            source_detail="tool",
        ),
    ]
    text, hw = await service.build_chatter_runtime_context(chat)
    assert "HB_NOISE" not in text
    assert "tool_args_blob" not in text
    assert "AGENT_DONE" in text
    assert "### 最近关键活动" in text
    assert hw == 2


@pytest.mark.asyncio
async def test_build_chatter_runtime_thought_delta_cursor_dedup() -> None:
    """同一 stream 第二次 build 不应再在 thought 块带 🔄 delta 标记。"""
    service = LifeEngineService(SimpleNamespace(config=None))
    chat = SimpleNamespace(stream_id="stream-d")
    service._thought_manager = SimpleNamespace(
        format_for_prompt=lambda **kw: (
            "🔄 (刚推进) idea-1" if kw.get("revision_cursor", 0) < 5 else "idea-1"
        ),
        current_revision=5,
    )
    service._event_history = []

    first, _ = await service.build_chatter_runtime_context(chat)
    second, _ = await service.build_chatter_runtime_context(chat)

    assert "🔄" in first
    assert "🔄" not in second
