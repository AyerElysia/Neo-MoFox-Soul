"""life_engine 社交主动性工具集。

为中枢提供直接发起话题的能力——不只是留言，而是直接说出来。
"""

from __future__ import annotations

import string
from typing import Annotated, Any
from uuid import uuid4

from src.core.components import BaseTool
from src.app.plugin_system.api import log_api
from src.app.plugin_system.api import stream_api
from src.core.models.message import Message, MessageType

logger = log_api.get_logger("life_engine.social_tools")


def _looks_like_stream_hash(value: str) -> bool:
    """判断是否像内部生成的 stream_id（SHA-256 十六进制串）。"""
    text = str(value or "").strip().lower()
    return len(text) == 64 and all(ch in string.hexdigits for ch in text)


def _apply_stream_info(chat_stream: Any, stream_info: dict[str, Any] | None) -> None:
    """用数据库中的流信息补齐运行时 ChatStream。"""
    if chat_stream is None or not stream_info:
        return

    platform = str(stream_info.get("platform") or "").strip()
    chat_type = str(stream_info.get("chat_type") or "").strip()
    stream_name = str(stream_info.get("group_name") or "").strip()

    if platform and not str(getattr(chat_stream, "platform", "") or "").strip():
        chat_stream.platform = platform
    if chat_type and not str(getattr(chat_stream, "chat_type", "") or "").strip():
        chat_stream.chat_type = chat_type
    if stream_name and not str(getattr(chat_stream, "stream_name", "") or "").strip():
        chat_stream.stream_name = stream_name


async def _safe_get_stream_info(stream_id: str) -> dict[str, Any] | None:
    """安全获取 stream_info。"""
    if not stream_id:
        return None

    try:
        from src.core.managers import get_stream_manager

        return await get_stream_manager().get_stream_info(stream_id)
    except Exception:
        return None


async def _find_stream_record_by_group_id(
    group_id: str,
    *,
    preferred_platform: str = "",
) -> dict[str, Any] | None:
    """按原始群号查找最近活跃的聊天流记录。"""
    target_group_id = str(group_id or "").strip()
    if not target_group_id:
        return None

    from src.core.models.sql_alchemy import ChatStreams
    from src.kernel.db import QueryBuilder

    if preferred_platform:
        preferred_record = await (
            QueryBuilder(ChatStreams)
            .filter(group_id=target_group_id, platform=preferred_platform)
            .order_by("-last_active_time")
            .first(as_dict=True)
        )
        if isinstance(preferred_record, dict):
            return preferred_record

    record = await (
        QueryBuilder(ChatStreams)
        .filter(group_id=target_group_id)
        .order_by("-last_active_time")
        .first(as_dict=True)
    )
    return record if isinstance(record, dict) else None


