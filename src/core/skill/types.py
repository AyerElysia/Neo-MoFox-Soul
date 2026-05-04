"""Skill 类型定义模块。"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class SkillSource(str, Enum):
    """Skill 来源类型。"""

    PROJECT = "project"
    USER = "user"
    PLUGIN = "plugin"


@dataclass(frozen=True, slots=True)
class SkillDefinition:
    """Skill 定义，从 SKILL.md 文件解析而来。

    Attributes:
        name: 唯一标识符，用于 /name 调用和 skill_control Action 引用。
        description: 一句话描述，Bot 据此判断何时使用此 skill。
            若 frontmatter 未指定，则取 Markdown 正文首段。
        user_invocable: 用户能否通过 /name 直接调用。
        disable_model_invocation: 是否禁止 Bot 自主激活此 skill。
        arguments: 命名参数列表，用于 $name 替换。
            如 arguments=["topic","format"] 则 $topic=$0, $format=$1。
        body: Markdown 正文（frontmatter 之后的全部内容）。
        dir_path: Skill 目录路径，用于定位辅助文件。
    """

    name: str
    description: str
    user_invocable: bool = True
    disable_model_invocation: bool = False
    arguments: list[str] = field(default_factory=list)
    body: str = ""
    dir_path: Path = field(default_factory=Path)

    @property
    def is_model_visible(self) -> bool:
        """此 skill 是否对 Bot 可见（会出现在 catalog 中）。"""
        return not self.disable_model_invocation


@dataclass(frozen=True, slots=True)
class SkillEntry:
    """注册到 SkillManager 的条目，包含定义和来源信息。

    Attributes:
        definition: Skill 定义。
        source: Skill 来源（project / user / plugin）。
        plugin_name: 当 source 为 PLUGIN 时，记录所属插件名。
    """

    definition: SkillDefinition
    source: SkillSource = SkillSource.PROJECT
    plugin_name: str = ""


def substitute_arguments(
    body: str,
    arguments: list[str],
    args: str = "",
) -> str:
    """对 skill body 执行参数替换。

    替换规则（与 Claude Code Agent Skills 标准一致）：
    - $ARGUMENTS → 全部参数字符串
    - $N / $ARGUMENTS[N] → 第 N 个位置参数（0-indexed）
    - $name → 命名参数（arguments 列表中的名称按位置映射）

    若 body 中不含 $ARGUMENTS 且 args 非空，
    则在末尾追加 ``ARGUMENTS: <args>``。

    Args:
        body: Skill Markdown 正文。
        arguments: frontmatter 中声明的命名参数列表。
        args: 用户传入的原始参数字符串。

    Returns:
        替换后的正文。
    """
    if not args:
        return body

    parts = _split_args(args)
    has_arguments_placeholder = "$ARGUMENTS" in body
    has_positional_placeholder = any(f"${i}" in body for i in range(len(parts)))
    has_named_placeholder = any(f"${name}" in body for name in arguments)
    has_any_placeholder = (
        has_arguments_placeholder
        or has_positional_placeholder
        or has_named_placeholder
    )

    result = body

    # $ARGUMENTS → 全部参数字符串
    result = result.replace("$ARGUMENTS", args)

    # 位置参数替换: $0, $1, ... 和 $ARGUMENTS[0], $ARGUMENTS[1], ...
    import re

    for i, part in enumerate(parts):
        result = result.replace(f"$ARGUMENTS[{i}]", part)
        result = result.replace(f"${i}", part)

    # 命名参数替换: $name → 对应位置参数
    for i, arg_name in enumerate(arguments):
        if i < len(parts):
            result = result.replace(f"${arg_name}", parts[i])

    # 若 body 中不含任何参数占位符且有参数，追加到末尾
    if not has_any_placeholder and args:
        result = result.rstrip("\n") + f"\n\nARGUMENTS: {args}"

    # 清理未替换的 $ARGUMENTS[N] 占位符
    result = re.sub(r"\$ARGUMENTS\[\d+\]", "", result)

    return result


def _split_args(args: str) -> list[str]:
    """将参数字符串按空格分割，支持引号包裹的多词参数。

    Args:
        args: 原始参数字符串。

    Returns:
        分割后的参数列表。
    """
    import shlex

    try:
        return shlex.split(args)
    except ValueError:
        return args.split()
