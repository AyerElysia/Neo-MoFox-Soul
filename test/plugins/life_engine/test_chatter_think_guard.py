"""life_chatter think-only 约束测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from plugins.life_engine.core.chatter import LifeChatter, LifeSendTextAction
from plugins.life_engine.core.tool_parallel import (
    is_life_tool_call_parallel_safe,
    iter_life_tool_call_batches,
)
from src.core.components.base.chatter import BaseChatter
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


def test_life_tool_parallel_policy_only_allows_safe_reads() -> None:
    assert is_life_tool_call_parallel_safe(
        SimpleNamespace(name="nucleus_read_file", args={})
    )
    assert is_life_tool_call_parallel_safe(
        SimpleNamespace(name="nucleus_manage_thought_stream", args={"action": "list"})
    )
    assert not is_life_tool_call_parallel_safe(
        SimpleNamespace(name="nucleus_manage_thought_stream", args={"action": "advance"})
    )
    assert not is_life_tool_call_parallel_safe(
        SimpleNamespace(name="nucleus_search_memory", args={"query": "x"})
    )
    assert not is_life_tool_call_parallel_safe(
        SimpleNamespace(name="nucleus_write_file", args={})
    )
    assert not is_life_tool_call_parallel_safe(
        SimpleNamespace(name="action-life_send_text", args={})
    )


def test_life_tool_parallel_batches_only_consecutive_safe_calls() -> None:
    calls = [
        SimpleNamespace(name="nucleus_read_file", args={}),
        SimpleNamespace(name="nucleus_web_search", args={}),
        SimpleNamespace(name="nucleus_write_file", args={}),
        SimpleNamespace(name="nucleus_list_files", args={}),
        SimpleNamespace(name="action-life_send_text", args={}),
    ]

    batches = [
        ([call.name for call in batch], can_parallel)
        for batch, can_parallel in iter_life_tool_call_batches(calls)
    ]

    assert batches == [
        (["nucleus_read_file", "nucleus_web_search"], True),
        (["nucleus_write_file"], False),
        (["nucleus_list_files"], True),
        (["action-life_send_text"], False),
    ]


@pytest.mark.asyncio
async def test_life_chatter_run_tool_call_accepts_single_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chatter = LifeChatter.__new__(LifeChatter)
    response = _FakeResponse()
    response.add_payload(
        LLMPayload(
            ROLE.TOOL_RESULT,
            [ToolResult(value="已发送", call_id="send-1", name="action-life_send_text")],
        )
    )
    captured: dict[str, object] = {}
    call = SimpleNamespace(id="send-1", name="action-life_send_text", args={})

    async def _fake_base_run_tool_call(
        self: BaseChatter,
        calls: object,
        _response: object,
        _usable_map: object,
        _trigger_msg: object,
    ) -> list[tuple[bool, bool]]:
        captured["calls"] = calls
        return [(True, True)]

    monkeypatch.setattr(BaseChatter, "run_tool_call", _fake_base_run_tool_call)

    appended, success = await chatter.run_tool_call(
        call,
        response,
        usable_map={},
        trigger_msg=None,
    )

    assert (appended, success) == (True, True)
    assert captured["calls"] == [call]
    payload = response.payloads[0]
    assert payload.content[0].value == "ok"


@pytest.mark.asyncio
async def test_life_chatter_run_tool_call_preserves_batch_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chatter = LifeChatter.__new__(LifeChatter)
    response = _FakeResponse()
    calls = [
        SimpleNamespace(id="send-1", name="action-life_send_text", args={}),
        SimpleNamespace(id="memory-1", name="search_life_memory", args={}),
    ]
    captured: dict[str, object] = {}

    async def _fake_base_run_tool_call(
        self: BaseChatter,
        incoming_calls: object,
        _response: object,
        _usable_map: object,
        _trigger_msg: object,
    ) -> list[tuple[bool, bool]]:
        captured["calls"] = incoming_calls
        return [(True, True), (True, True)]

    monkeypatch.setattr(BaseChatter, "run_tool_call", _fake_base_run_tool_call)

    results = await chatter.run_tool_call(
        calls,
        response,
        usable_map={},
        trigger_msg=None,
    )

    assert results == [(True, True), (True, True)]
    assert captured["calls"] == calls
