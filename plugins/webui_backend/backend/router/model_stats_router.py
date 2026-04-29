"""Model token statistics router."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

from src.core.components.base.router import BaseRouter
from src.core.utils.security import VerifiedDep
from src.kernel.logger import get_logger

from ..services.model_stats import (
    get_chart_data,
    get_model_detail,
    get_model_overview,
    get_model_usage_stats,
    get_module_stats,
    get_provider_stats,
)

logger = get_logger(name="WebUI_ModelStats", color="cyan")


class ModelUsageItemResponse(BaseModel):
    total_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost: float
    avg_time: float
    avg_tokens_per_call: float
    tps: float


class ModelUsageStatsResponse(BaseModel):
    stats: dict[str, ModelUsageItemResponse]


class ModelOverviewResponse(BaseModel):
    total_models: int
    total_calls: int
    total_tokens: int
    total_cost: float
    most_used_model: str | None
    most_expensive_model: str | None


class ModelDetailResponse(BaseModel):
    model_name: str
    total_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost: float
    avg_tokens_per_call: float
    avg_time_per_call: float
    tps: float
    cost_per_ktok: float


class ProviderStatsItemResponse(BaseModel):
    total_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost: float
    avg_time: float
    avg_tokens_per_call: float
    tps: float


class ProviderStatsResponse(BaseModel):
    stats: dict[str, ProviderStatsItemResponse]


class ModuleStatsItemResponse(BaseModel):
    total_calls: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost: float
    avg_time: float
    avg_tokens_per_call: float
    tps: float


class ModuleStatsResponse(BaseModel):
    stats: dict[str, ModuleStatsItemResponse]


class ChartPairResponse(BaseModel):
    labels: list[str]
    data: list[float]


class ChartDataResponse(BaseModel):
    chart_data: dict[str, ChartPairResponse]


class ModelStatsRouter(BaseRouter):
    """LLM model statistics router."""

    router_name = "WebUI_ModelStats"
    router_description = "WebUI 模型统计接口"
    custom_route_path = "/webui/api/model_stats"
    cors_origins = []

    def register_endpoints(self) -> None:
        """Register HTTP endpoints."""

        @self.app.get("/model_usage", summary="获取模型使用统计", response_model=ModelUsageStatsResponse)
        async def model_usage_stats(
            time_range: Literal["1h", "24h", "7d", "30d", "all"] = "24h",
            _=VerifiedDep,
        ):
            return get_model_usage_stats(time_range)

        @self.app.get("/model_overview", summary="获取模型统计总览", response_model=ModelOverviewResponse)
        async def model_overview(
            time_range: Literal["1h", "24h", "7d", "30d", "all"] = "24h",
            _=VerifiedDep,
        ):
            return get_model_overview(time_range)

        @self.app.get(
            "/model_detail/{model_name}",
            summary="获取模型详细统计",
            response_model=ModelDetailResponse,
        )
        async def model_detail(
            model_name: str,
            time_range: Literal["1h", "24h", "7d", "30d", "all"] = "24h",
            _=VerifiedDep,
        ):
            return get_model_detail(model_name, time_range)

        @self.app.get("/provider_stats", summary="获取提供商统计", response_model=ProviderStatsResponse)
        async def provider_stats(
            time_range: Literal["1h", "24h", "7d", "30d", "all"] = "24h",
            _=VerifiedDep,
        ):
            return get_provider_stats(time_range)

        @self.app.get("/module_stats", summary="获取模块统计", response_model=ModuleStatsResponse)
        async def module_stats(
            time_range: Literal["1h", "24h", "7d", "30d", "all"] = "24h",
            _=VerifiedDep,
        ):
            return get_module_stats(time_range)

        @self.app.get("/chart_data", summary="获取图表数据", response_model=ChartDataResponse)
        async def chart_data(
            time_range: Literal["1h", "24h", "7d", "30d", "all"] = "24h",
            _=VerifiedDep,
        ):
            return get_chart_data(time_range)

    async def startup(self) -> None:
        logger.info(f"ModelStats 路由已启动，路径: {self.custom_route_path}")

    async def shutdown(self) -> None:
        logger.info("ModelStats 路由已关闭")
