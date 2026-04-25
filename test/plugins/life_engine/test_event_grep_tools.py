"""life event grep tool tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from plugins.life_engine.service.core import LifeEngineService
from plugins.life_engine.service.event_builder import EventType, LifeEngineEvent
from plugins.life_engine.tools.event_grep_tools import (
    LifeChatterGrepEventsTool,
    LifeEngineGrepEventsTool,
    grep_life_events,
)


def _event(
    sequence: int,
    content: str,
    *,
    stream_id: str = "s1",
    event_type: EventType = EventType.MESSAGE,
    tool_name: str | None = None,
) -> LifeEngineEvent:
    return LifeEngineEvent(
        event_id=f"evt-{sequence}",
        event_type=event_type,
        timestamp=f"2026-04-25T00:0{sequence}:00+08:00",
        sequence=sequence,
        source="qq" if stream_id else "life_engine",
        source_detail=f"stream={stream_id}",
        content=content,
        sender="user",
        chat_type="private",
        stream_id=stream_id,
        tool_name=tool_name,
    )


@pytest.fixture(autouse=True)
def _reset_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    import plugins.life_engine.service.registry as registry

    monkeypatch.setattr(registry, "_life_engine_registry", registry.ServiceRegistry())


@pytest.mark.asyncio
async def test_grep_life_events_searches_history_and_pending() -> None:
    service = LifeEngineService(SimpleNamespace(config=None))
    service._event_history = [
        _event(1, "我们刚才聊了天气"),
        _event(2, "调用天气工具", event_type=EventType.TOOL_CALL, tool_name="weather"),
    ]
    service._pending_events = [_event(3, "pending 里提到咖啡")]

    import plugins.life_engine.service.registry as registry

    registry.register_life_engine_service(service)

    result = await grep_life_events(query="咖啡")

    assert result["stats"]["scanned_events"] == 3
    assert result["stats"]["matched_events"] == 1
    assert result["matches"][0]["event"]["event_id"] == "evt-3"


@pytest.mark.asyncio
async def test_life_chatter_grep_defaults_to_current_stream() -> None:
    service = LifeEngineService(SimpleNamespace(config=None))
    service._event_history = [
        _event(1, "同一个关键词", stream_id="s1"),
        _event(2, "同一个关键词", stream_id="s2"),
    ]

    import plugins.life_engine.service.registry as registry

    registry.register_life_engine_service(service)

    tool = LifeChatterGrepEventsTool(plugin=SimpleNamespace())
    tool.chat_stream = SimpleNamespace(stream_id="s1")

    ok, payload = await tool.execute(query="关键词")

    assert ok is True
    assert isinstance(payload, dict)
    assert payload["stream_ids"] == ["s1"]
    assert payload["stats"]["matched_events"] == 1
    assert payload["matches"][0]["event"]["stream_id"] == "s1"


@pytest.mark.asyncio
async def test_life_chatter_grep_context_stays_in_current_stream() -> None:
    service = LifeEngineService(SimpleNamespace(config=None))
    service._event_history = [
        _event(1, "当前流前文", stream_id="s1"),
        _event(2, "其它流前文", stream_id="s2"),
        _event(3, "目标关键词", stream_id="s1"),
        _event(4, "其它流后文", stream_id="s2"),
        _event(5, "当前流后文", stream_id="s1"),
    ]

    import plugins.life_engine.service.registry as registry

    registry.register_life_engine_service(service)

    tool = LifeChatterGrepEventsTool(plugin=SimpleNamespace())
    tool.chat_stream = SimpleNamespace(stream_id="s1")

    ok, payload = await tool.execute(query="目标", context_before=2, context_after=2)

    assert ok is True
    assert isinstance(payload, dict)
    match = payload["matches"][0]
    assert [item["stream_id"] for item in match["context_before"]] == ["s1"]
    assert [item["stream_id"] for item in match["context_after"]] == ["s1"]


@pytest.mark.asyncio
async def test_life_engine_grep_can_search_tool_name() -> None:
    service = LifeEngineService(SimpleNamespace(config=None))
    service._event_history = [
        _event(1, "调用工具", stream_id="", event_type=EventType.TOOL_CALL, tool_name="nucleus_web_search"),
    ]

    import plugins.life_engine.service.registry as registry

    registry.register_life_engine_service(service)

    tool = LifeEngineGrepEventsTool(plugin=SimpleNamespace())
    ok, payload = await tool.execute(query="web_search", fields=["tool_name"])

    assert ok is True
    assert isinstance(payload, dict)
    assert payload["stats"]["matched_events"] == 1
    assert payload["matches"][0]["event"]["tool_name"] == "nucleus_web_search"
