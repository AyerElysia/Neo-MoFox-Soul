"""default_chatter 子判定提示词回归测试。"""

from __future__ import annotations

from plugins.default_chatter.plugin import sub_agent_system_prompt


def test_sub_agent_prompt_should_not_contain_hardcoded_personal_rules() -> None:
    """子判定提示词不应包含历史私货的人名定制规则。"""
    assert "希羽" not in sub_agent_system_prompt
    assert "真我的爱莉希雅" not in sub_agent_system_prompt
