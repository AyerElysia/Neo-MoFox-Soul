"""Skill system for Neo-MoFox.

提供轻量级的行为指引系统，通过 SKILL.md 文件定义 Bot 在特定场景下的行为模式。
Skill 以 YAML frontmatter + Markdown 格式定义，Bot 根据描述自主判断何时使用，
用户也可通过 /skill-name 直接调用。

用法示例:
    from src.core.skill import get_skill_manager

    manager = get_skill_manager()
    catalog = manager.generate_catalog_xml()
    body = manager.load_skill_body("cooking-expert", args="红烧肉")
"""

from src.core.skill.types import (
    SkillDefinition,
    SkillEntry,
    SkillSource,
)
from src.core.skill.manager import (
    SkillManager,
    get_skill_manager,
    reset_skill_manager,
)

__all__ = [
    "SkillDefinition",
    "SkillEntry",
    "SkillSource",
    "SkillManager",
    "get_skill_manager",
    "reset_skill_manager",
]

__version__ = "1.0.0"
