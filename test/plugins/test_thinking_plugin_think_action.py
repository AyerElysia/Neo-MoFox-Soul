"""thinking_plugin ThinkAction 回归测试。"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from plugins.thinking_plugin.actions.think_action import ThinkAction


def _make_action(monkeypatch) -> ThinkAction:
    chat_stream = SimpleNamespace(context=SimpleNamespace(history_messages=[]))
    plugin = SimpleNamespace(components=[])
    action = ThinkAction(chat_stream=chat_stream, plugin=plugin)
    monkeypatch.setattr(ThinkAction, "_remove_trigger_reminder", lambda self: None)
    return action


def test_think_action_accepts_legacy_content_alias(monkeypatch) -> None:
    """当 thought 缺失但存在 content 时，应兼容执行。"""
    action = _make_action(monkeypatch)

    success, result = asyncio.run(
        action.execute(
            mood="温柔",
            decision="安抚对方",
            expected_response="对方会安心",
            content="我先接住对方情绪，再给出温柔回应",
        )
    )

    assert success is True
    assert "思考动作已记录" in result


def test_think_action_does_not_fail_when_thought_missing(monkeypatch) -> None:
    """当 thought/content 都缺失时，也不应抛异常中断 action 链。"""
    action = _make_action(monkeypatch)

    success, result = asyncio.run(
        action.execute(
            mood="平静",
            decision="先确认用户状态",
            expected_response="用户愿意继续交流",
        )
    )

    assert success is True
    assert "思考动作已记录" in result

