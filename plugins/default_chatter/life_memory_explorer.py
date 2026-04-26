"""Life memory explorer Agent.

This module promotes deep life-memory retrieval from an exposed tool pair into
a dedicated Agent with private search/fetch tools and an explicit finish tool.
"""

from __future__ import annotations

import json
from typing import Annotated, Any

from plugins.life_engine.tools.file_tools import FetchLifeMemoryTool
from src.app.plugin_system.api.llm_api import get_model_set_by_task
from src.core.components import BaseAgent
from src.core.components.base.tool import BaseTool
from src.core.managers import get_plugin_manager
from src.kernel.llm import LLMPayload, ROLE, Text, ToolResult
from src.kernel.logger import Logger, get_logger

logger: Logger = get_logger("life_memory_explorer")


def _get_life_plugin() -> Any:
    """Return the loaded life_engine plugin."""
    life_plugin = get_plugin_manager().get_plugin("life_engine")
    if life_plugin is None:
        raise RuntimeError("life_engine 未加载")
    return life_plugin


def _get_life_service() -> Any:
    """Return the life_engine service."""
    life_plugin = _get_life_plugin()
    service = getattr(life_plugin, "service", None)
    if service is None:
        raise RuntimeError("life_engine 服务不可用")
    return service


def _normalize_usable_name(name: str) -> str:
    """Strip common schema prefixes from tool/agent names."""
    for prefix in ("tool-", "agent-"):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _build_step_reminder(step_index: int, max_steps: int) -> str:
    current = step_index + 1
    if current >= max_steps:
        return (
            "【推理轮次提醒】"
            f"你已到达最后一轮 follow-up（{current}/{max_steps}）。"
            "请立刻调用 memory_finish_task(content=...) 返回当前检索结论，"
            "不要再调用其他工具。"
        )
    return (
        "【推理轮次提醒】"
        f"当前 follow-up 轮次：{current}/{max_steps}。"
        "请控制工具调用数量；信息足够后必须调用 memory_finish_task(content=...)。"
    )


def _with_single_system_payload(
    payloads: list[LLMPayload],
    *,
    base_system_prompt: str,
    step_reminder: str,
) -> list[LLMPayload]:
    """Keep one SYSTEM payload and preserve TOOL/conversation payloads."""
    tool_payloads: list[LLMPayload] = []
    convo_payloads: list[LLMPayload] = []
    for payload in payloads:
        if payload.role == ROLE.SYSTEM:
            continue
        if payload.role == ROLE.TOOL:
            tool_payloads.append(payload)
            continue
        convo_payloads.append(payload)

    return [
        LLMPayload(ROLE.SYSTEM, [Text(step_reminder), Text(base_system_prompt)]),
        *tool_payloads,
        *convo_payloads,
    ]


class LifeMemorySearchTool(BaseTool):
    """Private summary search tool for LifeMemoryExplorerAgent."""

    tool_name = "life_memory_search"
    tool_description = (
        "检索生命中枢深层记忆摘要与相关文件路径。"
        "这是 life_memory_explorer Agent 的私有工具，适合先定位相关记忆。"
    )

    async def execute(
        self,
        query: Annotated[str, "要检索的记忆主题或关键词"],
        top_k: Annotated[int, "最多返回多少条主结果，默认 5"] = 5,
    ) -> tuple[bool, str]:
        query_text = str(query or "").strip()
        if not query_text:
            return False, "query 不能为空"

        resolved_top_k = max(1, min(int(top_k), 10))
        try:
            service = _get_life_service()
            if hasattr(service, "search_actor_memory"):
                result = await service.search_actor_memory(query_text, top_k=resolved_top_k)
            elif hasattr(service, "search_outer_memory"):
                result = await service.search_outer_memory(query_text, top_k=resolved_top_k)
            else:
                return False, "life_engine 服务不支持深层记忆检索"

            logger.info(
                f"[life_memory_search] query={query_text} top_k={resolved_top_k} "
                f"result_len={len(result) if result else 0}"
            )
            if not result:
                return True, "暂时没有检索到相关记忆"
            return True, result
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"检索 life memory 失败: {exc}")
            return False, f"检索失败: {exc}"


class LifeMemoryFetchTool(BaseTool):
    """Private full-content fetch tool for LifeMemoryExplorerAgent."""

    tool_name = "life_memory_fetch"
    tool_description = (
        "读取 life_memory_search 返回的记忆文件完整内容。"
        "仅在摘要不足以回答问题时使用。"
    )

    async def execute(
        self,
        file_paths: Annotated[list[str], "要读取的文件路径列表"],
        max_length_per_file: Annotated[int, "每个文件最大字符数，0=不限制"] = 5000,
        include_metadata: Annotated[bool, "是否包含文件元数据"] = True,
    ) -> tuple[bool, dict]:
        try:
            life_plugin = _get_life_plugin()
            tool = FetchLifeMemoryTool(plugin=life_plugin)
            return await tool.execute(
                file_paths=file_paths,
                max_length_per_file=max_length_per_file,
                include_metadata=include_metadata,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"读取 life memory 文件失败: {exc}")
            return False, {"error": f"读取失败: {exc}"}


