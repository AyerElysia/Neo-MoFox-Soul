"""监控和日志系统。

提供请求指标收集、统计分析功能。
支持内存 + JSON 文件双写持久化，进程重启后自动恢复。
"""

from __future__ import annotations

import atexit
import json
import os
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class RequestMetrics:
    """单次请求的指标数据。"""

    model_name: str
    request_name: str
    latency: float  # 延迟（秒）
    tokens_in: int | None = None
    tokens_out: int | None = None
    cost: float | None = None
    success: bool = True
    error: str | None = None
    error_type: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)
    stream: bool = False
    retry_count: int = 0
    model_index: int = 0
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "request_name": self.request_name,
            "latency": self.latency,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost": self.cost,
            "success": self.success,
            "error": self.error,
            "error_type": self.error_type,
            "timestamp": self.timestamp.isoformat(),
            "stream": self.stream,
            "retry_count": self.retry_count,
            "model_index": self.model_index,
            "extra": self.extra,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> RequestMetrics:
        return cls(
            model_name=d["model_name"],
            request_name=d["request_name"],
            latency=d["latency"],
            tokens_in=d.get("tokens_in"),
            tokens_out=d.get("tokens_out"),
            cost=d.get("cost"),
            success=d.get("success", True),
            error=d.get("error"),
            error_type=d.get("error_type"),
            timestamp=datetime.fromisoformat(d["timestamp"]),
            stream=d.get("stream", False),
            retry_count=d.get("retry_count", 0),
            model_index=d.get("model_index", 0),
            extra=d.get("extra", {}),
        )


