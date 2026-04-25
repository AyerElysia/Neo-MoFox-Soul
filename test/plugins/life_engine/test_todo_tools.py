"""life TODO tool tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from plugins.life_engine.core.config import LifeEngineConfig
from plugins.life_engine.tools.todo_tools import (
    LifeEngineListTodosTool,
    LifeTodo,
    TodoStatus,
    TodoStorage,
)


def _make_tool(tmp_path: Path) -> LifeEngineListTodosTool:
    config = LifeEngineConfig()
    config.settings.workspace_path = str(tmp_path)
    plugin = SimpleNamespace(config=config)
    return LifeEngineListTodosTool(plugin=plugin)  # type: ignore[arg-type]


def _seed_todos(tmp_path: Path, count: int, *, completed: int = 0) -> None:
    todos = [
        LifeTodo(
            id=f"todo_{index:02d}",
            title=f"想做的事 {index}",
            description=f"很长的描述 {index}",
            notes=f"很多内心笔记 {index}",
            completion_feeling=f"完成感受 {index}",
            tags=["life", "test"],
        )
        for index in range(count)
    ]
    todos.extend(
        LifeTodo(
            id=f"done_{index:02d}",
            title=f"已完成 {index}",
            status=TodoStatus.COMPLETED.value,
        )
        for index in range(completed)
    )
    TodoStorage(tmp_path).save(todos)


@pytest.mark.asyncio
async def test_list_todos_defaults_to_compact_limited_summary(tmp_path: Path) -> None:
    _seed_todos(tmp_path, 12, completed=1)
    tool = _make_tool(tmp_path)

    ok, payload = await tool.execute()

    assert ok is True
    assert isinstance(payload, dict)
    assert payload["action"] == "list_todos"
    assert payload["total"] == 12
    assert payload["all_count"] == 13
    assert payload["returned"] == 10
    assert payload["limit"] == 10
    assert payload["truncated"] is True
    assert payload["detail_level"] == "summary"

    first = payload["todos"][0]
    assert set(first) == {
        "id",
        "title",
        "status",
        "desire",
        "meaning",
        "deadline",
        "target_time",
        "days_left",
        "tags",
        "has_description",
        "has_notes",
        "has_completion_feeling",
    }
    assert first["has_description"] is True
    assert first["has_notes"] is True
    assert first["has_completion_feeling"] is True
    assert "description" not in first
    assert "notes" not in first
    assert "created_at" not in first


@pytest.mark.asyncio
async def test_list_todos_full_detail_is_explicit_and_still_limited(tmp_path: Path) -> None:
    _seed_todos(tmp_path, 3)
    tool = _make_tool(tmp_path)

    ok, payload = await tool.execute(limit=2, detail_level="full")

    assert ok is True
    assert isinstance(payload, dict)
    assert payload["returned"] == 2
    assert payload["total"] == 3
    assert payload["truncated"] is True
    assert payload["detail_level"] == "full"
    assert "description" in payload["todos"][0]
    assert "notes" in payload["todos"][0]
    assert "created_at" in payload["todos"][0]


@pytest.mark.asyncio
async def test_list_todos_limit_has_hard_cap(tmp_path: Path) -> None:
    _seed_todos(tmp_path, 30)
    tool = _make_tool(tmp_path)

    ok, payload = await tool.execute(limit=100)

    assert ok is True
    assert isinstance(payload, dict)
    assert payload["limit"] == 25
    assert payload["returned"] == 25
    assert payload["truncated"] is True
