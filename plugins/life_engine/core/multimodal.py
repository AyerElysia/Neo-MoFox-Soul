"""life_chatter 原生全模态辅助模块。

负责把 unread_msgs 中的 image / emoji / video / voice / record / audio 媒体
转换为 LLM 原生 Image / Video / Audio Content 注入到 USER payload，让
全模态模型（如 MiMo-V2-Omni）可以直接消费媒体而不依赖 ASR/描述文本。

与 plugins/default_chatter/multimodal.py 的差异：
- 扩展支持 audio / voice / record（default_chatter 无此分支）
- MediaItem 携带 mime_type 与 source_message_id（用于 dedup 与失败重试）
- 三类媒体（image+emoji / video / audio）使用独立预算，互不抢占
- 不可识别的音频格式（如 silk/amr）降级为文本占位，避免 LLM 拒收

输出形态：
- 图片 / 表情包 → 前置 ``[图片]`` / ``[表情包]`` 文本占位 + Image
- 视频 → 前置 ``[视频]`` 文本占位 + Video
- 语音 → 前置 ``[语音]`` 文本占位 + Audio；mime 不识别时只输出占位文本
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from src.kernel.llm import Audio, Content, Image, Text, Video

if TYPE_CHECKING:
    from src.core.models.message import Message


# napcat record 已请求 `out_format=wav`；其它适配器若未指定 mime，按此默认。
_DEFAULT_VOICE_MIME = "audio/wav"

# OpenAI Chat Completions input_audio.format 仅接受 mp3 / wav，
# 其它 mime 进入 build 阶段时会降级为占位 Text。
_SUPPORTED_AUDIO_MIMES: frozenset[str] = frozenset(
    {
        "audio/mpeg",
        "audio/mp3",
        "audio/wav",
        "audio/x-wav",
        "audio/wave",
        "audio/vnd.wave",
    }
)

_VOICE_TYPES: frozenset[str] = frozenset({"voice", "record", "audio"})
_IMAGE_TYPES: frozenset[str] = frozenset({"image", "emoji"})


@dataclass
class MediaItem:
    """从消息中提取的媒体条目。"""

    media_type: str  # 归一化后：image / emoji / video / audio
    raw_data: str
    source_message_id: str
    mime_type: str = ""
    duration_seconds: float = 0.0


@dataclass
class MediaBudget:
    """三类媒体的独立预算追踪。"""

    max_images: int = 4
    max_videos: int = 1
    max_audios: int = 2
    _images: int = field(default=0, init=False)
    _videos: int = field(default=0, init=False)
    _audios: int = field(default=0, init=False)

    def can_take(self, media_type: str) -> bool:
        """检查指定类型是否仍有预算（不消耗）。"""
        if media_type in _IMAGE_TYPES:
            return self._images < self.max_images
        if media_type == "video":
            return self._videos < self.max_videos
        if media_type == "audio":
            return self._audios < self.max_audios
        return False

    def consume(self, media_type: str) -> bool:
        """消耗预算；预算不足返回 False（不消耗）。"""
        if not self.can_take(media_type):
            return False
        if media_type in _IMAGE_TYPES:
            self._images += 1
        elif media_type == "video":
            self._videos += 1
        elif media_type == "audio":
            self._audios += 1
        return True

    def is_exhausted(self) -> bool:
        return (
            self._images >= self.max_images
            and self._videos >= self.max_videos
            and self._audios >= self.max_audios
        )


def extract_media_from_messages(
    messages: list["Message"],
    budget: MediaBudget,
    *,
    enable_image: bool = True,
    enable_video: bool = True,
    enable_audio: bool = True,
    audio_max_seconds: int = 60,
) -> list[MediaItem]:
    """从消息列表中提取媒体条目，按预算与开关过滤。

    顺序遵循输入 messages 的原始顺序（通常即消息时间顺序），
    达到预算上限的类型会跳过后续同类。
    """
    items: list[MediaItem] = []
    for msg in messages:
        if budget.is_exhausted():
            break

        media_list = get_media_list(msg)
        if not media_list:
            continue

        msg_id = str(getattr(msg, "message_id", "") or "")
        for media in media_list:
            media_type_raw = str(media.get("type", "")).lower()
            if not media_type_raw:
                continue

            normalized_type, mime_type, duration = _classify_media(media_type_raw, media)
            if normalized_type is None:
                continue
            if normalized_type in _IMAGE_TYPES and not enable_image:
                continue
            if normalized_type == "video" and not enable_video:
                continue
            if normalized_type == "audio" and not enable_audio:
                continue
            if normalized_type == "audio" and duration and duration > audio_max_seconds:
                # 单段过长的语音降级，避免 base64 体积爆炸
                continue

            data = _extract_media_data(normalized_type, media.get("data", ""))
            if not data:
                continue

            if not budget.consume(normalized_type):
                continue

            items.append(
                MediaItem(
                    media_type=normalized_type,
                    raw_data=data,
                    source_message_id=msg_id,
                    mime_type=mime_type,
                    duration_seconds=float(duration or 0.0),
                )
            )
    return items


def build_multimodal_content(
    text: str,
    media_items: list[MediaItem],
    *,
    unsupported_audio_placeholder: str = "[语音消息]",
) -> list[Content]:
    """构建 Text + Image/Video/Audio 混合 content 列表。

    text 始终位于第一位；后续按 media_items 顺序追加，
    每条媒体前置语义占位文本（[图片]/[表情包]/[视频]/[语音]），
    便于纯文本回退或失败重试时仍能感知"这里有过媒体"。
    """
    content_list: list[Content] = []
    if text:
        content_list.append(Text(text))

    for item in media_items:
        if item.media_type == "emoji":
            content_list.append(Text("[表情包]"))
            content_list.append(Image(item.raw_data))
        elif item.media_type == "image":
            content_list.append(Text("[图片]"))
            content_list.append(Image(item.raw_data))
        elif item.media_type == "video":
            mime = item.mime_type or "video/mp4"
            content_list.append(Text("[视频]"))
            content_list.append(Video(item.raw_data, mime_type=mime))
        elif item.media_type == "audio":
            mime = (item.mime_type or _DEFAULT_VOICE_MIME).lower()
            if mime in _SUPPORTED_AUDIO_MIMES:
                content_list.append(Text("[语音]"))
                content_list.append(Audio(item.raw_data, mime_type=mime))
            else:
                # 未知/不支持的格式（silk/amr/...）：降级为文本占位，不生成 Audio
                content_list.append(Text(unsupported_audio_placeholder))
    return content_list


def get_media_list(msg: "Message") -> list[dict[str, Any]]:
    """从 Message 对象中提取 media 列表（兼容 content.media / extra.media / msg.media）。"""
    collected: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def extend_media(source: Any) -> None:
        if not isinstance(source, list):
            return
        for item in source:
            if not isinstance(item, dict):
                continue
            media_type = str(item.get("type", "")).lower()
            if not media_type:
                continue
            raw_key = (
                item.get("data")
                or item.get("base64")
                or item.get("path")
                or item.get("url")
                or item.get("file")
            )
            key = (media_type, str(raw_key))
            if key in seen:
                continue
            seen.add(key)
            collected.append(item)

    content = getattr(msg, "content", None)
    if isinstance(content, dict):
        extend_media(content.get("media"))

    extra = getattr(msg, "extra", {})
    if isinstance(extra, dict):
        extend_media(extra.get("media"))

    media = getattr(msg, "media", None)
    extend_media(media)

    if collected:
        return collected

    msg_type = getattr(msg, "message_type", None)
    if (
        msg_type is not None
        and str(msg_type).lower() == "emoji"
        and isinstance(content, str)
        and len(content) > 100
    ):
        data = content if content.startswith("base64|") else f"base64|{content}"
        return [{"type": "emoji", "data": data}]

    return []


# ─── 内部辅助 ─────────────────────────────


def _classify_media(
    media_type_raw: str,
    media: dict[str, Any],
) -> tuple[str | None, str, float]:
    """归一化媒体类型并提取 mime / 时长。

    Returns:
        (normalized_type, mime_type, duration_seconds)；当类型不识别时返回 (None, "", 0)。
    """
    if media_type_raw in _IMAGE_TYPES:
        mime = _read_str(media, ("mime", "mime_type", "format")) or ""
        return media_type_raw, mime, 0.0

    if media_type_raw == "video":
        mime = _read_str(media, ("mime", "mime_type", "format")) or "video/mp4"
        duration = _read_float(media, ("duration", "duration_seconds"))
        return "video", mime, duration

    if media_type_raw in _VOICE_TYPES:
        mime = _read_str(media, ("mime", "mime_type", "format")) or _DEFAULT_VOICE_MIME
        # format 字段如果是简短形式（"wav"/"mp3"）补全为 audio/<x>
        if "/" not in mime:
            mime = f"audio/{mime.lower()}"
        duration = _read_float(media, ("duration", "duration_seconds"))
        return "audio", mime.lower(), duration

    return None, "", 0.0


def _read_str(d: dict[str, Any], keys: tuple[str, ...]) -> str:
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _read_float(d: dict[str, Any], keys: tuple[str, ...]) -> float:
    for k in keys:
        v = d.get(k)
        if isinstance(v, (int, float)) and v > 0:
            return float(v)
        if isinstance(v, str):
            try:
                f = float(v)
                if f > 0:
                    return f
            except ValueError:
                continue
    return 0.0


def _extract_media_data(media_type: str, raw_data: Any) -> str:
    """提取媒体原始数据（base64/data-url/path）。"""
    if isinstance(raw_data, str):
        return _normalize_multimodal_media_data(raw_data)

    if isinstance(raw_data, dict):
        if media_type == "video":
            keys = ("base64", "data", "video_base64", "url", "path", "file")
        elif media_type == "audio":
            keys = ("base64", "data", "audio_base64", "url", "path", "file")
        else:
            keys = ("data", "base64", "url", "path", "file")

        for key in keys:
            value = raw_data.get(key)
            if isinstance(value, str) and value.strip():
                return _normalize_multimodal_media_data(value)

        nested_media = raw_data.get("media")
        if isinstance(nested_media, list):
            for item in nested_media:
                if not isinstance(item, dict):
                    continue
                for key in ("data", "base64", "url", "path", "file"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        return _normalize_multimodal_media_data(value)
    return ""


def _normalize_multimodal_media_data(value: str) -> str:
    """把不同来源的媒体前缀统一成 kernel File 可消费的形式。"""
    if value.startswith("base64://"):
        return f"base64|{value[len('base64://'):]}"
    return value


__all__ = [
    "MediaItem",
    "MediaBudget",
    "extract_media_from_messages",
    "build_multimodal_content",
    "get_media_list",
]
