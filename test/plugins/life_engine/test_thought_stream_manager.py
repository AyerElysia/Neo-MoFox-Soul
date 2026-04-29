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


# ---- 新增：lazy decay / revision / focus / delta 标记 -----------------------


def test_revision_monotonically_increases(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    rev0 = manager.current_revision
    a = manager.create("idea-1")
    rev1 = manager.current_revision
    assert rev1 > rev0
    manager.advance(a.id, "推进一下")
    rev2 = manager.current_revision
    assert rev2 > rev1
    manager.retire(a.id, new_status="dormant")
    assert manager.current_revision > rev2


def test_create_does_not_mark_focused(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path), curiosity_decay_half_life_hours=12.0)
    s = manager.create("仅创建不算焦点")
    assert s.last_focused_at == ""
    assert not s.is_focused(focus_window_minutes=30)


def test_advance_marks_focused(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    s = manager.create("idea")
    manager.advance(s.id, "想到一点")
    refreshed = manager.get(s.id)
    assert refreshed.last_focused_at != ""
    assert refreshed.is_focused(focus_window_minutes=30)


def test_lazy_decay_respects_floor(tmp_path) -> None:
    manager = ThoughtStreamManager(
        str(tmp_path),
        curiosity_decay_half_life_hours=0.001,  # 极快衰减
        curiosity_floor=0.2,
    )
    s = manager.create("会被衰减")
    s.curiosity_score = 0.9
    # 主动触发：把 last_decay_at 设到很久以前
    from datetime import datetime, timedelta, timezone
    s.last_decay_at = (datetime.now(timezone.utc) - timedelta(hours=10)).isoformat()
    refreshed = manager.get(s.id)
    assert refreshed.curiosity_score >= 0.2 - 1e-6
    assert refreshed.curiosity_score < 0.9


def test_format_for_prompt_no_top_heading(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    manager.create("topic-A")
    body = manager.format_for_prompt(max_items=3)
    assert "### 当前思考流" not in body
    assert "topic-A" in body


def test_format_for_prompt_grouped_focus_section(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    a = manager.create("背景思考")
    b = manager.create("焦点思考")
    manager.advance(b.id, "刚刚想到")
    body = manager.format_for_prompt(max_items=5, grouped=True, focus_window_minutes=30)
    assert "焦点思考" in body
    assert "背景思考" in body
    # focus 标题应在前
    assert body.index("焦点") < body.index("背景")
    _ = a


def test_format_for_prompt_delta_marking(tmp_path) -> None:
    manager = ThoughtStreamManager(str(tmp_path))
    s = manager.create("delta")
    cursor_before = manager.current_revision
    manager.advance(s.id, "新进展")
    body_with_delta = manager.format_for_prompt(
        max_items=3, revision_cursor=cursor_before, mark_delta=True
    )
    body_no_delta = manager.format_for_prompt(
        max_items=3, revision_cursor=manager.current_revision, mark_delta=True
    )
    assert "🔄" in body_with_delta
    assert "🔄" not in body_no_delta
