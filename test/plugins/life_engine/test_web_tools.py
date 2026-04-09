"""life_engine web_tools 测试。"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from plugins.life_engine.config import LifeEngineConfig
from plugins.life_engine.web_tools import (
    LifeEngineBrowserFetchTool,
    LifeEngineWebSearchTool,
)


@dataclass
class _DummyPlugin:
    config: LifeEngineConfig


def _make_plugin(tmp_path: Path) -> _DummyPlugin:
    cfg = LifeEngineConfig()
    cfg.settings.workspace_path = str(tmp_path)
    return _DummyPlugin(config=cfg)


def test_web_search_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """web_search 应返回 Tavily 结果并完成字段规范化。"""
    plugin = _make_plugin(tmp_path)
    plugin.config.web.tavily_api_key = "tvly-test-key"

    async def _fake_post(_plugin, endpoint: str, payload: dict, _timeout: int) -> dict:
        assert endpoint == "/search"
        assert payload["query"] == "最新 AI 新闻"
        return {
            "answer": "这里是摘要",
            "results": [
                {
                    "title": "T1",
                    "url": "https://example.com/a",
                    "content": "snippet-a",
                    "score": 0.91,
                    "published_date": "2026-04-09",
                }
            ],
        }

    monkeypatch.setattr("plugins.life_engine.web_tools._tavily_post_json", _fake_post)

    tool = LifeEngineWebSearchTool(plugin=plugin)
    ok, data = asyncio.run(
        tool.execute(
            query="最新 AI 新闻",
            search_depth="advanced",
            topic="news",
            max_results=3,
            include_answer=True,
        )
    )

    assert ok is True
    assert data["action"] == "web_search"
    assert data["provider"] == "tavily"
    assert data["total_results"] == 1
    assert data["results"][0]["title"] == "T1"
    assert data["answer"] == "这里是摘要"


def test_web_search_requires_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """未配置 Tavily key 时应给出明确错误。"""
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    plugin = _make_plugin(tmp_path)
    plugin.config.web.tavily_api_key = ""

    tool = LifeEngineWebSearchTool(plugin=plugin)
    ok, data = asyncio.run(tool.execute(query="test query"))

    assert ok is False
    assert "Tavily API Key" in data["error"]


def test_web_search_does_not_use_env_api_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """仅设置环境变量时不应生效，必须从 toml 配置读取 key。"""
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-env-only")
    plugin = _make_plugin(tmp_path)
    plugin.config.web.tavily_api_key = ""

    tool = LifeEngineWebSearchTool(plugin=plugin)
    ok, data = asyncio.run(tool.execute(query="test query"))

    assert ok is False
    assert "config/plugins/life_engine/config.toml" in data["error"]


def test_web_tools_allow_default_chatter() -> None:
    """网络工具应同时允许 life_engine 与 DFC(default_chatter) 调用。"""
    assert "life_engine_internal" in LifeEngineWebSearchTool.chatter_allow
    assert "default_chatter" in LifeEngineWebSearchTool.chatter_allow
    assert "life_engine_internal" in LifeEngineBrowserFetchTool.chatter_allow
    assert "default_chatter" in LifeEngineBrowserFetchTool.chatter_allow


def test_web_search_rejects_conflicting_domains(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """include_domains 与 exclude_domains 同时设置应被拒绝。"""
    plugin = _make_plugin(tmp_path)
    plugin.config.web.tavily_api_key = "tvly-test-key"

    tool = LifeEngineWebSearchTool(plugin=plugin)
    ok, data = asyncio.run(
        tool.execute(
            query="test",
            include_domains=["example.com"],
            exclude_domains=["foo.com"],
        )
    )

    assert ok is False
    assert "不能同时设置" in data["error"]


def test_browser_fetch_blocks_private_url(tmp_path: Path) -> None:
    """浏览工具应阻止访问本地/内网地址。"""
    plugin = _make_plugin(tmp_path)
    plugin.config.web.tavily_api_key = "tvly-test-key"

    tool = LifeEngineBrowserFetchTool(plugin=plugin)
    ok, data = asyncio.run(tool.execute(url="http://127.0.0.1:8080/admin"))

    assert ok is False
    assert "禁止访问本地或内网地址" in data["error"]


def test_browser_fetch_success_and_truncation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """browser_fetch 应提取内容并按 max_chars 截断。"""
    plugin = _make_plugin(tmp_path)
    plugin.config.web.tavily_api_key = "tvly-test-key"

    async def _fake_post(_plugin, endpoint: str, payload: dict, _timeout: int) -> dict:
        assert endpoint == "/extract"
        assert payload["urls"] == ["https://example.com/post"]
        return {
            "results": [
                {
                    "url": "https://example.com/post",
                    "title": "Example Post",
                    "content": "abcdefghijklmnopqrstuvwxyz",
                    "images": ["https://example.com/a.png"],
                }
            ]
        }

    monkeypatch.setattr("plugins.life_engine.web_tools._tavily_post_json", _fake_post)

    tool = LifeEngineBrowserFetchTool(plugin=plugin)
    ok, data = asyncio.run(
        tool.execute(
            url="https://example.com/post",
            extract_depth="basic",
            max_chars=10,
            include_images=True,
        )
    )

    assert ok is True
    assert data["action"] == "browser_fetch"
    assert data["provider"] == "tavily"
    assert data["title"] == "Example Post"
    assert data["truncated"] is True
    assert len(data["content"]) == 10
    assert data["images"] == ["https://example.com/a.png"]
