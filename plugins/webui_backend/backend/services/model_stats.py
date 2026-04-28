"""LLM model statistics aggregation helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from src.core.config import get_model_config
from src.kernel.llm.monitor import RequestMetrics, get_global_collector
from src.kernel.logger import get_logger

logger = get_logger("webui.model_stats")


TIME_RANGE_TO_DELTA: dict[str, timedelta | None] = {
    "1h": timedelta(hours=1),
    "24h": timedelta(hours=24),
    "7d": timedelta(days=7),
    "30d": timedelta(days=30),
    "all": None,
}


@dataclass(slots=True)
class AggregatedStats:
    """Aggregated statistics for a group."""

    total_calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    total_latency: float = 0.0
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def add(self, metrics: RequestMetrics, *, cost: float = 0.0) -> None:
        self.total_calls += 1
        self.prompt_tokens += int(metrics.tokens_in or 0)
        self.completion_tokens += int(metrics.tokens_out or 0)
        self.total_tokens += int(metrics.tokens_in or 0) + int(metrics.tokens_out or 0)
        self.total_cost += float(cost)
        self.total_latency += float(metrics.latency or 0.0)

        if self.first_seen is None or metrics.timestamp < self.first_seen:
            self.first_seen = metrics.timestamp
        if self.last_seen is None or metrics.timestamp > self.last_seen:
            self.last_seen = metrics.timestamp

    @property
    def avg_time(self) -> float:
        return self.total_latency / self.total_calls if self.total_calls else 0.0

    @property
    def avg_tokens_per_call(self) -> float:
        return self.total_tokens / self.total_calls if self.total_calls else 0.0

    @property
    def tps(self) -> float:
        if self.total_latency <= 0:
            return 0.0
        return self.total_tokens / self.total_latency

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_calls": self.total_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "avg_time": self.avg_time,
            "avg_tokens_per_call": self.avg_tokens_per_call,
            "tps": self.tps,
        }


def _normalize_time_range(time_range: str) -> str:
    if time_range in TIME_RANGE_TO_DELTA:
        return time_range
    logger.warning("未知的 time_range=%s，回退到 24h", time_range)
    return "24h"


def _get_cutoff(time_range: str) -> datetime | None:
    delta = TIME_RANGE_TO_DELTA[_normalize_time_range(time_range)]
    if delta is None:
        return None
    return datetime.now() - delta


def _collect_metrics(time_range: str) -> list[RequestMetrics]:
    collector = get_global_collector()
    cutoff = _get_cutoff(time_range)
    history = collector.get_recent_history(limit=10000)
    if cutoff is None:
        return list(history)
    return [metric for metric in history if metric.timestamp >= cutoff]


def _model_lookup() -> dict[str, tuple[str, float, float]]:
    lookup: dict[str, tuple[str, float, float]] = {}
    try:
        config = get_model_config()
    except Exception:
        return lookup

    for model in config.models:
        lookup[model.name] = (model.api_provider, float(model.price_in), float(model.price_out))
        lookup[model.model_identifier] = (
            model.api_provider,
            float(model.price_in),
            float(model.price_out),
        )
    return lookup


def _resolve_model_info(model_name: str) -> tuple[str, float, float]:
    lookup = _model_lookup()
    return lookup.get(model_name, ("unknown", 0.0, 0.0))


def _estimate_cost(metrics: RequestMetrics, model_name: str) -> float:
    _, price_in, price_out = _resolve_model_info(model_name)
    tokens_in = int(metrics.tokens_in or 0)
    tokens_out = int(metrics.tokens_out or 0)
    return (tokens_in * price_in + tokens_out * price_out) / 1_000_000.0


def _aggregate_by(
    metrics: list[RequestMetrics],
    key_fn,
) -> dict[str, AggregatedStats]:
    result: dict[str, AggregatedStats] = {}
    for metric in metrics:
        key = key_fn(metric)
        bucket = result.setdefault(key, AggregatedStats())
        bucket.add(metric, cost=_estimate_cost(metric, metric.model_name))
    return result


def _make_chart_payload(stats_map: dict[str, AggregatedStats], *, key: str) -> dict[str, dict[str, list[Any]]]:
    items = sorted(
        stats_map.items(),
        key=lambda item: (-float(getattr(item[1], key)), item[0]),
    )
    labels = [name for name, _ in items]
    values = [round(getattr(stat, key), 4) if isinstance(getattr(stat, key), float) else getattr(stat, key) for _, stat in items]
    return {"labels": labels, "data": values}


def get_model_usage_stats(time_range: str = "24h") -> dict[str, Any]:
    """Return per-model usage stats."""

    metrics = _collect_metrics(time_range)
    grouped = _aggregate_by(metrics, lambda metric: metric.model_name)
    return {
        "stats": {name: stat.to_dict() for name, stat in sorted(grouped.items())},
    }


def get_model_overview(time_range: str = "24h") -> dict[str, Any]:
    """Return overall model usage overview."""

    metrics = _collect_metrics(time_range)
    grouped = _aggregate_by(metrics, lambda metric: metric.model_name)

    total_calls = sum(stat.total_calls for stat in grouped.values())
    total_tokens = sum(stat.total_tokens for stat in grouped.values())
    total_cost = sum(stat.total_cost for stat in grouped.values())

    most_used_model = None
    if grouped:
        most_used_model = max(grouped.items(), key=lambda item: item[1].total_calls)[0]

    most_expensive_model = None
    if grouped:
        most_expensive_model = max(grouped.items(), key=lambda item: item[1].total_cost)[0]

    return {
        "total_models": len(grouped),
        "total_calls": total_calls,
        "total_tokens": total_tokens,
        "total_cost": total_cost,
        "most_used_model": most_used_model,
        "most_expensive_model": most_expensive_model,
    }


def get_model_detail(model_name: str, time_range: str = "24h") -> dict[str, Any]:
    """Return detail stats for a single model."""

    metrics = [metric for metric in _collect_metrics(time_range) if metric.model_name == model_name]
    grouped = _aggregate_by(metrics, lambda metric: metric.model_name)
    stats = grouped.get(model_name, AggregatedStats())
    return {
        "model_name": model_name,
        "total_calls": stats.total_calls,
        "prompt_tokens": stats.prompt_tokens,
        "completion_tokens": stats.completion_tokens,
        "total_tokens": stats.total_tokens,
        "total_cost": stats.total_cost,
        "avg_tokens_per_call": stats.avg_tokens_per_call,
        "avg_time_per_call": stats.avg_time,
        "tps": stats.tps,
        "cost_per_ktok": (stats.total_cost / stats.total_tokens * 1000.0) if stats.total_tokens else 0.0,
    }


def get_provider_stats(time_range: str = "24h") -> dict[str, Any]:
    """Return stats grouped by provider."""

    metrics = _collect_metrics(time_range)
    grouped = _aggregate_by(metrics, lambda metric: _resolve_model_info(metric.model_name)[0])
    return {
        "stats": {name: stat.to_dict() for name, stat in sorted(grouped.items())},
    }


def get_module_stats(time_range: str = "24h") -> dict[str, Any]:
    """Return stats grouped by request name."""

    metrics = _collect_metrics(time_range)

    def _module_key(metric: RequestMetrics) -> str:
        request_name = (metric.request_name or "").strip()
        return request_name or "unknown"

    grouped = _aggregate_by(metrics, _module_key)
    return {
        "stats": {name: stat.to_dict() for name, stat in sorted(grouped.items())},
    }


def get_chart_data(time_range: str = "24h") -> dict[str, Any]:
    """Return chart-friendly summaries."""

    metrics = _collect_metrics(time_range)
    model_stats = _aggregate_by(metrics, lambda metric: metric.model_name)
    provider_stats = _aggregate_by(metrics, lambda metric: _resolve_model_info(metric.model_name)[0])

    return {
        "chart_data": {
            "pie_chart_cost_by_provider": _make_chart_payload(provider_stats, key="total_cost"),
            "pie_chart_req_by_provider": _make_chart_payload(provider_stats, key="total_calls"),
            "pie_chart_cost_by_module": _make_chart_payload(
                _aggregate_by(metrics, lambda metric: (metric.request_name or "").strip() or "unknown"),
                key="total_cost",
            ),
            "bar_chart_cost_by_model": _make_chart_payload(model_stats, key="total_cost"),
            "bar_chart_req_by_model": _make_chart_payload(model_stats, key="total_calls"),
            "bar_chart_token_comparison": _make_chart_payload(model_stats, key="total_tokens"),
            "bar_chart_avg_response_time": _make_chart_payload(model_stats, key="avg_time"),
        }
    }
