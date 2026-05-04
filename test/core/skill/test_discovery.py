"""Skill 发现与解析单元测试。"""

import tempfile
from pathlib import Path

from src.core.skill.discovery import parse_skill_md, scan_skills_dir
from src.core.skill.types import SkillEntry, SkillSource


class TestParseSkillMd:
    """SKILL.md 解析测试。"""

    def test_full_frontmatter(self) -> None:
        """完整 frontmatter 解析。"""
        content = """---
name: test-skill
description: A test skill for testing
user-invocable: true
disable-model-invocation: false
arguments:
  - topic
  - format
---

# Test Skill

This is the body.
"""
        defn = parse_skill_md(content)
        assert defn.name == "test-skill"
        assert defn.description == "A test skill for testing"
        assert defn.user_invocable is True
        assert defn.disable_model_invocation is False
        assert defn.arguments == ["topic", "format"]
        assert "# Test Skill" in defn.body

    def test_minimal_frontmatter(self) -> None:
        """最简 frontmatter（只有 name）。"""
        content = """---
name: minimal
---

Body text here.
"""
        defn = parse_skill_md(content)
        assert defn.name == "minimal"
        assert defn.user_invocable is True
        assert defn.disable_model_invocation is False

    def test_no_frontmatter(self) -> None:
        """无 frontmatter 时全部作为 body。"""
        content = "# Just a body\n\nSome text here."
        defn = parse_skill_md(content)
        assert defn.name == ""
        assert "# Just a body" in defn.body
        assert "Some text here." in defn.description

    def test_description_fallback(self) -> None:
        """description 缺失时取首段。"""
        content = """---
name: fallback
---

First paragraph is the description.

Second paragraph is body.
"""
        defn = parse_skill_md(content)
        assert "First paragraph" in defn.description

    def test_arguments_string_format(self) -> None:
        """arguments 为字符串格式。"""
        content = """---
name: test
arguments: topic format
---

Body.
"""
        defn = parse_skill_md(content)
        assert defn.arguments == ["topic", "format"]

    def test_invalid_name(self) -> None:
        """非法 name 抛出 ValueError。"""
        content = """---
name: Invalid Name!
---

Body.
"""
        try:
            parse_skill_md(content)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_invalid_yaml(self) -> None:
        """无效 YAML frontmatter 抛出 ValueError。"""
        content = """---
: invalid yaml [
---

Body.
"""
        try:
            parse_skill_md(content)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestScanSkillsDir:
    """目录扫描测试。"""

    def test_scan_valid_directory(self, tmp_path: Path) -> None:
        """扫描包含有效 SKILL.md 的目录。"""
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Test\n---\n\nBody", encoding="utf-8"
        )

        entries = scan_skills_dir(tmp_path)
        assert len(entries) == 1
        assert entries[0].definition.name == "my-skill"

    def test_scan_empty_directory(self, tmp_path: Path) -> None:
        """空目录返回空列表。"""
        entries = scan_skills_dir(tmp_path)
        assert entries == []

    def test_scan_nonexistent_directory(self) -> None:
        """不存在的目录返回空列表。"""
        entries = scan_skills_dir(Path("/nonexistent"))
        assert entries == []

    def test_scan_dir_without_skill_md(self, tmp_path: Path) -> None:
        """子目录无 SKILL.md 时跳过。"""
        (tmp_path / "no-skill").mkdir()
        entries = scan_skills_dir(tmp_path)
        assert entries == []

    def test_scan_uses_dirname_as_fallback_name(self, tmp_path: Path) -> None:
        """name 缺失时用目录名。"""
        skill_dir = tmp_path / "fallback-name"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\n---\n\nBody", encoding="utf-8")

        entries = scan_skills_dir(tmp_path)
        assert len(entries) == 1
        assert entries[0].definition.name == "fallback-name"

    def test_scan_sets_source(self, tmp_path: Path) -> None:
        """扫描时设置来源类型。"""
        skill_dir = tmp_path / "user-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: user-skill\ndescription: Test\n---\n\nBody", encoding="utf-8"
        )

        entries = scan_skills_dir(tmp_path, source=SkillSource.USER)
        assert entries[0].source == SkillSource.USER