class NucleusInitiateTopicTool(BaseTool):
    """直接在聊天流中发起话题。"""

    tool_name: str = "nucleus_initiate_topic"
    tool_description: str = (
        "直接在指定聊天流中发起一个话题或说一句话。"
        "这是你主动表达的最直接方式——不是留言，而是直接说出来。"
        "\n\n"
        "**使用场景：**\n"
        "- 想分享什么有趣的发现\n"
        "- 想主动关心某人\n"
        "- 想打破沉默\n"
        "- 想讨论一个你正在思考的话题\n"
        "- 想发起一个讨论\n"
        "\n"
        "**与 nucleus_tell_dfc 的区别：**\n"
        "- nucleus_tell_dfc: 只补充表达层当前可能没看到的信息差/背景\n"
        "- nucleus_initiate_topic: 直接送出消息，立即可见\n"
        "\n"
        "**注意：** 这是较强力的主动行为，请确保有真正的表达欲，不要频繁使用。"
        "每小时最多主动发起 5 次话题。"
    )
    chatter_allow: list[str] = ["life_engine_internal"]

    # 主动发起频率限制
    _MAX_INITIATES_PER_HOUR: int = 5

    def __init__(self, plugin) -> None:
        super().__init__(plugin)
        self._recent_initiates: list[float] = []

    async def _resolve_target_stream(
        self,
        target_ref: str,
    ) -> tuple[Any | None, str, dict[str, Any] | None]:
        """把目标引用解析成一个可发送的聊天流。"""
        raw_target_ref = str(target_ref or "").strip()
        if not raw_target_ref:
            return None, "", None

        current_stream = getattr(self, "chat_stream", None)
        preferred_platform = str(getattr(current_stream, "platform", "") or "").strip()
        preferred_chat_type = str(getattr(current_stream, "chat_type", "") or "").strip().lower()

        chat_stream = await stream_api.get_stream(raw_target_ref)
        if chat_stream is None:
            chat_stream = await stream_api.build_stream_from_database(raw_target_ref)

        resolved_stream_id = raw_target_ref
        stream_info: dict[str, Any] | None = None
        if chat_stream is not None:
            resolved_stream_id = str(getattr(chat_stream, "stream_id", "") or raw_target_ref)
            stream_info = await _safe_get_stream_info(resolved_stream_id)
            _apply_stream_info(chat_stream, stream_info)
            if str(getattr(chat_stream, "platform", "") or "").strip():
                return chat_stream, resolved_stream_id, stream_info

        if not _looks_like_stream_hash(raw_target_ref):
            record = await _find_stream_record_by_group_id(
                raw_target_ref,
                preferred_platform=preferred_platform,
            )
            if isinstance(record, dict):
                candidate_stream_id = str(record.get("stream_id") or "").strip()
                if candidate_stream_id:
                    candidate_stream = await stream_api.get_stream(candidate_stream_id)
                    if candidate_stream is None:
                        candidate_stream = await stream_api.build_stream_from_database(
                            candidate_stream_id
                        )
                    candidate_info = await _safe_get_stream_info(candidate_stream_id)
                    _apply_stream_info(candidate_stream, candidate_info)
                    if (
                        candidate_stream is not None
                        and str(getattr(candidate_stream, "platform", "") or "").strip()
                    ):
                        return candidate_stream, candidate_stream_id, candidate_info

            if preferred_platform:
                inferred_chat_type = preferred_chat_type if preferred_chat_type in {
                    "private",
                    "group",
                    "discuss",
                } else "group"
                try:
                    if inferred_chat_type == "private":
                        candidate_stream = await stream_api.get_or_create_stream(
                            platform=preferred_platform,
                            user_id=raw_target_ref,
                            chat_type="private",
                        )
                    else:
                        candidate_stream = await stream_api.get_or_create_stream(
                            platform=preferred_platform,
                            group_id=raw_target_ref,
                            chat_type="group",
                        )
                except Exception as exc:
                    logger.warning(
                        "根据原始目标ID补建聊天流失败: "
                        f"target={raw_target_ref} platform={preferred_platform} error={exc}"
                    )
                else:
                    candidate_stream_id = str(
                        getattr(candidate_stream, "stream_id", "") or raw_target_ref
                    )
                    candidate_info = await _safe_get_stream_info(candidate_stream_id)
                    _apply_stream_info(candidate_stream, candidate_info)
                    if (
                        candidate_stream is not None
                        and str(getattr(candidate_stream, "platform", "") or "").strip()
                    ):
                        return candidate_stream, candidate_stream_id, candidate_info

        return chat_stream, resolved_stream_id, stream_info

    async def execute(
        self,
        content: Annotated[str, "要说的话，自然、感性，像自己想说的"],
        stream_id: Annotated[str, "目标聊天流ID（空=最近活跃的流）"] = "",
        reason: Annotated[str, "为什么想说这句话"] = "",
    ) -> tuple[bool, str]:
        """直接在聊天流中发起话题。"""
        import time

        text = str(content or "").strip()
        if not text:
            return False, "content 不能为空"

        # 频率限制
        now = time.time()
        one_hour_ago = now - 3600
        self._recent_initiates = [
            t for t in self._recent_initiates if t > one_hour_ago
        ]
        if len(self._recent_initiates) >= self._MAX_INITIATES_PER_HOUR:
            return False, (
                f"每小时最多主动发起 {self._MAX_INITIATES_PER_HOUR} 次话题，"
                "请稍后再试或使用 nucleus_tell_dfc 留言。"
            )

        # 获取目标流
        target_stream_id = str(stream_id or "").strip()
        if not target_stream_id:
            from .file_tools import _pick_latest_target_stream_id
            target_stream_id = _pick_latest_target_stream_id(self.plugin) or ""

        if not target_stream_id:
            # 尝试从活跃聊天流中寻找候选
            try:
                from src.core.managers import get_stream_manager
                sm = get_stream_manager()
                if sm:
                    candidates = sm.get_active_streams(limit=5) if hasattr(sm, 'get_active_streams') else []
                    for s in candidates:
                        if getattr(s, 'stream_type', '') in ("group", "private"):
                            target_stream_id = s.stream_id
                            break
            except Exception:
                pass

        if not target_stream_id:
            return False, "暂时没有可用的聊天流，下次有对话时再说吧。没关系的～"

        # 发送消息
        try:
            original_target_ref = target_stream_id
            chat_stream, target_stream_id, stream_info = await self._resolve_target_stream(
                target_stream_id
            )
            if chat_stream is None:
                return False, f"聊天流 {original_target_ref} 不存在"

            target_platform = str(getattr(chat_stream, "platform", "") or "").strip()
            target_chat_type = (
                str(getattr(chat_stream, "chat_type", "") or "").strip()
                or str((stream_info or {}).get("chat_type") or "").strip()
            )

            if not target_platform:
                return False, f"无法确定聊天流 {original_target_ref} 的平台信息"

            if target_chat_type and not str(getattr(chat_stream, "chat_type", "") or "").strip():
                chat_stream.chat_type = target_chat_type

            target_extra: dict[str, Any] = {}
            if target_chat_type == "group":
                group_id = str((stream_info or {}).get("group_id") or "").strip()
                group_name = str((stream_info or {}).get("group_name") or "").strip()
                if not group_id and not _looks_like_stream_hash(original_target_ref):
                    group_id = original_target_ref
                if group_id:
                    target_extra["target_group_id"] = group_id
                if group_name:
                    target_extra["target_group_name"] = group_name

            if target_stream_id != original_target_ref:
                logger.info(
                    "主动话题目标流已解析: "
                    f"input={original_target_ref} resolved={target_stream_id} "
                    f"platform={target_platform} chat_type={target_chat_type or 'unknown'}"
                )

            msg = Message(
                message_id=f"life_engine_proactive_{uuid4().hex}",
                content=text,
                processed_plain_text=text,
                message_type=MessageType.TEXT,
                sender_id="life_engine_proactive",
                platform=target_platform,
                chat_type=target_chat_type,
                stream_id=target_stream_id,
                source="nucleus_initiate_topic",
                reason=reason,
                **target_extra,
            )

            # 尝试通过消息发送器发送
            try:
                from src.core.transport import get_message_sender
                sender = get_message_sender()
                if sender:
                    await sender.send_message(msg)
                    self._recent_initiates.append(now)
                    logger.info(
                        f"中枢主动发起话题: stream={target_stream_id} "
                        f"content={text[:50]}... reason={reason}"
                    )
                    return True, f"已发起话题: {text[:50]}"
            except ImportError:
                pass

            # 回退：通过系统提醒注入
            try:
                context = getattr(chat_stream, "context", None)
                if context and hasattr(context, "add_system_reminder"):
                    context.add_system_reminder(
                        f"[爱莉主动想说] {text}",
                        source="nucleus_initiate_topic",
                    )
                    self._recent_initiates.append(now)
                    logger.info(
                        f"中枢通过系统提醒发起话题: stream={target_stream_id}"
                    )
                    return True, f"已通过系统提醒发起话题: {text[:50]}"
            except Exception as e:
                logger.warning(f"系统提醒注入失败: {e}")

            return False, "无法发送消息，请使用 nucleus_tell_dfc 留言"

        except Exception as e:
            logger.error(f"发起话题失败: {e}", exc_info=True)
            return False, f"发起话题失败: {e}"


SOCIAL_TOOLS = [
    NucleusInitiateTopicTool,
]
