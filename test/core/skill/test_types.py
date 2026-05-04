"""Skill 类型定义单元测试。"""

from src.core.skill.types import (
    SkillDefinition,
    SkillEntry,
    SkillSource,
    substitute_arguments,
)


class TestSkillDefinition:
    """SkillDefinition 数据类测试。"""

    def test_default_values(self) -> None:
        """默认值正确。"""
        defn = SkillDefinition(name="test", description="A test skill")
        assert defn.name == "test"
        assert defn.description == "A test skill"
        assert defn.user_invocable is True
        assert defn.disable_model_invocation is False
        assert defn.arguments == []
        assert defn.body == ""

    def test_is_model_visible_default(self) -> None:
        """默认对 Bot 可见。"""
        defn = SkillDefinition(name="test", description="test")
        assert defn.is_model_visible is True

    def test_is_model_visible_disabled(self) -> None:
        """disable_model_invocation=True 时对 Bot 不可见。"""
        defn = SkillDefinition(
            name="test", description="test", disable_model_invocation=True
        )
        assert defn.is_model_visible is False


class TestSkillEntry:
    """SkillEntry 数据类测试。"""

    def test_default_source(self) -> None:
        """默认来源为 PROJECT。"""
        defn = SkillDefinition(name="test", description="test")
        entry = SkillEntry(definition=defn)
        assert entry.source == SkillSource.PROJECT
        assert entry.plugin_name == ""

    def test_plugin_source(self) -> None:
        """PLUGIN 来源带插件名。"""
        defn = SkillDefinition(name="test", description="test")
        entry = SkillEntry(
            definition=defn, source=SkillSource.PLUGIN, plugin_name="my_plugin"
        )
        assert entry.source == SkillSource.PLUGIN
        assert entry.plugin_name == "my_plugin"


class TestSubstituteArguments:
    """参数替换测试。"""

    def test_no_args(self) -> None:
        """无参数时 body 不变。"""
        result = substitute_arguments("Hello world", [], args="")
        assert result == "Hello world"

    def test_arguments_placeholder(self) -> None:
        """$ARGUMENTS 替换。"""
        result = substitute_arguments("Fix $ARGUMENTS", [], args="issue-123")
        assert result == "Fix issue-123"

    def test_positional_placeholders(self) -> None:
        """$0, $1, ... 位置参数替换。"""
        result = substitute_arguments(
            "Migrate $0 from $1 to $2", [], args="SearchBar React Vue"
        )
        assert result == "Migrate SearchBar from React to Vue"

    def test_named_placeholders(self) -> None:
        """命名参数替换。"""
        result = substitute_arguments(
            "Cook $dish with $style",
            ["dish", "style"],
            args="红烧肉 家常",
        )
        assert result == "Cook 红烧肉 with 家常"

    def test_fallback_when_no_placeholders(self) -> None:
        """body 中无占位符时追加 ARGUMENTS。"""
        result = substitute_arguments("Hello world", [], args="extra info")
        assert "ARGUMENTS: extra info" in result

    def test_no_fallback_with_positional(self) -> None:
        """有位置占位符时不追加 ARGUMENTS。"""
        result = substitute_arguments("Hello $0", [], args="world")
        assert result == "Hello world"
        assert "ARGUMENTS:" not in result

    def test_no_fallback_with_named(self) -> None:
        """有命名占位符时不追加 ARGUMENTS。"""
        result = substitute_arguments("Hello $name", ["name"], args="world")
        assert result == "Hello world"
        assert "ARGUMENTS:" not in result

    def test_quoted_args(self) -> None:
        """引号包裹的多词参数。"""
        result = substitute_arguments(
            "Fix $0: $1", [], args='"bug fix" detail'
        )
        assert "bug fix" in result
