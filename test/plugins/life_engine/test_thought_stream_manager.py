from __future__ import annotations

from plugins.life_engine.streams.manager import ThoughtStreamManager


def test_advance_reactivates_dormant_stream(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    stream = manager.create("继续想上下文管理")
    manager.retire(stream.id, new_status="dormant")

    ok, message = manager.advance(stream.id, "想到可以避免重复注入。")

    assert ok is True
    assert "已推进思考流" in message
    assert manager.get(stream.id).status == "active"
    assert manager.get(stream.id).advance_count == 1


def test_advance_rejects_completed_stream(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    stream = manager.create("已经结束的想法")
    manager.retire(stream.id, new_status="completed")

    ok, message = manager.advance(stream.id, "不应该继续推进。")

    assert ok is False
    assert "已完成" in message
    assert manager.get(stream.id).status == "completed"
    assert manager.get(stream.id).advance_count == 0
