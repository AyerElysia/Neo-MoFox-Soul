"""default_chatter 与 life_engine 异步对话桥测试。"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from plugins.default_chatter.config import DefaultChatterConfig
from plugins.default_chatter.consult_nucleus import ConsultNucleusTool, SearchLifeMemoryTool
from plugins.default_chatter.life_memory_explorer import LifeMemoryExplorerAgent
from plugins.default_chatter.nucleus_bridge import MessageNucleusTool
from plugins.default_chatter.plugin import DefaultChatter, DefaultChatterPlugin
from src.kernel.llm import ToolRegistry


class _FakeResponse:
    """最小响应对象。"""

    def __init__(self) -> None:
        self.payloads: list[Any] = []

    def add_payload(self, payload: Any) -> None:
        self.payloads.append(payload)


def _build_chatter() -> DefaultChatter:
    config = DefaultChatterConfig.from_dict({"plugin": {"enabled": True, "mode": "enhanced"}})
    plugin = DefaultChatterPlugin(config=config)
    return DefaultChatter(stream_id="stream-default", plugin=plugin)


@pytest.mark.asyncio
async def test_message_nucleus_tool_queues_message(monkeypatch: pytest.MonkeyPatch) -> None:
    """桥接工具应把消息异步投递给 life_engine。"""
    captured: dict[str, Any] = {}

    class _FakeLifeService:
        async def enqueue_dfc_message(self, **kwargs: Any) -> dict[str, Any]:
            captured.update(kwargs)
            return {"event_id": "dfc_msg_1", "queued": True}

    class _FakePluginManager:
        def get_plugin(self, name: str) -> Any:
            if name == "life_engine":
                return SimpleNamespace(service=_FakeLifeService())
            return None

    monkeypatch.setattr(
        "plugins.default_chatter.nucleus_bridge.get_plugin_manager",
        lambda: _FakePluginManager(),
    )

    tool = MessageNucleusTool(plugin=DefaultChatterPlugin(config=DefaultChatterConfig()))
    success, result = await tool.execute(
        content="帮我问问另一个我最近在想什么",
        stream_id="stream-1",
        platform="qq",
        chat_type="private",
        sender_name="Alice",
    )

    assert success is True
    assert "不要等待即时回复" in result
    assert captured == {
        "message": "帮我问问另一个我最近在想什么",
        "stream_id": "stream-1",
        "platform": "qq",
        "chat_type": "private",
        "sender_name": "Alice",
    }


@pytest.mark.asyncio
async def test_message_nucleus_tool_fails_when_life_engine_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """life_engine 缺失时应明确失败，不得伪造已送达。"""

    class _FakePluginManager:
        def get_plugin(self, _name: str) -> None:
            return None

    monkeypatch.setattr(
        "plugins.default_chatter.nucleus_bridge.get_plugin_manager",
        lambda: _FakePluginManager(),
    )

    tool = MessageNucleusTool(plugin=DefaultChatterPlugin(config=DefaultChatterConfig()))
    success, result = await tool.execute(content="你好")

    assert success is False
    assert "life_engine 未加载" in result


@pytest.mark.asyncio
async def test_default_chatter_run_tool_call_autofills_nucleus_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """运行桥接工具时应自动补齐当前对话上下文。"""
    chatter = _build_chatter()
    captured: dict[str, Any] = {}

    async def _fake_exec_llm_usable(_usable_cls: Any, _message: Any, **kwargs: Any) -> tuple[bool, str]:
        captured.update(kwargs)
        return True, "queued"

    monkeypatch.setattr(chatter, "exec_llm_usable", _fake_exec_llm_usable)

    registry = ToolRegistry()
    registry.register(MessageNucleusTool)
    response = _FakeResponse()
    trigger_msg = SimpleNamespace(
        stream_id="stream-42",
        platform="qq",
        chat_type="group",
        sender_name="Alice",
    )
    call = SimpleNamespace(
        id="call-1",
        name="tool-message_nucleus",
        args={"message": "替我问问另一个我"},
    )

    appended, exec_success = await chatter.run_tool_call(
        call=call,
        response=response,
        usable_map=registry,
        trigger_msg=trigger_msg,
    )

    assert appended is True
    assert exec_success is True
    assert captured["content"] == "替我问问另一个我"
    assert captured["stream_id"] == "stream-42"
    assert captured["platform"] == "qq"
    assert captured["chat_type"] == "group"
    assert captured["sender_name"] == "Alice"


@pytest.mark.asyncio
async def test_default_chatter_run_tool_call_accepts_legacy_message_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """旧参数名 message 仍应被兼容转换，避免热更新后炸掉。"""
    chatter = _build_chatter()
    captured: dict[str, Any] = {}

    async def _fake_exec_llm_usable(_usable_cls: Any, _message: Any, **kwargs: Any) -> tuple[bool, str]:
        captured.update(kwargs)
        return True, "queued"

    monkeypatch.setattr(chatter, "exec_llm_usable", _fake_exec_llm_usable)

    registry = ToolRegistry()
    registry.register(MessageNucleusTool)
    response = _FakeResponse()
    trigger_msg = SimpleNamespace(
        stream_id="stream-88",
        platform="qq",
        chat_type="private",
        sender_name="Alice",
    )
    call = SimpleNamespace(
        id="call-2",
        name="tool-message_nucleus",
        args={"message": "旧字段也要能工作"},
    )

    appended, exec_success = await chatter.run_tool_call(
        call=call,
        response=response,
        usable_map=registry,
        trigger_msg=trigger_msg,
    )

    assert appended is True
    assert exec_success is True
    assert captured["content"] == "旧字段也要能工作"
    assert "message" not in captured


def test_default_chatter_plugin_exposes_message_nucleus_tool() -> None:
    """插件组件列表应包含中枢桥接工具。"""
    plugin = DefaultChatterPlugin(config=DefaultChatterConfig())

    components = plugin.get_components()

    assert MessageNucleusTool in components
    assert ConsultNucleusTool in components
    assert LifeMemoryExplorerAgent in components
    assert SearchLifeMemoryTool not in components
    assert MessageNucleusTool.chatter_allow == ["default_chatter"]
    assert ConsultNucleusTool.chatter_allow == ["default_chatter"]
    assert LifeMemoryExplorerAgent.chatter_allow == ["default_chatter", "life_chatter"]


@pytest.mark.anyio
async def test_consult_nucleus_tool_uses_formal_actor_context_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """consult_nucleus 应调用 life service 的正式状态查询接口。"""

    class _FakeLifeService:
        async def query_actor_context(self, query: str) -> str:
            assert query == "最近在想什么"
            return "【当前状态】一切正常"

    class _FakePluginManager:
        def get_plugin(self, name: str) -> Any:
            if name == "life_engine":
                return SimpleNamespace(service=_FakeLifeService())
            return None

    monkeypatch.setattr(
        "plugins.default_chatter.consult_nucleus.get_plugin_manager",
        lambda: _FakePluginManager(),
    )

    tool = ConsultNucleusTool(plugin=DefaultChatterPlugin(config=DefaultChatterConfig()))
    success, result = await tool.execute(query="最近在想什么")

    assert success is True
    assert result == "【当前状态】一切正常"


@pytest.mark.anyio
async def test_search_life_memory_tool_uses_formal_memory_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """search_life_memory 应调用 life service 的正式深度记忆检索接口。"""

    class _FakeLifeService:
        async def search_actor_memory(self, query: str, top_k: int) -> str:
            assert query == "旧计划"
            assert top_k == 3
            return "【直接命中的记忆】\n- 计划A"

    class _FakePluginManager:
        def get_plugin(self, name: str) -> Any:
            if name == "life_engine":
                return SimpleNamespace(service=_FakeLifeService())
            return None

    monkeypatch.setattr(
        "plugins.default_chatter.consult_nucleus.get_plugin_manager",
        lambda: _FakePluginManager(),
    )

    tool = SearchLifeMemoryTool(plugin=DefaultChatterPlugin(config=DefaultChatterConfig()))
    success, result = await tool.execute(query="旧计划", top_k=3)

    assert success is True
    assert "计划A" in result


@pytest.mark.anyio
async def test_life_memory_explorer_agent_runs_private_search_then_finish(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """life_memory_explorer 应通过私有工具循环返回 finish 内容。"""

    class _FakeAgentResponse:
        def __init__(self, calls: list[Any], text: str = "") -> None:
            self.call_list = calls
            self.text = text
            self.payloads: list[Any] = []
            self._next: "_FakeAgentResponse | None" = None

        def __await__(self):
            async def _done() -> str:
                return self.text

            return _done().__await__()

        def add_payload(self, payload: Any) -> None:
            self.payloads.append(payload)

        async def send(self, stream: bool = False) -> "_FakeAgentResponse":
            assert stream is False
            assert self._next is not None
            return self._next

    class _FakeRequest:
        def __init__(self) -> None:
            self.payloads: list[Any] = []
            first = _FakeAgentResponse([
                SimpleNamespace(
                    id="search-1",
                    name="tool-life_memory_search",
                    args={"query": "旧计划", "top_k": 3},
                )
            ])
            second = _FakeAgentResponse([
                SimpleNamespace(
                    id="finish-1",
                    name="tool-memory_finish_task",
                    args={"content": "核心结论：找到计划A。"},
                )
            ])
            first._next = second
            self._responses = [first]

        def add_payload(self, payload: Any) -> None:
            self.payloads.append(payload)

        async def send(self, stream: bool = False) -> _FakeAgentResponse:
            assert stream is False
            return self._responses.pop(0)

    monkeypatch.setattr(
        "plugins.default_chatter.life_memory_explorer.get_model_set_by_task",
        lambda task: SimpleNamespace(task=task),
    )
    monkeypatch.setattr(
        LifeMemoryExplorerAgent,
        "create_llm_request",
        lambda self, **kwargs: _FakeRequest(),
    )

    captured: dict[str, Any] = {}

    async def _fake_execute_local_usable(name: str, _message: Any, **kwargs: Any) -> tuple[bool, str]:
        captured["name"] = name
        captured["kwargs"] = kwargs
        return True, "【直接命中的记忆】计划A"

    agent = LifeMemoryExplorerAgent(
        stream_id="stream-default",
        plugin=DefaultChatterPlugin(config=DefaultChatterConfig()),
    )
    monkeypatch.setattr(agent, "execute_local_usable", _fake_execute_local_usable)

    success, result = await agent.execute(query="旧计划", detail_level="normal", max_results=3)

    assert success is True
    assert result == "核心结论：找到计划A。"
    assert captured == {
        "name": "life_memory_search",
        "kwargs": {"query": "旧计划", "top_k": 3},
    }


@pytest.mark.anyio
async def test_life_memory_explorer_agent_falls_back_to_plain_text_when_finish_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """life_memory_explorer 在模型未调用 memory_finish_task 时应接受纯文本结束结果。"""

    class _FakeAgentResponse:
        def __init__(self, calls: list[Any], text: str = "") -> None:
            self.call_list = calls
            self.text = text
            self.payloads: list[Any] = []
            self._next: "_FakeAgentResponse | None" = None

        def __await__(self):
            async def _done() -> str:
                return self.text

            return _done().__await__()

        def add_payload(self, payload: Any) -> None:
            self.payloads.append(payload)

        async def send(self, stream: bool = False) -> "_FakeAgentResponse":
            assert stream is False
            assert self._next is not None
            return self._next

    class _FakeRequest:
        def __init__(self) -> None:
            self.payloads: list[Any] = []
            first = _FakeAgentResponse([
                SimpleNamespace(
                    id="search-1",
                    name="tool-life_memory_search",
                    args={"query": "旧计划", "top_k": 3},
                )
            ])
            second = _FakeAgentResponse([], text="核心结论：找到计划A。")
            first._next = second
            self._responses = [first]

        def add_payload(self, payload: Any) -> None:
            self.payloads.append(payload)

        async def send(self, stream: bool = False) -> _FakeAgentResponse:
            assert stream is False
            return self._responses.pop(0)

    monkeypatch.setattr(
        "plugins.default_chatter.life_memory_explorer.get_model_set_by_task",
        lambda task: SimpleNamespace(task=task),
    )
    monkeypatch.setattr(
        LifeMemoryExplorerAgent,
        "create_llm_request",
        lambda self, **kwargs: _FakeRequest(),
    )

    captured: dict[str, Any] = {}

    async def _fake_execute_local_usable(name: str, _message: Any, **kwargs: Any) -> tuple[bool, str]:
        captured["name"] = name
        captured["kwargs"] = kwargs
        return True, "【直接命中的记忆】计划A"

    agent = LifeMemoryExplorerAgent(
        stream_id="stream-default",
        plugin=DefaultChatterPlugin(config=DefaultChatterConfig()),
    )
    monkeypatch.setattr(agent, "execute_local_usable", _fake_execute_local_usable)

    success, result = await agent.execute(query="旧计划", detail_level="normal", max_results=3)

    assert success is True
    assert result == "核心结论：找到计划A。"
    assert captured == {
        "name": "life_memory_search",
        "kwargs": {"query": "旧计划", "top_k": 3},
    }
