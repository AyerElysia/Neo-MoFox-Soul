"""Default Chatter 提示词构建模块。"""

from __future__ import annotations

import os
import random
import re
from collections.abc import Callable

from src.core.components.types import ChatType
from src.core.config import get_core_config
from src.core.models.message import Message
from src.core.models.stream import ChatStream
from src.core.prompt import get_prompt_manager
from src.kernel.llm import LLMPayload, ROLE, Text

from .config import DefaultChatterConfig


class DefaultChatterPromptBuilder:
    """Default Chatter 提示词构建器。"""

    _DYNAMIC_ACTOR_EXTRA_START = "<runtime_state_block>"
    _DYNAMIC_ACTOR_EXTRA_END = "</runtime_state_block>"
    _DYNAMIC_BLOCK_LIMITS: dict[str, int] = {
        "current_datetime": 240,
        "生命中枢唤醒上下文": 1200,
        "think_trigger_temp": 240,
        "subconscious": 1600,
    }

    _DYNAMIC_ACTOR_REMINDER_NAMES: tuple[str, ...] = (
        "current_datetime",
        "subconscious",
        "生命中枢唤醒上下文",
        "think_trigger_temp",
    )

    @staticmethod
    def _clamp_probability(probability: float) -> float:
        if probability < 0:
            return 0.0
        if probability > 1:
            return 1.0
        return probability

    @staticmethod
    def _should_include_persona_field(enabled: bool, probability: float) -> bool:
        if not enabled:
            return True
        return random.random() < DefaultChatterPromptBuilder._clamp_probability(
            probability
        )

    @staticmethod
    def get_mode(plugin_config: DefaultChatterConfig | None) -> str:
        """读取 DefaultChatter 执行模式。"""
        if plugin_config is not None:
            return plugin_config.plugin.mode
        return "enhanced"

    @staticmethod
    def get_dynamic_actor_reminder_names() -> tuple[str, ...]:
        """返回应从稳定前缀中排除的动态 actor reminder 名称。"""
        return DefaultChatterPromptBuilder._DYNAMIC_ACTOR_REMINDER_NAMES

    @staticmethod
    def build_negative_behaviors_extra(plugin_config: DefaultChatterConfig | None) -> str:
        """构建用于 user extra 板块的负面行为强调文本。"""
        if not (
            plugin_config is not None
            and plugin_config.plugin.reinforce_negative_behaviors
        ):
            return ""

        negative_behaviors = get_core_config().personality.negative_behaviors
        if not negative_behaviors:
            return ""

        lines = "\n".join(negative_behaviors)
        return "行为提醒：请在本轮回复中严格遵守以下约束：\n" f"{lines}"

    @staticmethod
    async def build_system_prompt(
        plugin_config: DefaultChatterConfig | None,
        chat_stream: ChatStream,
    ) -> str:
        """构建系统提示词。"""
        from src.app.plugin_system.api import adapter_api

        bot_info = await adapter_api.get_bot_info_by_platform(chat_stream.platform) or {}
        platform_name = str(
            bot_info.get("bot_name")
            or chat_stream.bot_nickname
            or "未知"
        )
        platform_id = str(
            bot_info.get("bot_id")
            or chat_stream.bot_id
            or "未知"
        )

        selected_theme_guide = ""
        if plugin_config is not None:
            chat_type_raw = str(chat_stream.chat_type or "").lower()

            if chat_type_raw == ChatType.PRIVATE.value:
                selected_theme_guide = plugin_config.plugin.theme_guide.private
            elif chat_type_raw == ChatType.GROUP.value:
                selected_theme_guide = plugin_config.plugin.theme_guide.group

        tmpl = get_prompt_manager().get_template("default_chatter_system_prompt")
        if not tmpl:
            return ""

        personality_core = ""
        personality_side = ""
        reply_style = ""
        identity = ""
        background_story = ""

        probability_enabled = (
            plugin_config is not None
            and plugin_config.plugin.probabilistic_persona_injection_enabled
        )

        try:
            personality = get_core_config().personality
        except Exception:
            personality = None

        if personality is not None:
            if plugin_config is None:
                personality_core = getattr(personality, "personality_core", "") or ""
                personality_side = getattr(personality, "personality_side", "") or ""
                reply_style = getattr(personality, "reply_style", "") or ""
                identity = getattr(personality, "identity", "") or ""
                background_story = (
                    getattr(personality, "background_story", "") or ""
                )
            else:
                settings = plugin_config.plugin
                if DefaultChatterPromptBuilder._should_include_persona_field(
                    probability_enabled,
                    settings.personality_core_injection_probability,
                ):
                    personality_core = (
                        getattr(personality, "personality_core", "") or ""
                    )
                if DefaultChatterPromptBuilder._should_include_persona_field(
                    probability_enabled,
                    settings.personality_side_injection_probability,
                ):
                    personality_side = (
                        getattr(personality, "personality_side", "") or ""
                    )
                if DefaultChatterPromptBuilder._should_include_persona_field(
                    probability_enabled,
                    settings.reply_style_injection_probability,
                ):
                    reply_style = getattr(personality, "reply_style", "") or ""
                if DefaultChatterPromptBuilder._should_include_persona_field(
                    probability_enabled,
                    settings.identity_injection_probability,
                ):
                    identity = getattr(personality, "identity", "") or ""
                if DefaultChatterPromptBuilder._should_include_persona_field(
                    probability_enabled,
                    settings.background_story_injection_probability,
                ):
                    background_story = (
                        getattr(personality, "background_story", "") or ""
                    )

        return await (
            tmpl.set("platform", chat_stream.platform)
            .set("chat_type", chat_stream.chat_type)
            .set("nickname", chat_stream.bot_nickname)
            .set("bot_id", platform_id)
            .set("platform_name", platform_name)
            .set("platform_id", platform_id)
            .set("theme_guide", selected_theme_guide)
            .set("personality_core", personality_core)
            .set("personality_side", personality_side)
            .set("reply_style", reply_style)
            .set("identity", identity)
            .set("background_story", background_story)
            .set("stream_id", chat_stream.stream_id or "")
            .set("subconscious_state", "")
            .build()
        )

    @staticmethod
    async def build_user_prompt(
        chat_stream: ChatStream,
        history_text: str,
        unread_lines: str,
        extra: str = "",
    ) -> str:
        """通过 user prompt 模板构建用户提示词。"""
        stream_name = chat_stream.stream_name
        tmpl = get_prompt_manager().get_template("default_chatter_user_prompt")
        assert tmpl, "缺少 default_chatter_user_prompt 模板，请检查提示词管理器配置"

        return await (
            tmpl
            .set("stream_name", stream_name)
            .set("history", history_text)
            .set("unreads", unread_lines)
            .set("extra", extra)
            # stream_id 不在模板占位符中，仅作为元数据随 on_prompt_build 事件 values 传递，
            # 供 notice_injector 等插件按会话区分并注入内容
            .set("stream_id", chat_stream.stream_id or "")
            .build()
        )

    @staticmethod
    def merge_extra_blocks(*blocks: str) -> str:
        """合并 extra 文本块，自动忽略空值。"""
        parts = [str(block or "").strip() for block in blocks if str(block or "").strip()]
        return "\n\n".join(parts)

    @staticmethod
    def build_dynamic_actor_extra() -> str:
        """构建应后移到 user extra 的动态 actor 上下文。"""
        from src.core.prompt import get_system_reminder_store

        store = get_system_reminder_store()
        runtime_blocks: list[str] = []

        current_datetime = store.get(bucket="actor", names=["current_datetime"])
        if current_datetime:
            runtime_blocks.append(
                DefaultChatterPromptBuilder._clip_dynamic_block(
                    "current_datetime",
                    current_datetime,
                )
            )

        wake_context = store.get(bucket="actor", names=["生命中枢唤醒上下文"])
        if wake_context:
            runtime_blocks.append(
                DefaultChatterPromptBuilder._clip_dynamic_block(
                    "生命中枢唤醒上下文",
                    wake_context,
                )
            )

        think_trigger = store.get(bucket="actor", names=["think_trigger_temp"])
        if think_trigger:
            runtime_blocks.append(
                DefaultChatterPromptBuilder._clip_dynamic_block(
                    "think_trigger_temp",
                    think_trigger,
                )
            )

        subconscious_content = store.get(bucket="actor", names=["subconscious"])
        if not subconscious_content:
            sub_file = "/root/Elysia/Neo-MoFox/data/life_engine_workspace/SUBCONSCIOUS.md"
            if os.path.exists(sub_file):
                try:
                    with open(sub_file, "r", encoding="utf-8") as f:
                        text = f.read().strip()
                    if text:
                        subconscious_content = f"[subconscious]\n{text}"
                except Exception:
                    pass
        if subconscious_content:
            runtime_blocks.append(
                DefaultChatterPromptBuilder._clip_dynamic_block(
                    "subconscious",
                    subconscious_content,
                )
            )

        if not runtime_blocks:
            return ""

        body = "\n\n".join(runtime_blocks)
        return (
            f"{DefaultChatterPromptBuilder._DYNAMIC_ACTOR_EXTRA_START}\n"
            "运行时上下文：以下信息可能会在每轮变化，供你理解当前状态，不必逐字复述。\n"
            f"{body}"
            f"\n{DefaultChatterPromptBuilder._DYNAMIC_ACTOR_EXTRA_END}"
        )

    @staticmethod
    def _clip_dynamic_block(name: str, content: str) -> str:
        """裁剪动态上下文块，避免 user extra 失控膨胀。"""
        limit = DefaultChatterPromptBuilder._DYNAMIC_BLOCK_LIMITS.get(name, 800)
        text = str(content or "").strip()
        if len(text) <= limit:
            return text
        return text[: max(0, limit - 15)].rstrip() + "\n...(已截断)"

    @staticmethod
    def append_dynamic_actor_extra(
        payload_content: object,
        dynamic_extra: str,
    ) -> object:
        """把动态运行时块作为独立文本段附加到当前 USER payload。"""
        text = str(dynamic_extra or "").strip()
        if not text:
            return payload_content

        runtime_part = Text(text)

        if isinstance(payload_content, list):
            if payload_content and isinstance(payload_content[0], Text):
                return [payload_content[0], runtime_part, *payload_content[1:]]
            return [runtime_part, *payload_content]

        if isinstance(payload_content, Text):
            return [payload_content, runtime_part]

        return [Text(str(payload_content)), runtime_part]

    @staticmethod
    def strip_dynamic_actor_extra_from_payloads(payloads: list[LLMPayload]) -> None:
        """从已存在的 USER payload 中移除旧的动态运行时块，避免跨轮堆积。"""
        for payload in payloads:
            if payload.role != ROLE.USER:
                continue

            rebuilt: list[object] = []
            changed = False

            for part in payload.content:
                if not isinstance(part, Text):
                    rebuilt.append(part)
                    continue

                cleaned = DefaultChatterPromptBuilder._strip_dynamic_actor_extra_from_text(
                    part.text
                )
                if cleaned != part.text:
                    changed = True
                if cleaned.strip():
                    rebuilt.append(Text(cleaned))

            if changed:
                payload.content = rebuilt or [Text("")]

    @staticmethod
    def _strip_dynamic_actor_extra_from_text(text: str) -> str:
        """从单段文本中剥离动态运行时块。"""
        pattern = re.compile(
            rf"\n?{re.escape(DefaultChatterPromptBuilder._DYNAMIC_ACTOR_EXTRA_START)}.*?"
            rf"{re.escape(DefaultChatterPromptBuilder._DYNAMIC_ACTOR_EXTRA_END)}\n?",
            re.DOTALL,
        )
        cleaned = pattern.sub("\n", str(text or ""))
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def build_enhanced_history_text(
        chat_stream: ChatStream,
        formatter: Callable[[Message], str],
    ) -> str:
        """构建 enhanced 模式的历史消息文本。"""
        history_lines: list[str] = []
        for msg in chat_stream.context.history_messages:
            history_lines.append(formatter(msg))

        return "\n".join(history_lines)

    @staticmethod
    async def build_classical_user_text(
        chat_stream: ChatStream,
        unread_msgs: list[Message],
        formatter: Callable[[Message], str],
        extra: str,
    ) -> str:
        """构建 classical 模式 user 提示词。"""
        history_lines = []
        for msg in chat_stream.context.history_messages:
            history_lines.append(formatter(msg))

        unread_lines = []
        for msg in unread_msgs:
            unread_lines.append(formatter(msg))

        history_block = "\n".join(history_lines) if history_lines else ""
        unread_block = "\n".join(unread_lines) if unread_lines else ""

        return await DefaultChatterPromptBuilder.build_user_prompt(
            chat_stream,
            history_text=history_block,
            unread_lines=unread_block,
            extra=extra,
        )
