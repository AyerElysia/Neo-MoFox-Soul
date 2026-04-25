"""life heartbeat pause tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from plugins.life_engine.core.config import LifeEngineConfig
from plugins.life_engine.service.core import LifeEngineService


def _service(threshold: int = 30) -> LifeEngineService:
    config = LifeEngineConfig()
    config.settings.idle_pause_after_external_silence_minutes = threshold
    return LifeEngineService(SimpleNamespace(config=config))


def test_should_pause_llm_heartbeat_after_external_silence() -> None:
    service = _service(threshold=30)
    service._state.last_external_message_at = (
        datetime.now(timezone.utc).astimezone() - timedelta(minutes=31)
    ).isoformat()

    paused, minutes, threshold = service._should_pause_llm_heartbeat_for_external_silence()

    assert paused is True
    assert minutes is not None and minutes >= 30
    assert threshold == 30


def test_should_not_pause_llm_heartbeat_when_disabled() -> None:
    service = _service(threshold=0)
    service._state.last_external_message_at = (
        datetime.now(timezone.utc).astimezone() - timedelta(hours=6)
    ).isoformat()

    paused, _minutes, threshold = service._should_pause_llm_heartbeat_for_external_silence()

    assert paused is False
    assert threshold == 0


def test_should_not_pause_llm_heartbeat_without_external_message_record() -> None:
    service = _service(threshold=30)

    paused, minutes, threshold = service._should_pause_llm_heartbeat_for_external_silence()

    assert paused is False
    assert minutes is None
    assert threshold == 30
