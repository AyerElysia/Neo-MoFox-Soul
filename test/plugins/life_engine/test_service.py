"""life_engine 服务测试。"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from plugins.life_engine.core.config import LifeEngineConfig
from plugins.life_engine.service import LifeEngineService


@dataclass
class _DummyPlugin:
    config: object


def _make_service(tmp_path: Path) -> LifeEngineService:
    config = LifeEngineConfig()
    config.settings.enabled = True
    config.settings.workspace_path = str(tmp_path)
    return LifeEngineService(_DummyPlugin(config=config))


def test_memory_service_property_aliases_private_field(tmp_path: Path) -> None:
    """memory_service 公共属性应兼容映射到内部 _memory_service。"""
    service = _make_service(tmp_path)

    assert service.memory_service is None

    sentinel = object()
    service._memory_service = sentinel  # type: ignore[assignment]

    assert service.memory_service is sentinel


def test_cfg_auto_migrates_legacy_config_without_thresholds(tmp_path: Path) -> None:
    """旧版配置对象缺少 thresholds 时，_cfg 应自动迁移为新结构。"""

    class _LegacyConfig:
        def model_dump(self, mode: str = "python") -> dict[str, object]:
            return {
                "settings": {
                    "enabled": True,
                    "workspace_path": str(tmp_path),
                    "heartbeat_interval_seconds": 30,
                    "context_history_max_events": 100,
                    "max_rounds_per_heartbeat": 3,
                    "sleep_time": "",
                    "wake_time": "",
                    "log_heartbeat": True,
                },
                "model": {"task_name": "life"},
                "web": {},
                "snn": {"enabled": False, "shadow_only": True, "inject_to_heartbeat": False},
                "neuromod": {"enabled": True, "inject_to_heartbeat": True},
                "dream": {"enabled": True},
                "chatter": {"enabled": False, "mode": "enhanced", "max_rounds_per_chat": 5},
            }

    plugin = _DummyPlugin(config=_LegacyConfig())
    service = LifeEngineService(plugin)

    cfg = service._cfg()
    assert isinstance(cfg, LifeEngineConfig)
    assert hasattr(cfg, "thresholds")
    assert hasattr(cfg, "memory_algorithm")
    assert isinstance(plugin.config, LifeEngineConfig)


def test_heartbeat_system_prompt_filters_memory_sections(tmp_path: Path) -> None:
    """心跳态应只注入结构化 MEMORY 摘要，不带 Fading 和编辑说明。"""
    (tmp_path / "SOUL.md").write_text("SOUL_CONTENT", encoding="utf-8")
    (tmp_path / "TOOL.md").write_text("TOOL_CONTENT", encoding="utf-8")
    (tmp_path / "MEMORY.md").write_text(
        "\n".join(
            [
                "# 值得记住的事",
                "",
                "给编辑者看的说明",
                "",
                "### Durable（持久）",
                "- D1",
                "",
                "### Active（活跃）",
                "- A1",
                "",
                "### Fading（待审视）",
                "- F1",
            ]
        ),
        encoding="utf-8",
    )
    service = _make_service(tmp_path)

    prompt = service._build_heartbeat_system_prompt()

    assert "SOUL_CONTENT" in prompt
    assert "TOOL_CONTENT" in prompt
    assert "D1" in prompt
    assert "A1" in prompt
    assert "F1" not in prompt
    assert "给编辑者看的说明" not in prompt


def test_memory_maintenance_prompt_emits_once_per_interval(tmp_path: Path) -> None:
    """MEMORY 超限时，维护提醒不应在短时间内重复刷屏。"""
    oversize_item = "很长的叙事内容" * 80
    (tmp_path / "MEMORY.md").write_text(
        "\n".join(
            [
                "# 值得记住的事",
                "",
                "### Durable（持久）",
                *(f"- {oversize_item}{i}" for i in range(45)),
            ]
        ),
        encoding="utf-8",
    )
    service = _make_service(tmp_path)

    first = service._build_memory_maintenance_prompt_if_due()
    second = service._build_memory_maintenance_prompt_if_due()

    assert "MEMORY 维护任务" in first
    assert second == ""


@pytest.mark.asyncio
async def test_enqueue_dfc_message_appends_pending_event(tmp_path: Path) -> None:
    """DFC 留言应进入 pending 队列并持久化。"""
    service = _make_service(tmp_path)

    receipt = await service.enqueue_dfc_message(
        "另一个我最近有什么想法么？",
        stream_id="stream-1",
        platform="qq",
        chat_type="private",
        sender_name="DFC",
    )

    assert receipt["queued"] is True
    assert receipt["stream_id"] == "stream-1"
    assert receipt["pending_event_count"] == 1

    assert len(service._pending_events) == 1
    event = service._pending_events[0]
    assert event.event_id == receipt["event_id"]
    assert event.event_type.value == "message"
    assert event.source == "qq"
    assert event.stream_id == "stream-1"
    assert event.chat_type == "private"
    assert event.sender == "DFC"
    assert event.content == "另一个我最近有什么想法么？"
    assert "DFC 留言给生命中枢" in event.source_detail

    persisted = json.loads((tmp_path / "life_engine_context.json").read_text(encoding="utf-8"))
    assert len(persisted["pending_events"]) == 1
    assert persisted["pending_events"][0]["event_id"] == event.event_id
    assert persisted["pending_events"][0]["content_type"] == "dfc_message"


@pytest.mark.asyncio
async def test_enqueue_dfc_message_rejects_empty_message(tmp_path: Path) -> None:
    """空留言必须被拒绝。"""
    service = _make_service(tmp_path)

    with pytest.raises(ValueError, match="message 不能为空"):
        await service.enqueue_dfc_message("   ")


@pytest.mark.asyncio
async def test_chatter_context_cursor_persists_across_restart(tmp_path: Path) -> None:
    """life_chatter 事件流游标应持久化，避免重启后重复注入旧事件。"""
    service = _make_service(tmp_path)

    await service.mark_chatter_runtime_context_seen("stream-1", 42)
    await service._save_runtime_context()

    restored = _make_service(tmp_path)
    await restored._load_runtime_context()

    assert restored._state.chatter_context_cursors["stream-1"] == 42


@pytest.mark.asyncio
async def test_enqueue_dfc_message_rejects_when_disabled(tmp_path: Path) -> None:
    """life_engine 禁用时不应接受 DFC 留言。"""
    config = LifeEngineConfig()
    config.settings.enabled = False
    config.settings.workspace_path = str(tmp_path)
    service = LifeEngineService(_DummyPlugin(config=config))

    with pytest.raises(RuntimeError, match="life_engine 未启用"):
        await service.enqueue_dfc_message("帮我记一下")
