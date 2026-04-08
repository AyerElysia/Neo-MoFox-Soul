"""life_engine memory_service 回归测试。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from plugins.life_engine.config import LifeEngineConfig
from plugins.life_engine.memory_service import LifeMemoryService


@dataclass
class _DummyPlugin:
    config: LifeEngineConfig


class _FakeVectorService:
    """最小向量服务桩。"""

    def __init__(self, collection: Any) -> None:
        self._collection = collection
        self.calls = 0

    async def get_or_create_collection(self, name: str) -> Any:
        assert name == "life_memory"
        self.calls += 1
        return self._collection


def _make_service(tmp_path: Path) -> LifeMemoryService:
    config = LifeEngineConfig()
    config.settings.workspace_path = str(tmp_path)
    return LifeMemoryService(_DummyPlugin(config=config))


def test_get_chroma_collection_awaits_async_vector_service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """应 await 异步 get_or_create_collection，并缓存集合实例。"""

    service = _make_service(tmp_path)
    fake_collection = SimpleNamespace(query=lambda **_: {"ids": [[]], "distances": [[]]})
    fake_vector_service = _FakeVectorService(fake_collection)

    monkeypatch.setattr(
        "plugins.life_engine.memory_service.get_vector_db_service",
        lambda _path: fake_vector_service,
    )

    first = asyncio.run(service._get_chroma_collection())
    second = asyncio.run(service._get_chroma_collection())

    assert first is fake_collection
    assert second is fake_collection
    assert fake_vector_service.calls == 1
