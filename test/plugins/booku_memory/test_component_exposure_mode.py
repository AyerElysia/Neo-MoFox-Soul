"""Booku Memory 插件运行时暴露面测试。"""

from __future__ import annotations

from plugins.booku_memory.agent.tools import BookuMemoryEditInherentTool
from plugins.booku_memory.config import BookuMemoryConfig
from plugins.booku_memory.plugin import BookuMemoryAgentPlugin
from plugins.booku_memory.service import BookuMemoryService


def test_get_components_returns_minimal_long_term_runtime_by_default() -> None:
    """缺少配置对象时也应只暴露长期记忆最小运行面。"""

    plugin = BookuMemoryAgentPlugin(config=None)

    assert plugin.get_components() == [
        BookuMemoryEditInherentTool,
        BookuMemoryService,
    ]


def test_get_components_returns_minimal_long_term_runtime_when_enabled() -> None:
    """启用插件时只保留长期记忆编辑工具与服务。"""

    cfg = BookuMemoryConfig()
    plugin = BookuMemoryAgentPlugin(config=cfg)

    assert plugin.get_components() == [
        BookuMemoryEditInherentTool,
        BookuMemoryService,
    ]


def test_get_components_returns_empty_when_plugin_disabled() -> None:
    """插件被禁用时不应暴露任何组件。"""

    cfg = BookuMemoryConfig()
    cfg.plugin.enabled = False
    plugin = BookuMemoryAgentPlugin(config=cfg)

    assert plugin.get_components() == []


def test_edit_inherent_tool_is_dfc_only() -> None:
    """长期记忆编辑只允许 default_chatter 调用。"""

    assert BookuMemoryEditInherentTool.chatter_allow == ["default_chatter"]
