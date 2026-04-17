"""Booku 长期记忆层测试。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from plugins.booku_memory.config import BookuMemoryConfig
from plugins.booku_memory.service.booku_memory_service import BookuMemoryService
from src.core.prompt import get_system_reminder_store, reset_system_reminder_store


@dataclass
class _DummyPlugin:
    config: Any


class _FakeVectorDB:
    def __init__(self) -> None:
        self._collections: dict[str, dict[str, dict[str, Any]]] = {}

    async def count(self, collection_name: str) -> int:
        return len(self._collections.get(collection_name, {}))

    async def query(self, **_: Any) -> dict[str, Any]:
        return {
            "ids": [[]],
            "embeddings": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

    async def get(self, **_: Any) -> dict[str, Any]:
        return {"embeddings": []}

    async def add(
        self,
        *,
        collection_name: str,
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        ids: list[str],
    ) -> None:
        collection = self._collections.setdefault(collection_name, {})
        for index, memory_id in enumerate(ids):
            collection[memory_id] = {
                "embedding": embeddings[index],
                "document": documents[index],
                "metadata": metadatas[index],
            }

    async def delete(self, *, collection_name: str, ids: list[str]) -> None:
        collection = self._collections.setdefault(collection_name, {})
        for memory_id in ids:
            collection.pop(memory_id, None)


@pytest.mark.anyio
async def test_edit_inherent_memory_rewrites_canonical_long_term_record(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """固有记忆编辑应清空旧版本，只保留最新长期记忆正文。"""

    cfg = BookuMemoryConfig()
    cfg.storage.metadata_db_path = str(tmp_path / "booku_memory.db")
    cfg.storage.vector_db_path = str(tmp_path / "vector_store")
    reset_system_reminder_store()

    vector_db = _FakeVectorDB()
    monkeypatch.setattr(
        "plugins.booku_memory.service.booku_memory_service.get_vector_db_service",
        lambda _path: vector_db,
    )

    async def _fake_embed_text(self: BookuMemoryService, text: str) -> list[float]:
        return [float(len(text)), 1.0, 0.5]

    monkeypatch.setattr(BookuMemoryService, "_embed_text", _fake_embed_text)

    service = BookuMemoryService(plugin=_DummyPlugin(config=cfg))
    repo = await service._get_repo()
    await repo.upsert_record(
        memory_id="inherent_old_1",
        title="旧固有记忆A",
        folder_id="global",
        bucket="inherent",
        content="# 旧固有记忆A\n旧内容A",
        source="unit_test",
        novelty_energy=0.1,
        tags=[],
        core_tags=[],
        diffusion_tags=[],
        opposing_tags=[],
    )
    await repo.upsert_record(
        memory_id="inherent_old_2",
        title="旧固有记忆B",
        folder_id="global",
        bucket="inherent",
        content="# 旧固有记忆B\n旧内容B",
        source="unit_test",
        novelty_energy=0.1,
        tags=[],
        core_tags=[],
        diffusion_tags=[],
        opposing_tags=[],
    )

    result = await service.edit_inherent_memory(content="新的长期记忆正文")

    records = await repo.list_records_by_bucket(
        bucket="inherent",
        folder_id=None,
        limit=20,
        include_deleted=True,
    )

    assert result["action"] == "edit_inherent_memory"
    assert result["mode"] == "created"
    assert len(records) == 1
    assert records[0].title == "固有记忆"

    resolved_title, pure_body = BookuMemoryService._split_title_and_content(
        records[0].title,
        records[0].content,
    )
    assert resolved_title == "固有记忆"
    assert pure_body == "新的长期记忆正文"

    stored = get_system_reminder_store().get("actor", names=["booku_memory"])
    assert "新的长期记忆正文" in stored
    assert "旧内容A" not in stored
    assert "旧内容B" not in stored

    await repo.close()
