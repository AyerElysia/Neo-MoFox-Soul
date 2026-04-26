"""proactive_message_plugin 配置默认值测试。"""

from __future__ import annotations

from plugins.proactive_message_plugin.config import ProactiveMessageConfig


def test_decision_mode_defaults_to_chatter() -> None:
    config = ProactiveMessageConfig()

    assert config.settings.decision_mode == "chatter"
