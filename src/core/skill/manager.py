"""Skill 管理器模块。

提供 SkillManager 单例，负责 skill 的注册、查找、catalog 生成和 body 加载。
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from src.core.skill.discovery import scan_skills_dir
from src.core.skill.types import (
    SkillDefinition,
    SkillEntry,
    SkillSource,
    substitute_arguments,
)

logger = logging.getLogger(__name__)

_DEFAULT_MAX_CATALOG_CHARS = 4096
_DEFAULT_MAX_SKILL_BODY_CHARS = 8192


class SkillManager:
    """Skill 管理器，负责注册、查找和渲染 skill。

    实现为单例模式，确保全局只有一个管理器实例。

    Attributes:
        _entries: 已注册的 skill 条目字典，键为 skill name。
        _max_catalog_chars: catalog XML 最大字符数。
        _max_skill_body_chars: 单个 skill 正文最大字符数。
    """

    _instance: SkillManager | None = None

    def __new__(cls) -> SkillManager:
        """实现单例模式。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """初始化管理器。"""
        if self._initialized:
            return
        self._entries: dict[str, SkillEntry] = {}
        self._max_catalog_chars: int = _DEFAULT_MAX_CATALOG_CHARS
        self._max_skill_body_chars: int = _DEFAULT_MAX_SKILL_BODY_CHARS
        self._initialized = True

    def register(self, entry: SkillEntry) -> None:
        """注册一个 skill 条目。

        若同名 skill 已存在，高优先级来源覆盖低优先级。
        优先级：USER > PROJECT > PLUGIN。

        Args:
            entry: 要注册的 SkillEntry。
        """
        name = entry.definition.name
        existing = self._entries.get(name)

        if existing is not None and _source_priority(existing.source) >= _source_priority(entry.source):
            logger.debug(
                "Skill '%s' already registered with higher/equal priority (%s > %s), skipping",
                name,
                existing.source.value,
                entry.source.value,
            )
            return

        self._entries[name] = entry
        logger.debug("Registered skill: %s (source=%s)", name, entry.source.value)

    def unregister(self, name: str) -> bool:
        """注销一个 skill。

        Args:
            name: Skill 名称。

        Returns:
            是否成功注销。
        """
        if name in self._entries:
            del self._entries[name]
            return True
        return False

    def get(self, name: str) -> SkillEntry | None:
        """获取指定名称的 skill 条目。

        Args:
            name: Skill 名称。

        Returns:
            SkillEntry 或 None。
        """
        return self._entries.get(name)

    def get_all(self) -> dict[str, SkillEntry]:
        """获取所有已注册的 skill 条目。"""
        return dict(self._entries)

    def list_user_invocable(self) -> list[SkillDefinition]:
        """列出所有用户可调用的 skill 定义。"""
        return [
            e.definition
            for e in self._entries.values()
            if e.definition.user_invocable
        ]

    def list_model_visible(self) -> list[SkillDefinition]:
        """列出所有 Bot 可见的 skill 定义（会出现在 catalog 中）。"""
        return [
            e.definition
            for e in self._entries.values()
            if e.definition.is_model_visible
        ]

    def generate_catalog_xml(self) -> str:
        """生成注入 system prompt 的 skill catalog XML。

        格式：
        .. code-block:: xml

            <available_skills>
              <skill>
                <name>cooking-expert</name>
                <description>烹饪专家模式...</description>
              </skill>
            </available_skills>

        当 catalog 超过 _max_catalog_chars 时，按 description 长度从长到短裁剪。

        Returns:
            XML 字符串。若无可用 skill 则返回空字符串。
        """
        visible = self.list_model_visible()
        if not visible:
            return ""

        root = ET.Element("available_skills")
        for skill_def in visible:
            skill_el = ET.SubElement(root, "skill")
            name_el = ET.SubElement(skill_el, "name")
            name_el.text = skill_def.name
            desc_el = ET.SubElement(skill_el, "description")
            desc_el.text = skill_def.description

        xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)

        # 超长裁剪：按 description 长度从长到短移除
        if len(xml_str) > self._max_catalog_chars:
            sorted_skills = sorted(visible, key=lambda s: len(s.description), reverse=True)
            trimmed = list(visible)
            for skill_def in sorted_skills:
                if len(xml_str) <= self._max_catalog_chars:
                    break
                trimmed.remove(skill_def)
                logger.debug(
                    "Trimmed skill from catalog due to budget: %s",
                    skill_def.name,
                )
                root = ET.Element("available_skills")
                for s in trimmed:
                    skill_el = ET.SubElement(root, "skill")
                    name_el = ET.SubElement(skill_el, "name")
                    name_el.text = s.name
                    desc_el = ET.SubElement(skill_el, "description")
                    desc_el.text = s.description
                xml_str = ET.tostring(root, encoding="unicode", xml_declaration=False)

        return xml_str

    def load_skill_body(self, name: str, args: str = "") -> str:
        """加载指定 skill 的完整内容并执行参数替换。

        Args:
            name: Skill 名称。
            args: 用户传入的参数字符串。

        Returns:
            替换后的 skill body。

        Raises:
            KeyError: Skill 不存在。
        """
        entry = self._entries.get(name)
        if entry is None:
            raise KeyError(f"Skill not found: {name}")

        body = entry.definition.body

        # 参数替换
        body = substitute_arguments(
            body=body,
            arguments=entry.definition.arguments,
            args=args,
        )

        # 正文长度限制
        if len(body) > self._max_skill_body_chars:
            body = body[: self._max_skill_body_chars]
            logger.warning(
                "Skill body for '%s' truncated to %d chars",
                name,
                self._max_skill_body_chars,
            )

        return body

    def load_from_dirs(
        self,
        project_dir: Path | None = None,
        user_dir: Path | None = None,
    ) -> int:
        """从项目级和用户级目录加载 skill。

        Args:
            project_dir: 项目级 skill 目录路径。
            user_dir: 用户级 skill 目录路径。

        Returns:
            加载的 skill 数量。
        """
        count = 0

        if project_dir is not None:
            entries = scan_skills_dir(project_dir, source=SkillSource.PROJECT)
            for entry in entries:
                self.register(entry)
                count += 1

        if user_dir is not None:
            entries = scan_skills_dir(user_dir, source=SkillSource.USER)
            for entry in entries:
                self.register(entry)
                count += 1

        logger.info("Loaded %d skills from directories", count)
        return count

    def set_catalog_budget(self, max_chars: int) -> None:
        """设置 catalog 最大字符数。"""
        self._max_catalog_chars = max_chars

    def set_body_budget(self, max_chars: int) -> None:
        """设置单个 skill 正文最大字符数。"""
        self._max_skill_body_chars = max_chars

    def clear(self) -> None:
        """清空所有已注册的 skill。"""
        self._entries.clear()

    def count(self) -> int:
        """获取已注册 skill 的数量。"""
        return len(self._entries)

    def __repr__(self) -> str:
        """返回管理器的字符串表示。"""
        return f"SkillManager(skills={self.count()})"


def _source_priority(source: SkillSource) -> int:
    """返回来源优先级，数值越高优先级越高。

    USER > PROJECT > PLUGIN
    """
    priorities = {
        SkillSource.PLUGIN: 0,
        SkillSource.PROJECT: 1,
        SkillSource.USER: 2,
    }
    return priorities.get(source, 0)


_global_manager: SkillManager | None = None


def get_skill_manager() -> SkillManager:
    """获取全局 SkillManager 单例。"""
    global _global_manager
    if _global_manager is None:
        _global_manager = SkillManager()
    return _global_manager


def reset_skill_manager() -> None:
    """重置全局 SkillManager（主要用于测试）。"""
    global _global_manager
    if _global_manager is not None:
        _global_manager.clear()
    _global_manager = None
    SkillManager._instance = None
