"""default_chatter 工具能力校准提醒测试。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from plugins.default_chatter.runners import (
    _build_tool_capability_reminder,
    _inject_tool_capability_reminder,
)
from src.kernel.llm import ROLE


class _FakeRegistry:
    def __init__(self, names: list[str]) -> None:
        self._names = names

    def get_all_names(self) -> list[str]:
        return list(self._names)


class _FakeResponse:
    def __init__(self) -> None:
        self.payloads: list[Any] = []

    def add_payload(self, payload: Any) -> None:
        self.payloads.append(payload)


def test_build_tool_capability_reminder_for_web_tools() -> None:
    """挂载联网工具时应生成能力校准提醒。"""
    registry = _FakeRegistry(
        ["action-send_text", "tool-nucleus_web_search", "tool-nucleus_browser_fetch"]
    )
    reminder = _build_tool_capability_reminder(registry)
    assert "tool-nucleus_web_search" in reminder
    assert "tool-nucleus_browser_fetch" in reminder
    assert "应明确回答“有”" in reminder


def test_build_tool_capability_reminder_empty_without_web_tools() -> None:
    """未挂载联网工具时不应注入该提醒。"""
    registry = _FakeRegistry(["action-send_text", "tool-message_nucleus"])
    reminder = _build_tool_capability_reminder(registry)
    assert reminder == ""


def test_inject_tool_capability_reminder_adds_system_payload() -> None:
    """注入提醒时应追加 SYSTEM payload。"""
    registry = _FakeRegistry(["tool-nucleus_web_search"])
    response = _FakeResponse()
    logger = SimpleNamespace(debug=lambda *_args, **_kwargs: None)

    _inject_tool_capability_reminder(response, registry, logger)

    assert len(response.payloads) == 1
    payload = response.payloads[0]
    assert getattr(payload, "role", None) == ROLE.SYSTEM
    assert "tool-nucleus_web_search" in str(getattr(payload, "content", ""))
