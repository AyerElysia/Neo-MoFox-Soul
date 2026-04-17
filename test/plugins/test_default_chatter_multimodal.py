from __future__ import annotations

from src.core.models.message import Message, MessageType
from src.kernel.llm import Image, Text, Video
from plugins.default_chatter.multimodal import (
    MediaItem,
    build_multimodal_content,
    extract_media_from_messages,
)


def test_extract_media_from_messages_reads_content_and_extra_media() -> None:
    """多模态链路应从 content.media / extra.media 里提取可用媒体。"""
    message = Message(
        message_id="msg-200",
        content={
            "text": "看图",
            "media": [
                {"type": "image", "data": "base64://QUJD"},
                {
                    "type": "video",
                    "data": {"base64": "base64|RkZGRg==", "filename": "clip.mp4"},
                },
            ],
        },
        message_type=MessageType.TEXT,
        sender_id="user-200",
        sender_name="Alice",
        platform="qq",
        chat_type="private",
        stream_id="stream-200",
        media=[
            {"type": "emoji", "data": "base64|R0hJ"},
        ],
    )

    items = extract_media_from_messages([message], max_images=4, max_videos=1)

    assert [(item.media_type, item.raw_data) for item in items] == [
        ("image", "base64|QUJD"),
        ("video", "base64|RkZGRg=="),
        ("emoji", "base64|R0hJ"),
    ]
    assert [item.source_message_id for item in items] == ["msg-200", "msg-200", "msg-200"]


def test_extract_media_from_messages_ignores_voice_for_native_multimodal() -> None:
    """语音应保留给 ASR 链路，不进入默认原生多模态内容。"""
    message = Message(
        message_id="msg-201",
        content={
            "text": "听一下",
            "media": [
                {"type": "voice", "data": "base64|QUJD"},
                {"type": "image", "data": "base64|RkZGRg=="},
            ],
        },
        message_type=MessageType.TEXT,
        sender_id="user-201",
        sender_name="Bob",
        platform="qq",
        chat_type="private",
        stream_id="stream-201",
    )

    items = extract_media_from_messages([message], max_images=4, max_videos=1)

    assert [(item.media_type, item.raw_data) for item in items] == [("image", "base64|RkZGRg==")]


def test_build_multimodal_content_keeps_media_order() -> None:
    """多模态 content 组装应保持文本、图片、视频、表情的顺序。"""
    items = [
        MediaItem(media_type="image", raw_data="QUJD", source_message_id="m1"),
        MediaItem(media_type="video", raw_data="RkZGRg==", source_message_id="m1"),
        MediaItem(media_type="emoji", raw_data="R0hJ", source_message_id="m1"),
    ]

    content = build_multimodal_content("prompt", items)

    assert isinstance(content[0], Text)
    assert isinstance(content[1], Image)
    assert isinstance(content[2], Text)
    assert isinstance(content[3], Video)
    assert isinstance(content[4], Text)
    assert isinstance(content[5], Image)
