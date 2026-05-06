"""life_engine 记忆演化链路回归测试。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from plugins.life_engine.core.config import LifeEngineConfig
from plugins.life_engine.memory import LifeMemoryService
from plugins.life_engine.tools.file_tools import FetchLifeMemoryTool


@dataclass
class _DummyPlugin:
    config: LifeEngineConfig


class _FakeCollection:
    def query(self, **_: Any) -> dict[str, list[list[Any]]]:
        return {"ids": [[]], "distances": [[]]}

    def get(self, **_: Any) -> dict[str, list[Any]]:
        return {"ids": [], "embeddings": [], "documents": [], "metadatas": []}

    def upsert(self, **_: Any) -> None:
        return None

    def delete(self, **_: Any) -> None:
        return None


def _make_plugin(tmp_path: Path) -> _DummyPlugin:
    config = LifeEngineConfig()
    config.settings.workspace_path = str(tmp_path)
    return _DummyPlugin(config=config)


def test_dream_system_lineage_keeps_old_memory_and_resolves_current_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧研究笔记不应被删掉，而应指向后来的当前文件。"""

    async def _run() -> None:
        plugin = _make_plugin(tmp_path)
        service = LifeMemoryService(plugin)

        async def _fake_get_collection() -> Any:
            return _FakeCollection()

        async def _fake_embed_text(_: str) -> list[float]:
            return [0.0]

        monkeypatch.setattr(service, "_get_chroma_collection", _fake_get_collection)
        monkeypatch.setattr("plugins.life_engine.memory.search.embed_text", _fake_embed_text)
        await service.initialize()

        old_path = "notes/tech/dream_system_research.md"
        current_path = "notes/tech/dream_system.md"
        current_file = tmp_path / current_path
        current_file.parent.mkdir(parents=True)
        current_file.write_text(
            "# 做梦系统\n\n做梦系统已经做好了，会整理记忆，也会生成洞察。\n",
            encoding="utf-8",
        )

        await service.get_or_create_file_node(
            old_path,
            title="dream_system_research",
            content="做梦系统还在研究阶段，旧笔记只记录了早期方案。",
        )

        resolution = await service.resolve_canonical_path(old_path)
        assert resolution["resolved"] is True
        assert resolution["resolved_path"] == current_path
        assert resolution["lineage"][0]["relation"] == "renames"

        await service.record_memory_correction(
            topic="做梦系统",
            message="做梦系统早就做好了；旧研究笔记只能作为早期轨迹，不代表当前状态。",
            related_paths=[current_path],
            query="做梦系统",
        )

        bundles = await service.search_memory_bundles("做梦系统", top_k=3)
        assert bundles
        bundle = bundles[0]
        assert bundle.primary_path == current_path
        assert "早就做好了" in bundle.current_understanding

        evidence_paths = {item.file_path for item in bundle.evidence}
        assert old_path in evidence_paths
        assert current_path in evidence_paths
        assert any(item.file_path == old_path for item in bundle.history_trace)

        monkeypatch.setattr(
            "plugins.life_engine.tools.file_tools._get_life_engine_service",
            lambda _plugin: type("_Service", (), {"_memory_service": service})(),
        )
        tool = FetchLifeMemoryTool(plugin=plugin)
        ok, payload = await tool.execute([old_path], max_length_per_file=1000)
        assert ok is True
        assert payload["successful"] == 1
        file_payload = payload["files"][0]
        assert file_payload["path"] == current_path
        assert file_payload["requested_path"] == old_path
        assert "已经做好了" in file_payload["content"]
        assert file_payload["path_resolution"]["resolved"] is True

    asyncio.run(_run())