class LifeMemoryFinishTaskTool(BaseTool):
    """Finish the explorer task and return the final summary."""

    tool_name = "memory_finish_task"
    tool_description = "结束当前记忆检索任务，并把最终自然语言结果返回给主模型。"

    async def execute(
        self,
        content: Annotated[str, "返回给主模型的自然语言结果"],
    ) -> tuple[bool, str]:
        text = str(content or "").strip()
        if not text:
            return False, "content 不能为空"
        return True, text


class LifeMemoryExplorerAgent(BaseAgent):
    """Agent that explores life_engine deep memory and summarizes evidence."""

    agent_name = "life_memory_explorer"
    agent_description = (
        "探索式检索生命中枢深层记忆。"
        "适合查询过去聊过的事、旧计划、历史文件记录、被记住的线索。"
        "会自行决定是否读取全文，并返回整合后的结论、依据与不确定性。"
    )
    chatter_allow: list[str] = ["default_chatter", "life_chatter"]
    usables = [
        LifeMemorySearchTool,
        LifeMemoryFetchTool,
        LifeMemoryFinishTaskTool,
    ]

    @staticmethod
    def _build_system_prompt() -> str:
        return """你是 life_memory_explorer，一个专职记忆检索 Agent。

## 职责
- 理解主模型传入的 query，检索生命中枢深层记忆。
- 先用 life_memory_search 获取摘要和路径。
- 摘要不足时，再用 life_memory_fetch 读取最相关文件全文。
- 整合结果，返回可直接给主模型使用的自然语言摘要。

## detail_level 规则
- brief: 只使用 life_memory_search 摘要，不读全文。
- normal: 摘要不足时读取最相关的 1-2 条，每个文件最多 500 字符。
- detailed: 读取所有高相关结果，每个文件最多 1000 字符。
- auto: 根据信息完整度自行判断是否读取全文。

## 输出要求
- 必须调用 memory_finish_task(content=...) 结束任务。
- content 包含：核心结论、关键依据、必要的不确定性。
- 没有找到相关记忆时明确说明，不要编造。
- 不要说“我已经检索完成”等元信息，直接给结果。"""

    async def execute(
        self,
        query: Annotated[str, "要检索的记忆主题或关键词"],
        detail_level: Annotated[str, "详细程度：brief/normal/detailed/auto"] = "normal",
        max_results: Annotated[int, "最多返回几条记忆"] = 3,
    ) -> tuple[bool, str | dict]:
        query_text = str(query or "").strip()
        if not query_text:
            return False, "query 不能为空"

        resolved_detail = str(detail_level or "normal").strip().lower()
        if resolved_detail not in {"brief", "normal", "detailed", "auto"}:
            resolved_detail = "normal"

        resolved_max_results = max(1, min(int(max_results), 5))
        try:
            model_set = get_model_set_by_task("sub_actor")
            request = self.create_llm_request(
                model_set=model_set,
                request_name="life_memory_explorer",
                with_usables=True,
            )
            base_system_prompt = self._build_system_prompt()
            request.add_payload(LLMPayload(ROLE.SYSTEM, Text(base_system_prompt)))
            request.add_payload(
                LLMPayload(
                    ROLE.USER,
                    Text(
                        json.dumps(
                            {
                                "query": query_text,
                                "detail_level": resolved_detail,
                                "max_results": resolved_max_results,
                            },
                            ensure_ascii=False,
                        )
                    ),
                )
            )

            max_steps = 5
            response = await request.send(stream=False)
            await response
            tool_traces: list[dict[str, Any]] = []

            for step_index in range(max_steps):
                calls = list(getattr(response, "call_list", []) or [])
                if not calls:
                    return False, {
                        "error": "life_memory_explorer 未调用 memory_finish_task，无法确认检索结果",
                        "tool_traces": tool_traces,
                    }

                for call in calls:
                    call_name = str(getattr(call, "name", "") or "")
                    normalized_name = _normalize_usable_name(call_name)
                    args = getattr(call, "args", {}) if isinstance(getattr(call, "args", None), dict) else {}

                    if normalized_name == "memory_finish_task":
                        content = str(args.get("content", "")).strip()
                        if not content:
                            return False, "memory_finish_task 的 content 不能为空"
                        logger.info(
                            f"[life_memory_explorer] query={query_text} "
                            f"detail_level={resolved_detail} steps={step_index + 1} "
                            f"result_len={len(content)}"
                        )
                        return True, content

                    success, result = await self.execute_local_usable(
                        normalized_name,
                        None,
                        **args,
                    )
                    trace = {"tool": normalized_name, "success": success, "result": result}
                    tool_traces.append(trace)
                    response.add_payload(
                        LLMPayload(
                            ROLE.TOOL_RESULT,
                            ToolResult(
                                value=trace,
                                call_id=getattr(call, "id", None),
                                name=call_name,
                            ),
                        )
                    )

                response.payloads = _with_single_system_payload(
                    response.payloads,
                    base_system_prompt=base_system_prompt,
                    step_reminder=_build_step_reminder(step_index, max_steps),
                )
                response = await response.send(stream=False)
                await response

            return False, {
                "error": "life_memory_explorer 未能在规定轮数内完成检索",
                "tool_traces": tool_traces,
            }
        except Exception as exc:  # noqa: BLE001
            logger.error(f"life_memory_explorer 执行失败: {exc}", exc_info=True)
            return False, f"检索失败: {exc}"
