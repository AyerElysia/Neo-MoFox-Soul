"""life_engine 对话提示词与叙事测试。"""

from __future__ import annotations

from types import SimpleNamespace

from plugins.life_engine.core.config import LifeEngineConfig
from plugins.life_engine.core.chatter import LifeChatter
from plugins.life_engine.service.core import LifeEngineService
from plugins.life_engine.service.event_builder import EventType, LifeEngineEvent
from plugins.life_engine.tools.file_tools import LifeEngineWakeDFCTool
from src.core.models.message import Message
from src.kernel.llm import LLMPayload, ROLE, Text
import pytest

def test_life_chatter_system_prompt_includes_memory_not_tool(tmp_path) -> None:
    """聊天态应共享 SOUL/MEMORY，并仅追加一个核心工具说明。"""
    (tmp_path / "SOUL.md").write_text("SOUL_CONTENT", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text(
        "\n".join(
            [
                "# 值得记住的事",
                "",
                "这里是一大段给编辑者看的说明，不该原样注入。",
                "",
                "### Durable（持久）",
                "- MEMORY_DURABLE",
                "",
                "### Active（活跃）",
                "- MEMORY_ACTIVE",
                "",
                "### Fading（待审视）",
                "- MEMORY_FADING",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "TOOL.md").write_text("TOOL_CONTENT", encoding="utf-8")

    config = LifeEngineConfig()
    config.settings.workspace_path = str(tmp_path)
    chatter = LifeChatter.__new__(LifeChatter)
    chatter.plugin = SimpleNamespace(config=config)
    prompt = chatter._build_chat_system_prompt(service=None)

    assert "SOUL_CONTENT" in prompt
    assert "MEMORY_DURABLE" in prompt
    assert "MEMORY_ACTIVE" in prompt
    assert "MEMORY_FADING" not in prompt
    assert "给编辑者看的说明" not in prompt
    assert "TOOL_CONTENT" not in prompt
    assert "action-think" in prompt
    assert "action-life_pass_and_wait" in prompt
    assert "life_send_text" in prompt
    assert "reason" in prompt


def test_life_chatter_persistent_user_prompt_excludes_dynamic_context() -> None:
    """持久 USER prompt 不应写入 inner_state/recent_context 等动态快照。"""
    chatter = LifeChatter.__new__(LifeChatter)
    chat_stream = SimpleNamespace(stream_name="Test", stream_id="stream-1")

    prompt = chatter._build_chat_user_prompt(
        chat_stream,
        unread_lines="新消息",
        history_text="历史消息",
    )

    assert "<chat_history>" in prompt
    assert "<new_messages>" in prompt
    assert "<inner_state>" not in prompt
    assert "<recent_context>" not in prompt
    assert "<runtime_assistant_context>" not in prompt


@pytest.mark.asyncio
async def test_life_chatter_dynamic_context_is_separate_snapshot() -> None:
    """动态上下文应能单独构建，用于本次请求 transient 注入。"""
    chatter = LifeChatter.__new__(LifeChatter)
    chat_stream = SimpleNamespace(stream_id="stream-1")
    service = LifeEngineService(SimpleNamespace(config=None))
    service._inner_state = SimpleNamespace(
        format_full_state_for_prompt=lambda _today: "STATE_NOW"
    )
    service._thought_manager = SimpleNamespace(
        format_for_prompt=lambda **kwargs: "THOUGHT_STREAM_NOW",
        current_revision=1,
    )
    service._event_history = [
        LifeEngineEvent(
            event_id="evt-1",
            event_type=EventType.MESSAGE,
            timestamp="2026-04-25T22:00:00+08:00",
            sequence=1,
            source="life_engine",
            source_detail="dfc",
            content="RECENT_EVENT",
            content_type="dfc_message",
            stream_id="stream-1",
            sender="dfc",
        )
    ]

    dynamic, high_water = await chatter._build_dynamic_context_text(
        chat_stream,
        service,
        runtime_context_text="RUNTIME_NOW",
    )

    assert "<life_runtime_context>" in dynamic
    assert "STATE_NOW" in dynamic
    assert "THOUGHT_STREAM_NOW" in dynamic
    assert "RECENT_EVENT" in dynamic
    assert "RUNTIME_NOW" in dynamic
    assert high_water == 1


@pytest.mark.asyncio
async def test_life_chatter_runtime_context_cursor_avoids_repeat_injection() -> None:
    service = LifeEngineService(SimpleNamespace(config=None))
    service._event_history = [
        LifeEngineEvent(
            event_id="evt-1",
            event_type=EventType.MESSAGE,
            timestamp="2026-04-25T22:00:00+08:00",
            sequence=1,
            source="life_engine",
            source_detail="dfc",
            content="OLD_LIFE_EVENT",
            content_type="dfc_message",
            stream_id="stream-1",
            sender="dfc",
        ),
        LifeEngineEvent(
            event_id="evt-2",
            event_type=EventType.MESSAGE,
            timestamp="2026-04-25T22:01:00+08:00",
            sequence=2,
            source="life_engine",
            source_detail="dfc",
            content="NEW_LIFE_EVENT",
            content_type="dfc_message",
            stream_id="stream-1",
            sender="dfc",
        ),
    ]
    chat_stream = SimpleNamespace(stream_id="stream-1")

    first_text, first_high_water = await service.build_chatter_runtime_context(chat_stream)
    await service.mark_chatter_runtime_context_seen(chat_stream.stream_id, 1)
    second_text, second_high_water = await service.build_chatter_runtime_context(chat_stream)
    await service.mark_chatter_runtime_context_seen(chat_stream.stream_id, first_high_water)
    third_text, third_high_water = await service.build_chatter_runtime_context(chat_stream)

    assert "OLD_LIFE_EVENT" in first_text
    assert "NEW_LIFE_EVENT" in first_text
    assert first_high_water == 2
    assert "OLD_LIFE_EVENT" not in second_text
    assert "NEW_LIFE_EVENT" in second_text
    assert second_high_water == 2
    assert third_text == ""
    assert third_high_water == 2


def test_life_chatter_transient_context_can_be_stripped() -> None:
    """发送前临时注入的动态上下文不应残留在持久 payload。"""
    response = SimpleNamespace(
        payloads=[LLMPayload(ROLE.USER, Text("PERSISTENT_USER"))]
    )

    LifeChatter._append_transient_context(response, "STATE_NOW")
    assert any(
        isinstance(part, Text) and "STATE_NOW" in part.text
        for part in response.payloads[0].content
    )

    LifeChatter._strip_transient_context(response)

    assert response.payloads[0].content == [response.payloads[0].content[0]]
    assert response.payloads[0].content[0].text == "PERSISTENT_USER"


def test_life_chatter_second_turn_prompt_does_not_repeat_history() -> None:
    """第二轮应只追加新消息，不重复注入 chat_history 尾巴。"""
    chatter = LifeChatter.__new__(LifeChatter)
    chat_stream = SimpleNamespace(stream_name="Test", stream_id="stream-1")

    first_turn = chatter._build_chat_user_prompt(
        chat_stream,
        unread_lines="第一轮新消息",
        history_text="首轮历史",
    )
    second_turn = chatter._build_chat_user_prompt(
        chat_stream,
        unread_lines="第二轮新消息",
        history_text="",
    )

    assert "<chat_history>" in first_turn
    assert "首轮历史" in first_turn
    assert "<chat_history>" not in second_turn
    assert "第二轮新消息" in second_turn


def test_life_chatter_history_excludes_internal_prompt_messages() -> None:
    chatter = LifeChatter.__new__(LifeChatter)
    chat_stream = SimpleNamespace(
        context=SimpleNamespace(
            history_messages=[
                Message(
                    message_id="user_1",
                    processed_plain_text="真正的聊天历史",
                    sender_name="Ayer",
                    stream_id="stream-1",
                ),
                Message(
                    message_id="proactive_opportunity_x",
                    processed_plain_text="系统主动机会",
                    sender_name="系统",
                    stream_id="stream-1",
                    is_proactive_opportunity_trigger=True,
                ),
                Message(
                    message_id="inner_monologue_x",
                    processed_plain_text="[内心独白] 我有点想他",
                    sender_name="爱莉",
                    stream_id="stream-1",
                    is_inner_monologue=True,
                ),
            ]
        )
    )

    history = chatter._build_history_text(chat_stream, max_messages=10)

    assert "真正的聊天历史" in history
    assert "系统主动机会" not in history
    assert "内心独白" not in history


def test_tell_dfc_tool_description_frames_as_runtime_mode_sync() -> None:
    """nucleus_tell_dfc 的叙事应指向运行模式同步，而不是双意识。"""
    description = LifeEngineWakeDFCTool.tool_description

    assert "同一主体的表达层" in description
    assert "不是在和另一个意识体对话" in description
    assert "信息差" in description
    assert "不用于指导" in description
