"""做梦系统单元测试。"""

from __future__ import annotations

import asyncio
import time
from typing import Any
from unittest.mock import MagicMock, AsyncMock, patch

import numpy as np
import pytest

# ---------------------------------------------------------------------------
# Fixtures & helpers
# ---------------------------------------------------------------------------

def _make_snn_network():
    """创建一个 mock SNN 网络，包含真实 numpy 权重矩阵。"""
    net = MagicMock()
    net.hidden = MagicMock()
    net.output = MagicMock()
    net.hidden.tau = 20.0
    net.output.tau = 25.0
    net.hidden.w = np.random.rand(8, 8).astype(np.float32) * 0.5
    net.output.w = np.random.rand(8, 4).astype(np.float32) * 0.5
    net.tick_count = 100
    net.replay_episodes = MagicMock(return_value={
        "steps": 60, "hidden_spikes": 120, "output_spikes": 30,
    })
    net.homeostatic_scaling = MagicMock(return_value={
        "mean_before": 0.25, "mean_after": 0.245, "rate": 0.02,
    })
    return net


def _make_inner_state():
    """创建一个 mock 调质层。"""
    state = MagicMock()
    state.enter_sleep = MagicMock()
    state.wake_up = MagicMock()
    return state


def _make_memory_service():
    """创建一个 mock 记忆服务。"""
    svc = MagicMock()
    svc.dream_walk = MagicMock(return_value={
        "seeds": 5, "activated": 12, "new_edges": 3, "reinforced_edges": 8,
    })
    svc.prune_weak_edges = MagicMock(return_value={"pruned": 2})
    return svc


def _make_snn_bridge():
    """创建一个 mock SNN bridge。"""
    bridge = MagicMock()
    bridge.extract_features_from_events = MagicMock(
        return_value=np.zeros(8, dtype=np.float32)
    )
    return bridge


def _make_events(count: int = 30) -> list[dict[str, Any]]:
    """生成模拟事件历史。"""
    events = []
    base_time = time.time() - 3600
    for i in range(count):
        events.append({
            "type": "message" if i % 3 != 0 else "heartbeat",
            "timestamp": base_time + i * 60,
            "content": f"event_{i}",
            "source": "user" if i % 2 == 0 else "system",
        })
    return events


# ---------------------------------------------------------------------------
# DreamScheduler 测试
# ---------------------------------------------------------------------------

class TestDreamScheduler:
    """DreamScheduler 核心逻辑测试。"""

    def _make_scheduler(self, **overrides):
        from plugins.life_engine.dream import DreamScheduler
        kwargs = dict(
            snn=_make_snn_network(),
            inner_state=_make_inner_state(),
            memory_service=_make_memory_service(),
            snn_bridge=_make_snn_bridge(),
            nrem_replay_episodes=2,
            nrem_events_per_episode=10,
            nrem_speed_multiplier=5.0,
            nrem_homeostatic_rate=0.02,
            rem_walk_rounds=1,
            rem_seeds_per_round=3,
            rem_max_depth=3,
            rem_decay_factor=0.6,
            rem_learning_rate=0.05,
            rem_edge_prune_threshold=0.08,
            dream_interval_minutes=90,
            idle_trigger_heartbeats=10,
            nap_enabled=True,
        )
        kwargs.update(overrides)
        return DreamScheduler(**kwargs)

    def test_should_dream_respects_interval(self):
        """间隔不够时不应触发做梦。"""
        sched = self._make_scheduler(dream_interval_minutes=90)
        # 刚创建，last_dream_time 为 0，应该可以做梦
        assert sched.should_dream(idle_heartbeat_count=0, in_sleep_window=True)
        # 标记刚做过梦
        sched._last_dream_time = time.time()
        assert not sched.should_dream(idle_heartbeat_count=0, in_sleep_window=True)

    def test_should_dream_idle_nap(self):
        """白天空闲触发小憩做梦。"""
        sched = self._make_scheduler(idle_trigger_heartbeats=5, nap_enabled=True)
        assert not sched.should_dream(idle_heartbeat_count=3, in_sleep_window=False)
        assert sched.should_dream(idle_heartbeat_count=5, in_sleep_window=False)

    def test_should_dream_nap_disabled(self):
        """nap 禁用时白天不触发。"""
        sched = self._make_scheduler(nap_enabled=False)
        assert not sched.should_dream(idle_heartbeat_count=100, in_sleep_window=False)

    def test_enter_sleep_calls_inner_state(self):
        """enter_sleep 应调用调质层 enter_sleep。"""
        sched = self._make_scheduler()
        sched.enter_sleep()
        sched._inner_state.enter_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_dream_cycle_returns_report(self):
        """完整做梦周期应返回 DreamReport。"""
        from plugins.life_engine.dream import DreamReport
        sched = self._make_scheduler()
        events = _make_events(30)
        report = await sched.run_dream_cycle(events)
        assert isinstance(report, DreamReport)
        assert report.dream_id is not None
        assert report.duration_seconds >= 0
        sched._snn.replay_episodes.assert_called()
        sched._memory.dream_walk.assert_called()

    @pytest.mark.asyncio
    async def test_run_dream_cycle_updates_last_dream_time(self):
        """做梦后更新 last_dream_time。"""
        sched = self._make_scheduler()
        before = sched._last_dream_time
        events = _make_events(30)
        await sched.run_dream_cycle(events)
        assert sched._last_dream_time > before

    @pytest.mark.asyncio
    async def test_run_dream_cycle_no_events_still_completes(self):
        """即使没有事件也应正常完成做梦。"""
        sched = self._make_scheduler()
        report = await sched.run_dream_cycle([])
        assert report is not None

    def test_serialize_deserialize_roundtrip(self):
        """序列化/反序列化往返一致。"""
        sched = self._make_scheduler()
        sched._last_dream_time = 1234567890.0
        data = sched.serialize()
        assert isinstance(data, dict)
        assert data["last_dream_time"] == 1234567890.0

        sched2 = self._make_scheduler()
        sched2.deserialize(data)
        assert sched2._last_dream_time == 1234567890.0

    def test_get_state_returns_dict(self):
        """get_state 返回可序列化的状态字典。"""
        sched = self._make_scheduler()
        state = sched.get_state()
        assert isinstance(state, dict)
        assert "is_dreaming" in state
        assert "last_dream_time" in state


