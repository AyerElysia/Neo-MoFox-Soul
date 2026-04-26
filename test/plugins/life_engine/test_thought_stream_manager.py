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


def test_advance_reactivates_dormant_stream_without_exceeding_active_limit(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path), max_active=2)
    first = manager.create("第一条")
    manager.create("第二条")
    manager.create("第三条")

    assert manager.get(first.id).status == "dormant"
    assert len(manager.list_active()) == 2

    ok, message = manager.advance(first.id, "重新值得继续想。")

    assert ok is True
    assert "已推进思考流" in message
    assert manager.get(first.id).status == "active"
    assert len(manager.list_active()) == 2
    assert sum(1 for stream in manager.list_all() if stream.status == "dormant") == 1


def test_advance_rejects_completed_stream(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    stream = manager.create("已经结束的想法")
    manager.retire(stream.id, new_status="completed")

    ok, message = manager.advance(stream.id, "不应该继续推进。")

    assert ok is False
    assert "已完成" in message
    assert manager.get(stream.id).status == "completed"
    assert manager.get(stream.id).advance_count == 0


def test_advance_rejects_unknown_status_without_mutating(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    stream = manager.create("状态异常的想法")
    stream.status = "paused"

    ok, message = manager.advance(stream.id, "不应该假装推进成功。")

    assert ok is False
    assert "无法推进" in message
    assert manager.get(stream.id).status == "paused"
    assert manager.get(stream.id).advance_count == 0
