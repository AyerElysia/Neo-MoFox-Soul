"""life_chatter runtime assistant injection tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from plugins.life_engine.core.chatter import (
    LifeChatter,
    consume_runtime_assistant_injections,
    push_runtime_assistant_injection,
)
from src.kernel.llm import LLMPayload, ROLE, Text


class _FakeResponse:
    def __init__(self, payloads: list[LLMPayload] | None = None) -> None:
        self.payloads = payloads or []

    def add_payload(self, payload: LLMPayload) -> None:
        self.payloads.append(payload)


def _payload_text(payload: Any) -> str:
    content = getattr(payload, "content", [])
    if isinstance(content, list) and content:
        part = content[0]
        return str(getattr(part, "text", part))
    return str(content)


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

    assert chatter._inject_runtime_assistant_payloads(response, stream) == 1
    assert response.payloads[-1].role == ROLE.ASSISTANT
    assert _payload_text(response.payloads[-1]) == "[内心独白] 等一等再说"


def test_life_chatter_keeps_runtime_context_for_first_user_prompt() -> None:
    stream = SimpleNamespace(stream_id="stream_without_user")
    response = _FakeResponse([LLMPayload(ROLE.SYSTEM, Text("sys"))])
    chatter = LifeChatter.__new__(LifeChatter)

    push_runtime_assistant_injection(stream.stream_id, "[内心独白] 先记下来")

    assert chatter._inject_runtime_assistant_payloads(response, stream) == 0
    runtime_context = chatter._format_runtime_context_text(
        chatter._consume_runtime_assistant_context(stream)
    )

    prompt = chatter._build_chat_user_prompt(
        SimpleNamespace(stream_id=stream.stream_id, stream_name="test"),
        service=None,
        unread_lines="用户: hi",
        runtime_context_text=runtime_context,
    )

    assert "<runtime_assistant_context>" in prompt
    assert "[内心独白] 先记下来" in prompt
    assert consume_runtime_assistant_injections(stream.stream_id) == []