# ---------------------------------------------------------------------------
# SNN replay_episodes 和 homeostatic_scaling 真实逻辑测试
# ---------------------------------------------------------------------------

class TestSNNDreamMethods:
    """测试 SNN 核心网络的做梦相关方法。"""

    def _make_real_snn(self):
        try:
            from plugins.life_engine.snn_core import DriveCoreNetwork
            return DriveCoreNetwork()
        except Exception:
            pytest.skip("无法导入 DriveCoreNetwork")

    def test_replay_episodes_changes_weights(self):
        """replay_episodes 应返回正确结果。"""
        net = self._make_real_snn()
        # replay_episodes 接收扁平的特征序列列表
        features = [np.random.rand(8).astype(np.float32) for _ in range(20)]
        result = net.replay_episodes(features, speed_multiplier=5.0)
        assert "steps" in result
        assert result["steps"] == 20

    def test_homeostatic_scaling_reduces_weights(self):
        """homeostatic_scaling 应全局缩减突触权重。"""
        net = self._make_real_snn()
        # 权重在 syn_in_hid.W / syn_hid_out.W 上
        net.syn_in_hid.W = np.ones_like(net.syn_in_hid.W) * 0.5
        net.syn_hid_out.W = np.ones_like(net.syn_hid_out.W) * 0.5
        mean_before = net.syn_in_hid.W.mean()
        result = net.homeostatic_scaling(rate=0.02)
        mean_after = net.syn_in_hid.W.mean()
        assert mean_after < mean_before
        assert abs(mean_after - mean_before * 0.98) < 1e-5


# ---------------------------------------------------------------------------
# Neuromod enter_sleep / wake_up 真实逻辑测试
# ---------------------------------------------------------------------------

class TestNeuromodSleepWake:
    """测试调质层的睡眠/觉醒方法。"""

    def _make_real_inner_state(self):
        try:
            from plugins.life_engine.neuromod import InnerStateEngine
            return InnerStateEngine()
        except Exception:
            pytest.skip("无法导入 InnerStateEngine")

    def test_enter_sleep_lowers_energy(self):
        """enter_sleep 应降低精力。"""
        engine = self._make_real_inner_state()
        engine.enter_sleep()
        energy = engine.modulators.get("energy")
        assert energy.value <= 0.4
        assert energy.baseline == 0.25

    def test_wake_up_restores_energy(self):
        """wake_up 应恢复精力。"""
        engine = self._make_real_inner_state()
        engine.enter_sleep()
        engine.wake_up()
        energy = engine.modulators.get("energy")
        assert energy.value >= 0.4
        assert energy.baseline == 0.55

    def test_sleep_wake_cycle(self):
        """完整的睡眠-觉醒周期。"""
        engine = self._make_real_inner_state()
        initial_energy = engine.modulators.get("energy").value
        engine.enter_sleep()
        sleep_energy = engine.modulators.get("energy").value
        assert sleep_energy < initial_energy
        engine.wake_up()
        wake_energy = engine.modulators.get("energy").value
        assert wake_energy > sleep_energy


# ---------------------------------------------------------------------------
# Config DreamSection 测试
# ---------------------------------------------------------------------------

class TestDreamConfig:
    """测试做梦配置。"""

    def test_dream_section_defaults(self):
        from plugins.life_engine.config import LifeEngineConfig
        cfg = LifeEngineConfig()
        dream = cfg.dream
        assert dream.enabled is True
        assert dream.nrem_replay_episodes == 3
        assert dream.nrem_speed_multiplier == 5.0
        assert dream.rem_walk_rounds == 2
        assert dream.dream_interval_minutes == 90
        assert dream.nap_enabled is True

    def test_life_engine_config_has_dream(self):
        from plugins.life_engine.config import LifeEngineConfig
        cfg = LifeEngineConfig()
        assert hasattr(cfg, "dream")
        assert cfg.dream.enabled is True
