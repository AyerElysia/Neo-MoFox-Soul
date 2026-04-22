"""life_chatter think-only 约束测试。"""

from __future__ import annotations

from types import SimpleNamespace

from plugins.life_engine.core.chatter import LifeChatter
from src.kernel.llm import ROLE


class _FakeResponse:
    def __init__(self) -> None:
        self.payloads: list[object] = []

    def add_payload(self, payload: object) -> None:
        self.payloads.append(payload)


def _call(name: str) -> object:
    return SimpleNamespace(name=name)


def test_is_think_only_calls_true_for_single_think() -> None:
    assert LifeChatter._is_think_only_calls([_call("action-think")]) is True


def test_is_think_only_calls_false_for_mixed_actions() -> None:
    calls = [_call("action-think"), _call("action-life_send_text")]
    assert LifeChatter._is_think_only_calls(calls) is False


def test_append_think_only_retry_instruction_adds_system_payload() -> None:
    response = _FakeResponse()
    LifeChatter._append_think_only_retry_instruction(response)

    assert len(response.payloads) == 1
    payload = response.payloads[0]
    assert getattr(payload, "role", None) == ROLE.SYSTEM


def test_should_encourage_segment_send_for_long_single_content() -> None:
    call_args = {"content": "这是一条比较长的消息" * 8}
    assert LifeChatter._should_encourage_segment_send("action-life_send_text", call_args) is True


def test_should_not_encourage_segment_send_for_segment_array() -> None:
    call_args = {"content": ["第一段", "第二段"]}
    assert LifeChatter._should_encourage_segment_send("action-life_send_text", call_args) is False


def test_append_segment_send_retry_instruction_adds_system_payload() -> None:
    response = _FakeResponse()
    LifeChatter._append_segment_send_retry_instruction(response)

    assert len(response.payloads) == 1
    payload = response.payloads[0]
    assert getattr(payload, "role", None) == ROLE.SYSTEM


def test_append_must_reply_retry_instruction_adds_system_payload() -> None:
    response = _FakeResponse()
    LifeChatter._append_must_reply_retry_instruction(response)

    assert len(response.payloads) == 1
    payload = response.payloads[0]
    assert getattr(payload, "role", None) == ROLE.SYSTEM
