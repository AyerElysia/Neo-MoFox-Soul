"""智能体类型定义与执行结果。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class AgentTypeDefinition:
    """智能体类型蓝图，描述一类智能体的能力边界和行为规范。

    对应 Claude Code 的 BaseAgentDefinition，适配 life_engine 的工具体系。
    """

    agent_type: str
    when_to_use: str
    system_prompt: Callable[[], str]
    allowed_tools: list[str] | None = None
    disallowed_tools: list[str] = field(default_factory=list)
    model_task_name: str | None = None
    max_rounds: int = 10
    is_read_only: bool = False
    background: bool = False


@dataclass
class AgentResult:
    """智能体执行结果。"""

    agent_type: str
    success: bool
    result_text: str
    tool_use_count: int = 0
    duration_ms: int = 0
    rounds_used: int = 0
