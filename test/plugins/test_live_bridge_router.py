"""live_bridge 输入规范化测试。"""

from plugins.live_bridge.router.openai_router import (
    _get_last_user_content,
    _normalize_live_comment,
)


def test_live_bridge_prefers_last_user_message() -> None:
    messages = [
        type("Msg", (), {"role": "system", "content": "sys"})(),
        type("Msg", (), {"role": "user", "content": "first"})(),
        type("Msg", (), {"role": "assistant", "content": "reply"})(),
        type("Msg", (), {"role": "user", "content": "last"})(),
    ]

    assert _get_last_user_content(messages) == "last"


def test_live_bridge_normalizes_legacy_prefixed_viewer_template() -> None:
    viewer, comment = _normalize_live_comment('请简要回复:观众“测试用户”说：000')

    assert viewer == "测试用户"
    assert comment == "000"


def test_live_bridge_keeps_plain_comment_when_no_template() -> None:
    viewer, comment = _normalize_live_comment("今晚吃什么")

    assert viewer == ""
    assert comment == "今晚吃什么"
