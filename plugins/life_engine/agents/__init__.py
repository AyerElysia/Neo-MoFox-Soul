"""life_engine 智能体类型系统。

提供可扩展的智能体类型定义、注册表和运行器，
将 Claude Code 的 AgentTool 架构适配到 life_engine 的心跳循环中。
"""

from .definitions import AgentTypeDefinition, AgentResult
from .registry import AgentTypeRegistry, get_agent_type_registry
from .builtin import register_builtin_agents

__all__ = [
    "AgentTypeDefinition",
    "AgentResult",
    "AgentTypeRegistry",
    "get_agent_type_registry",
    "register_builtin_agents",
]
