"""Skill 管理器单元测试。"""

from pathlib import Path

from src.core.skill.manager import SkillManager, reset_skill_manager
from src.core.skill.types import SkillDefinition, SkillEntry, SkillSource


class TestSkillManager:
    """SkillManager 单例测试。"""

    def setup_method(self) -> None:
        """每个测试前重置单例。"""
        reset_skill_manager()

    def test_register_and_get(self) -> None:
        """注册和获取 skill。"""
        manager = SkillManager()
        defn = SkillDefinition(name="test", description="A test skill")
        entry = SkillEntry(definition=defn, source=SkillSource.PROJECT)
        manager.register(entry)

        result = manager.get("test")
        assert result is not None
        assert result.definition.name == "test"

    def test_get_nonexistent(self) -> None:
        """获取不存在的 skill 返回 None。"""
        manager = SkillManager()
        assert manager.get("nonexistent") is None

    def test_unregister(self) -> None:
        """注销 skill。"""
        manager = SkillManager()
        defn = SkillDefinition(name="test", description="test")
        manager.register(SkillEntry(definition=defn))

        assert manager.unregister("test") is True
        assert manager.get("test") is None
        assert manager.unregister("test") is False

    def test_source_priority_user_over_project(self) -> None:
        """USER 来源覆盖 PROJECT 来源。"""
        manager = SkillManager()

        project_defn = SkillDefinition(name="skill", description="project version", body="project body")
        user_defn = SkillDefinition(name="skill", description="user version", body="user body")

        manager.register(SkillEntry(definition=project_defn, source=SkillSource.PROJECT))
        manager.register(SkillEntry(definition=user_defn, source=SkillSource.USER))

        result = manager.get("skill")
        assert result.definition.body == "user body"

    def test_source_priority_project_not_over_user(self) -> None:
        """PROJECT 来源不覆盖 USER 来源。"""
        manager = SkillManager()

        user_defn = SkillDefinition(name="skill", description="user version", body="user body")
        project_defn = SkillDefinition(name="skill", description="project version", body="project body")

        manager.register(SkillEntry(definition=user_defn, source=SkillSource.USER))
        manager.register(SkillEntry(definition=project_defn, source=SkillSource.PROJECT))

        result = manager.get("skill")
        assert result.definition.body == "user body"

    def test_list_user_invocable(self) -> None:
        """列出用户可调用的 skill。"""
        manager = SkillManager()

        invocable = SkillDefinition(name="a", description="invocable", user_invocable=True)
        not_invocable = SkillDefinition(name="b", description="hidden", user_invocable=False)

        manager.register(SkillEntry(definition=invocable))
        manager.register(SkillEntry(definition=not_invocable))

        result = manager.list_user_invocable()
        names = [d.name for d in result]
        assert "a" in names
        assert "b" not in names

    def test_list_model_visible(self) -> None:
        """列出 Bot 可见的 skill。"""
        manager = SkillManager()

        visible = SkillDefinition(name="a", description="visible", disable_model_invocation=False)
        hidden = SkillDefinition(name="b", description="hidden", disable_model_invocation=True)

        manager.register(SkillEntry(definition=visible))
        manager.register(SkillEntry(definition=hidden))

        result = manager.list_model_visible()
        names = [d.name for d in result]
        assert "a" in names
        assert "b" not in names

    def test_generate_catalog_xml(self) -> None:
        """生成 catalog XML。"""
        manager = SkillManager()

        defn = SkillDefinition(name="test", description="A test skill")
        manager.register(SkillEntry(definition=defn))

        xml = manager.generate_catalog_xml()
        assert "<available_skills>" in xml
        assert "<name>test</name>" in xml
        assert "<description>A test skill</description>" in xml

    def test_generate_catalog_empty(self) -> None:
        """无 skill 时 catalog 为空字符串。"""
        manager = SkillManager()
        assert manager.generate_catalog_xml() == ""

    def test_generate_catalog_excludes_hidden(self) -> None:
        """catalog 不包含 disable_model_invocation 的 skill。"""
        manager = SkillManager()

        visible = SkillDefinition(name="visible", description="shown")
        hidden = SkillDefinition(name="hidden", description="not shown", disable_model_invocation=True)

        manager.register(SkillEntry(definition=visible))
        manager.register(SkillEntry(definition=hidden))

        xml = manager.generate_catalog_xml()
        assert "visible" in xml
        assert "hidden" not in xml

    def test_load_skill_body(self) -> None:
        """加载 skill body。"""
        manager = SkillManager()

        defn = SkillDefinition(name="test", description="test", body="Hello $ARGUMENTS")
        manager.register(SkillEntry(definition=defn))

        body = manager.load_skill_body("test", args="world")
        assert body == "Hello world"

    def test_load_skill_body_not_found(self) -> None:
        """加载不存在的 skill 抛出 KeyError。"""
        manager = SkillManager()
        try:
            manager.load_skill_body("nonexistent")
            assert False, "Should have raised KeyError"
        except KeyError:
            pass

    def test_load_skill_body_truncation(self) -> None:
        """超长 body 被截断。"""
        manager = SkillManager()
        manager.set_body_budget(10)

        defn = SkillDefinition(name="test", description="test", body="A" * 100)
        manager.register(SkillEntry(definition=defn))

        body = manager.load_skill_body("test")
        assert len(body) == 10

    def test_load_from_dirs(self, tmp_path: Path) -> None:
        """从目录加载 skill。"""
        manager = SkillManager()

        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(
            "---\nname: my-skill\ndescription: Test\n---\n\nBody", encoding="utf-8"
        )

        count = manager.load_from_dirs(project_dir=tmp_path)
        assert count == 1
        assert manager.get("my-skill") is not None

    def test_clear(self) -> None:
        """清空所有 skill。"""
        manager = SkillManager()
        defn = SkillDefinition(name="test", description="test")
        manager.register(SkillEntry(definition=defn))

        manager.clear()
        assert manager.count() == 0

    def test_singleton(self) -> None:
        """单例模式。"""
        from src.core.skill.manager import get_skill_manager

        m1 = get_skill_manager()
        m2 = get_skill_manager()
        assert m1 is m2
