"""life_chatter think-only 约束测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from plugins.life_engine.core.chatter import LifeChatter, LifeSendTextAction
from src.kernel.llm import LLMPayload, ROLE, ToolResult


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


def test_life_send_text_normalize_splits_newlines_in_plain_text() -> None:
    result = LifeSendTextAction._normalize_content_segments("第一条\n\n第二条\r\n第三条")
    assert result == ["第一条", "第二条", "第三条"]


def test_life_send_text_normalize_splits_escaped_newlines_in_list() -> None:
    result = LifeSendTextAction._normalize_content_segments(["第一条\\n第二条", "第三条"])
    assert result == ["第一条", "第二条", "第三条"]


def test_life_send_text_rejects_placeholder_only_content() -> None:
    action = LifeSendTextAction.__new__(LifeSendTextAction)

    ok, message = asyncio.run(action.execute("..."))

    assert ok is False
    assert "占位符" in message


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


def test_append_inner_monologue_retry_instruction_adds_system_payload() -> None:
    response = _FakeResponse()
    LifeChatter._append_inner_monologue_retry_instruction(response)

    assert len(response.payloads) == 1
    payload = response.payloads[0]
    assert getattr(payload, "role", None) == ROLE.SYSTEM


def test_visible_reply_action_accepts_emoji_send() -> None:
    assert LifeChatter._is_visible_reply_action("action-life_send_text") is True
    assert LifeChatter._is_visible_reply_action("action-send_emoji_meme") is True
    assert LifeChatter._is_visible_reply_action("action-schedule_followup_message") is False


def test_requires_inner_monologue_only_for_proactive_trigger_batch() -> None:
    proactive = SimpleNamespace(
        is_proactive_opportunity_trigger=True,
        is_proactive_followup_trigger=False,
    )
    followup = SimpleNamespace(
        is_proactive_opportunity_trigger=False,
        is_proactive_followup_trigger=True,
    )
    real_user = SimpleNamespace(
        is_proactive_opportunity_trigger=False,
        is_proactive_followup_trigger=False,
    )

    assert LifeChatter._requires_inner_monologue_for_unread_batch([proactive]) is True
    assert LifeChatter._requires_inner_monologue_for_unread_batch([followup]) is True
    assert LifeChatter._requires_inner_monologue_for_unread_batch([proactive, followup]) is True
    assert LifeChatter._requires_inner_monologue_for_unread_batch([real_user]) is False
    assert LifeChatter._requires_inner_monologue_for_unread_batch([proactive, real_user]) is False


def test_should_force_reply_only_for_real_external_messages() -> None:
    proactive = SimpleNamespace(
        is_proactive_opportunity_trigger=True,
        is_proactive_followup_trigger=False,
        sender_role="other",
    )
    real_user = SimpleNamespace(
        is_proactive_opportunity_trigger=False,
        is_proactive_followup_trigger=False,
        sender_role="other",
    )

    assert LifeChatter._should_force_reply_for_unread_batch([proactive]) is False
    assert LifeChatter._should_force_reply_for_unread_batch([real_user]) is True


def test_compact_successful_tool_result_only_targets_low_information_actions() -> None:
    assert LifeChatter._should_compact_successful_tool_result("action-record_inner_monologue") is True
    assert LifeChatter._should_compact_successful_tool_result("action-life_send_text") is True
    assert LifeChatter._should_compact_successful_tool_result("action-send_emoji_meme") is True
    assert LifeChatter._should_compact_successful_tool_result("action-think") is True
    assert LifeChatter._should_compact_successful_tool_result("search_life_memory") is False
    assert LifeChatter._should_compact_successful_tool_result("agent-life_memory_explorer") is False
    assert LifeChatter._should_compact_successful_tool_result("nucleus_search_memory") is False
    assert LifeChatter._should_compact_successful_tool_result("fetch_life_memory") is False


def test_compact_successful_tool_result_preserves_other_tool_results() -> None:
    response = _FakeResponse()
    response.add_payload(
        LLMPayload(
            ROLE.TOOL_RESULT,
            [
                ToolResult(value="已发送3条消息: hello", call_id="send-1", name="action-life_send_text"),
                ToolResult(value="记忆检索结果正文", call_id="memory-1", name="agent-life_memory_explorer"),
            ],
        )
    )

    LifeChatter._compact_successful_tool_result(response, "send-1")

    payload = response.payloads[0]
    send_result, memory_result = payload.content
    assert send_result.value == "ok"
    assert memory_result.value == "记忆检索结果正文"