@dataclass
class ModelStats:
    """模型的统计数据。"""

    model_name: str
    total_requests: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost: float = 0.0
    error_types: dict[str, int] = field(default_factory=lambda: defaultdict(int))

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.success_count / self.total_requests

    @property
    def avg_latency(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_latency / self.total_requests

    @property
    def avg_cost(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_cost / self.total_requests

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "total_requests": self.total_requests,
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "total_latency": self.total_latency,
            "avg_latency": self.avg_latency,
            "total_tokens_in": self.total_tokens_in,
            "total_tokens_out": self.total_tokens_out,
            "total_cost": self.total_cost,
            "avg_cost": self.avg_cost,
            "error_types": dict(self.error_types),
        }


_METRICS_VERSION = 1
_FLUSH_INTERVAL = 5.0  # 秒


class MetricsCollector:
    """指标收集器。

    线程安全，用于收集和存储 LLM 请求的指标。
    支持内存 + JSON 文件双写持久化。
    """

    def __init__(
        self,
        *,
        max_history: int = 10000,
        json_path: str | Path | None = None,
        flush_interval: float = _FLUSH_INTERVAL,
    ) -> None:
        self._lock = threading.RLock()
        self._history: deque[RequestMetrics] = deque(maxlen=max_history)
        self._max_history = max_history
        self._stats: dict[str, ModelStats] = {}

        # 持久化相关
        self._json_path: str | None = str(json_path) if json_path else None
        self._flush_interval = flush_interval
        self._persist_queue: list[RequestMetrics] = []
        self._persist_lock = threading.Lock()
        self._persist_thread: threading.Thread | None = None
        self._shutdown_event = threading.Event()

        if self._json_path:
            self._ensure_dir()
            self._restore_from_json()
            self._start_persist_thread()
            atexit.register(self.flush)

    def _ensure_dir(self) -> None:
        if self._json_path:
            os.makedirs(os.path.dirname(self._json_path), exist_ok=True)

    def _get_json_content(self) -> dict[str, Any]:
        """读取现有 JSON 文件内容。"""
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"version": _METRICS_VERSION, "max_history": self._max_history, "history": []}

    def _restore_from_json(self) -> None:
        """启动时从 JSON 文件恢复历史数据到内存。"""
        content = self._get_json_content()
        history_raw = content.get("history", [])
        metrics_list = []
        for item in reversed(history_raw[-self._max_history:]):
            try:
                metrics_list.append(RequestMetrics.from_dict(item))
            except Exception:
                continue

        with self._lock:
            self._history.extend(metrics_list)
            for m in metrics_list:
                self._update_stats(m)

    def _update_stats(self, metrics: RequestMetrics) -> None:
        """更新内存中的统计数据（调用方需持有 _lock）。"""
        model_name = metrics.model_name
        if model_name not in self._stats:
            self._stats[model_name] = ModelStats(model_name=model_name)

        stats = self._stats[model_name]
        stats.total_requests += 1
        if metrics.success:
            stats.success_count += 1
        else:
            stats.error_count += 1
            if metrics.error_type:
                stats.error_types[metrics.error_type] += 1

        stats.total_latency += metrics.latency
        if metrics.tokens_in:
            stats.total_tokens_in += metrics.tokens_in
        if metrics.tokens_out:
            stats.total_tokens_out += metrics.tokens_out
        if metrics.cost:
            stats.total_cost += metrics.cost

    def record_request(self, metrics: RequestMetrics) -> None:
        """记录一次请求。"""
        with self._lock:
            self._history.append(metrics)
            self._update_stats(metrics)

        if self._json_path:
            with self._persist_lock:
                self._persist_queue.append(metrics)

    def _do_persist(self) -> None:
        """将队列中的数据追加写入 JSON 文件。"""
        if not self._persist_queue or not self._json_path:
            return

        batch = self._persist_queue
        self._persist_queue = []

        try:
            content = self._get_json_content()
            history = content.get("history", [])

            for m in batch:
                history.append(m.to_dict())

            # 裁剪超出上限部分
            if len(history) > self._max_history:
                history = history[-self._max_history:]

            content["history"] = history
            content["version"] = _METRICS_VERSION
            content["max_history"] = self._max_history

            # 原子写入：先写临时文件再 rename
            tmp_path = self._json_path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._json_path)
        except Exception:
            # 持久化失败不影响主流程
            pass

    def _start_persist_thread(self) -> None:
        """启动定时刷写线程。"""
        self._persist_thread = threading.Thread(
            target=self._persist_worker,
            daemon=True,
            name="metrics-persist",
        )
        self._persist_thread.start()

    def _persist_worker(self) -> None:
        """定时将队列数据刷写到 JSON 文件。"""
        while not self._shutdown_event.is_set():
            self._shutdown_event.wait(timeout=self._flush_interval)
            with self._persist_lock:
                self._do_persist()

    def flush(self) -> None:
        """刷写所有待持久化的数据到 JSON 文件。"""
        if not self._json_path:
            return
        self._shutdown_event.set()
        with self._persist_lock:
            self._do_persist()
        if self._persist_thread and self._persist_thread.is_alive():
            self._persist_thread.join(timeout=5.0)

    def get_stats(self, model_name: str | None = None) -> dict[str, Any] | list[dict[str, Any]]:
        """获取统计数据。"""
        with self._lock:
            if model_name is not None:
                stats = self._stats.get(model_name)
                if stats is None:
                    return {
                        "model_name": model_name,
                        "total_requests": 0,
                        "success_count": 0,
                        "error_count": 0,
                        "success_rate": 0.0,
                    }
                return stats.to_dict()

            return [stats.to_dict() for stats in self._stats.values()]

    def get_recent_history(self, limit: int = 100) -> list[RequestMetrics]:
        """获取最近的请求历史。"""
        with self._lock:
            return list(self._history)[-limit:]

    def clear(self) -> None:
        """清空所有统计数据。"""
        with self._lock:
            self._history.clear()
            self._stats.clear()
        if self._json_path:
            with self._persist_lock:
                self._persist_queue.clear()
            try:
                content = {"version": _METRICS_VERSION, "max_history": self._max_history, "history": []}
                tmp_path = self._json_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, self._json_path)
            except Exception:
                pass


class RequestTimer:
    """请求计时器（上下文管理器）。"""

    def __init__(self) -> None:
        self.start_time: float = 0.0
        self.end_time: float = 0.0

    def __enter__(self) -> RequestTimer:
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.end_time = time.perf_counter()

    @property
    def elapsed(self) -> float:
        if self.end_time > 0:
            return self.end_time - self.start_time
        return time.perf_counter() - self.start_time


# 全局单例
_global_collector: MetricsCollector | None = None
_global_collector_lock = threading.Lock()

# 默认 JSON 持久化路径
_DEFAULT_JSON_PATH = "data/json_storage/llm_metrics.json"


def get_global_collector(json_path: str | Path | None = None) -> MetricsCollector:
    """获取全局指标收集器。

    Args:
        json_path: JSON 持久化文件路径。仅在首次创建时生效。
    """
    global _global_collector
    if _global_collector is not None:
        return _global_collector
    with _global_collector_lock:
        if _global_collector is not None:
            return _global_collector
        path = json_path if json_path is not None else _DEFAULT_JSON_PATH
        _global_collector = MetricsCollector(json_path=path)
        return _global_collector
