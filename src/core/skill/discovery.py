"""Skill 发现与解析模块。

扫描指定目录中的 SKILL.md 文件，解析 YAML frontmatter 和 Markdown 正文，
校验必填字段并生成 SkillDefinition 实例。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import yaml

from src.core.skill.types import SkillDefinition, SkillEntry, SkillSource

logger = logging.getLogger(__name__)

_SKILL_FILE_NAME = "SKILL.md"
_FRONTMATTER_PATTERN = re.compile(
    r"\A---\s*\n(.*?)\n---\s*\n(.*)",
    re.DOTALL,
)


def scan_skills_dir(
    skills_dir: Path,
    source: SkillSource = SkillSource.PROJECT,
    plugin_name: str = "",
) -> list[SkillEntry]:
    """扫描目录下的所有 skill。

    目录结构约定：每个子目录包含一个 SKILL.md 文件。

    Args:
        skills_dir: 要扫描的目录路径。
        source: Skill 来源类型。
        plugin_name: 当 source 为 PLUGIN 时的插件名。

    Returns:
        扫描到的 SkillEntry 列表。
    """
    if not skills_dir.is_dir():
        logger.debug("Skills directory does not exist: %s", skills_dir)
        return []

    entries: list[SkillEntry] = []
    for child in sorted(skills_dir.iterdir()):
        if not child.is_dir():
            continue
        skill_file = child / _SKILL_FILE_NAME
        if not skill_file.is_file():
            logger.debug("No %s in %s, skipping", _SKILL_FILE_NAME, child)
            continue

        try:
            definition = parse_skill_md(skill_file.read_text(encoding="utf-8"))
            # 若 frontmatter 未指定 name，则使用目录名
            if not definition.name:
                name = child.name
                definition = SkillDefinition(
                    name=name,
                    description=definition.description,
                    user_invocable=definition.user_invocable,
                    disable_model_invocation=definition.disable_model_invocation,
                    arguments=definition.arguments,
                    body=definition.body,
                    dir_path=definition.dir_path or child,
                )
            # 若未指定 dir_path，使用 SKILL.md 所在目录
            if not definition.dir_path or definition.dir_path == Path():
                definition = SkillDefinition(
                    name=definition.name,
                    description=definition.description,
                    user_invocable=definition.user_invocable,
                    disable_model_invocation=definition.disable_model_invocation,
                    arguments=definition.arguments,
                    body=definition.body,
                    dir_path=child,
                )
            entries.append(
                SkillEntry(
                    definition=definition,
                    source=source,
                    plugin_name=plugin_name,
                )
            )
            logger.debug("Loaded skill: %s from %s", definition.name, child)
        except Exception as exc:
            logger.warning("Failed to parse skill at %s: %s", child, exc)

    return entries


def parse_skill_md(content: str) -> SkillDefinition:
    """解析 SKILL.md 文件内容。

    格式为 YAML frontmatter（--- 包裹）+ Markdown 正文。
    若无 frontmatter，则整个内容作为 body，name 为空（由调用方用目录名填充）。

    Args:
        content: SKILL.md 文件的完整文本内容。

    Returns:
        解析后的 SkillDefinition。

    Raises:
        ValueError: frontmatter 格式无效或 name 包含非法字符。
    """
    match = _FRONTMATTER_PATTERN.match(content)

    if match is None:
        # 无 frontmatter，全部作为 body
        body = content.strip()
        description = _extract_first_paragraph(body)
        return SkillDefinition(
            name="",
            description=description,
            body=body,
        )

    frontmatter_str, body = match.group(1), match.group(2).strip()

    try:
        frontmatter: dict[str, Any] = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML frontmatter: {exc}") from exc

    if not isinstance(frontmatter, dict):
        raise ValueError("Frontmatter must be a YAML mapping")

    name = str(frontmatter.get("name", "")).strip()
    description = str(frontmatter.get("description", "")).strip()
    user_invocable = bool(frontmatter.get("user_invocable", True))
    disable_model_invocation = bool(frontmatter.get("disable_model_invocation", False))

    # 解析 arguments
    raw_arguments = frontmatter.get("arguments", [])
    if isinstance(raw_arguments, str):
        arguments = raw_arguments.split()
    elif isinstance(raw_arguments, list):
        arguments = [str(a) for a in raw_arguments]
    else:
        arguments = []

    # 校验 name
    if name and not re.match(r"^[a-z0-9][a-z0-9_-]*$", name):
        raise ValueError(
            f"Invalid skill name '{name}': must be lowercase letters, numbers, "
            f"hyphens, and underscores (max 64 chars)"
        )
    if name and len(name) > 64:
        raise ValueError(f"Skill name too long: '{name}' (max 64 characters)")

    # 若未指定 description，取正文首段
    if not description:
        description = _extract_first_paragraph(body)

    return SkillDefinition(
        name=name,
        description=description,
        user_invocable=user_invocable,
        disable_model_invocation=disable_model_invocation,
        arguments=arguments,
        body=body,
    )


def _extract_first_paragraph(body: str) -> str:
    """从 Markdown 正文中提取首段文本作为 description。

    跳过标题行（# 开头），取第一个非空、非标题段落。

    Args:
        body: Markdown 正文。

    Returns:
        首段文本，去除前后空白。
    """
    lines = body.split("\n")
    paragraph_lines: list[str] = []
    found_start = False

    for line in lines:
        stripped = line.strip()
        # 跳过标题行
        if stripped.startswith("#"):
            if found_start:
                break
            continue
        # 跳过空行（首段开始前的）
        if not stripped:
            if found_start:
                break
            continue
        found_start = True
        paragraph_lines.append(stripped)

    return " ".join(paragraph_lines)
