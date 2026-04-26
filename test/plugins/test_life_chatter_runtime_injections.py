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
        service=None,
        unread_lines="用户: hi",
        runtime_context_text=runtime_context,
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


def test_life_chatter_user_prompt_tells_model_to_use_chat_history_for_references() -> None:
    chatter = LifeChatter.__new__(LifeChatter)
    prompt = chatter._build_fixed_chat_framework(
        SimpleNamespace(
            bot_nickname="爱莉希雅",
            platform="qq",
            chat_type="private",
            bot_id="bot",
        )
    )

    assert "<chat_history>" in prompt
    assert "必须先结合 <chat_history> 和 <new_messages>" in prompt
    assert "fetch_chat_history" in prompt
