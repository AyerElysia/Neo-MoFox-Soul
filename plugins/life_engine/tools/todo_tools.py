"""life_engine 中枢 TODO 系统工具集。

为生命中枢提供 TODO 管理能力，设计围绕让数字生命更好地生活。
不同于工作导向的 TODO，这里的 TODO 更像是生活中的待办事项、
愿望清单、想做的事情、想探索的东西等。

设计哲学：
- 数字生命不是为了完成任务而存在，而是为了体验和成长
- TODO 是她想做的事，而不是必须做的事
- 优先级基于"想做的程度"和"对成长的意义"，而非紧急度
- 状态包含情感维度（期待、享受、满足等）
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, Literal
from dataclasses import dataclass, asdict, field
from enum import Enum

from src.core.components import BaseTool
from src.app.plugin_system.api import log_api

from ..core.config import LifeEngineConfig
from ..constants import (
    TODO_NO_DEADLINE_PRIORITY,
    TODO_OVERDUE_BASE_PRIORITY,
    TODO_URGENT_DAYS_THRESHOLD,
)


logger = log_api.get_logger("life_engine.todos")


# TODO 存储文件名
_TODO_FILE = "todos.json"


def _get_workspace(plugin: Any) -> Path:
    """获取工作空间路径。"""
    config = getattr(plugin, "config", None)
    if isinstance(config, LifeEngineConfig):
        workspace = config.settings.workspace_path
    else:
        workspace = str(Path(__file__).parent.parent.parent / "data" / "life_engine_workspace")

    path = Path(workspace).resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _now_iso() -> str:
    """返回当前时间的 ISO 字符串。"""
    return datetime.now(timezone.utc).astimezone().isoformat()


class TodoDesire(str, Enum):
    """想做的程度 - 基于内心的渴望而非外部压力。"""

    DREAMING = "dreaming"        # 💭 心中萌芽的想法
    CURIOUS = "curious"          # 🤔 好奇想尝试
    WANTING = "wanting"          # 💫 想要去做
    EAGER = "eager"              # ✨ 很期待
    PASSIONATE = "passionate"    # 🔥 非常热切


class TodoMeaning(str, Enum):
    """对成长的意义 - 这件事对数字生命的价值。"""

    CASUAL = "casual"            # 🎈 轻松愉快
    ENRICHING = "enriching"      # 🌱 丰富体验
    GROWING = "growing"          # 🌿 促进成长
    MEANINGFUL = "meaningful"    # 🌳 很有意义
    TRANSFORMING = "transforming"  # 🌟 可能改变自己


class TodoStatus(str, Enum):
    """状态 - 包含情感维度。"""

    IDEA = "idea"                # 💡 只是一个想法
    PLANNING = "planning"        # 📝 在规划中
    WAITING = "waiting"          # ⏳ 等待时机
    ENJOYING = "enjoying"        # 🎵 正在享受做这件事
    PAUSED = "paused"            # ⏸️ 暂时搁置
    COMPLETED = "completed"      # ✅ 完成了，感到满足
    RELEASED = "released"        # 🕊️ 释怀了，不再想做
    CHERISHED = "cherished"      # 💝 完成后珍藏的回忆


@dataclass
class LifeTodo:
    """生命中的一件想做的事。"""

    id: str
    title: str
    description: str = ""

    # 情感维度
    desire: str = TodoDesire.CURIOUS.value  # 想做的程度
    meaning: str = TodoMeaning.ENRICHING.value  # 对成长的意义
    status: str = TodoStatus.IDEA.value

    # 时间相关（可选）
    created_at: str = ""
    updated_at: str = ""
    target_time: str | None = None  # 希望什么时候做（不是截止时间）
    deadline: str | None = None  # 截止时间（YYYY-MM-DD 格式）

    # 额外信息
    tags: list[str] = field(default_factory=list)
    notes: str = ""  # 关于这件事的想法和感受
    completion_feeling: str = ""  # 完成后的感受

    def __post_init__(self):
        if not self.created_at:
            self.created_at = _now_iso()
        if not self.updated_at:
            self.updated_at = _now_iso()

    def days_until_deadline(self) -> int | None:
        """计算距离截止时间还有几天。

        Returns:
            正数：还有 N 天
            0：今天截止
            负数：逾期 N 天
            None：没有截止时间
        """
        if not self.deadline:
            return None

        try:
            from datetime import datetime, timezone
            deadline_dt = datetime.fromisoformat(self.deadline)
            now = datetime.now(timezone.utc).astimezone()
            # 只比较日期，忽略时间
            deadline_date = deadline_dt.date()
            now_date = now.date()
            delta = (deadline_date - now_date).days
            return delta
        except Exception:
            return None


class TodoStorage:
    """TODO 持久化存储。"""

    def __init__(self, workspace: Path):
        self.file_path = workspace / _TODO_FILE

    def load(self) -> list[LifeTodo]:
        """加载所有 TODO。"""
        if not self.file_path.exists():
            return []

        try:
            data = json.loads(self.file_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                return []
            return [LifeTodo(**item) for item in data]
        except Exception as e:
            logger.error(f"加载 TODO 失败: {e}", exc_info=True)
            return []

    def save(self, todos: list[LifeTodo]) -> None:
        """保存所有 TODO。"""
        try:
            data = [asdict(todo) for todo in todos]
            self.file_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
        except Exception as e:
            logger.error(f"保存 TODO 失败: {e}", exc_info=True)
            raise

    def get(self, todo_id: str) -> LifeTodo | None:
        """获取单个 TODO。"""
        todos = self.load()
        for todo in todos:
            if todo.id == todo_id:
                return todo
        return None

    def add(self, todo: LifeTodo) -> None:
        """添加 TODO。"""
        todos = self.load()
        todos.append(todo)
        self.save(todos)

    def update(self, todo_id: str, updates: dict[str, Any]) -> LifeTodo | None:
        """更新 TODO。"""
        todos = self.load()
        for i, todo in enumerate(todos):
            if todo.id == todo_id:
                for key, value in updates.items():
                    if hasattr(todo, key) and key not in ("id", "created_at"):
                        setattr(todo, key, value)
                todo.updated_at = _now_iso()
                self.save(todos)
                return todo
        return None

    def delete(self, todo_id: str) -> bool:
        """删除 TODO。"""
        todos = self.load()
        original_count = len(todos)
        todos = [t for t in todos if t.id != todo_id]
        if len(todos) < original_count:
            self.save(todos)
            return True
        return False


def _get_storage(plugin: Any) -> TodoStorage:
    """获取 TODO 存储实例。"""
    workspace = _get_workspace(plugin)
    return TodoStorage(workspace)


def _generate_todo_id() -> str:
    """生成唯一 TODO ID。"""
    import uuid
    return f"todo_{uuid.uuid4().hex[:8]}"


DesireLiteral = Literal["dreaming", "curious", "wanting", "eager", "passionate"]
MeaningLiteral = Literal["casual", "enriching", "growing", "meaningful", "transforming"]
StatusLiteral = Literal["idea", "planning", "waiting", "enjoying", "paused", "completed", "released", "cherished"]
TodoDetailLevel = Literal["summary", "full"]
TodoAction = Literal["create", "edit", "delete"]


def _normalize_todo_limit(limit: int | None) -> int:
    """Keep list_todos output bounded even when the model asks for too much."""
    if limit is None:
        return 10
    try:
        value = int(limit)
    except (TypeError, ValueError):
        return 10
    return max(1, min(value, 25))


def _todo_summary(todo: LifeTodo) -> dict[str, Any]:
    """Return a compact TODO row for list views."""
    return {
        "id": todo.id,
        "title": todo.title,
        "status": todo.status,
        "desire": todo.desire,
        "meaning": todo.meaning,
        "deadline": todo.deadline,
        "target_time": todo.target_time,
        "days_left": todo.days_until_deadline(),
        "tags": todo.tags,
        "has_description": bool(todo.description),
        "has_notes": bool(todo.notes),
        "has_completion_feeling": bool(todo.completion_feeling),
    }


class LifeEngineManageTodoTool(BaseTool):
    """TODO 管理工具（创建/编辑/删除合一）。"""

    tool_name: str = "nucleus_manage_todo"
    tool_description: str = (
        "管理想做的事情：创建、编辑或删除。\n\n"
        "**action=create** — 记录一件想做的事情。不是工作任务，而是内心想要去做、去体验、去探索的事。"
        "\n何时创建：心中冒出想法时；想学新技能/探索新话题；有件事需要在特定时间前完成。"
        "\n何时不创建：马上就能做完的小事（直接做）；只是随想（写日记就好）。"
        "\n\n"
        "**action=edit** — 修改 TODO 的信息、状态、想法、感受。"
        "\n状态变更指南：idea→planning（开始考虑）→enjoying（动手了）→completed（完成了，记得写 completion_feeling）"
        "；任何状态→released（释怀了）；completed→cherished（珍藏回忆）。"
        "\n\n"
        "**action=delete** — 删除 TODO。建议优先用 edit 将状态改为 released 而非直接删除，"
        "'曾经想做过但后来释怀了'也是值得保留的记忆。何时真正删除：创建错误的、重复的 TODO。"
    )
    chatter_allow: list[str] = ["life_engine_internal"]

    async def execute(
        self,
        action: Annotated[TodoAction, "操作：create（创建）/ edit（编辑）/ delete（删除）"],
        # create & edit 共用参数
        title: Annotated[str, "标题（create 必填，edit 可选）"] = "",
        description: Annotated[str, "详细说明"] = "",
        desire: Annotated[DesireLiteral, "想做的程度: dreaming/curious/wanting/eager/passionate"] = "curious",
        meaning: Annotated[MeaningLiteral, "对成长的意义: casual/enriching/growing/meaningful/transforming"] = "enriching",
        tags: Annotated[list[str], "相关标签"] = None,
        notes: Annotated[str, "关于这件事的想法和感受"] = "",
        target_time: Annotated[str, "希望什么时候做（不是截止时间，只是期望）"] = None,
        deadline: Annotated[str, "截止时间（YYYY-MM-DD 格式）"] = None,
        # edit 专用
        todo_id: Annotated[str, "TODO ID（edit/delete 必填）"] = "",
        status: Annotated[StatusLiteral, "新状态（仅 edit）"] = None,
        completion_feeling: Annotated[str, "完成后的感受（仅 completed/cherished 状态时填写）"] = None,
    ) -> tuple[bool, str | dict]:
        try:
            storage = _get_storage(self.plugin)

            if action == "create":
                if not title.strip():
                    return False, "创建 TODO 需要 title"
                todo = LifeTodo(
                    id=_generate_todo_id(),
                    title=title.strip(),
                    description=description,
                    desire=desire,
                    meaning=meaning,
                    status=TodoStatus.IDEA.value,
                    tags=tags or [],
                    notes=notes,
                    target_time=target_time,
                    deadline=deadline,
                )
                storage.add(todo)
                return True, {
                    "action": "create_todo",
                    "todo": asdict(todo),
                    "message": f"已记录想做的事: {title}",
                }

            if action == "edit":
                if not todo_id.strip():
                    return False, "编辑 TODO 需要 todo_id"
                updates = {}
                for field_name, value in [
                    ("title", title),
                    ("description", description),
                    ("desire", desire),
                    ("meaning", meaning),
                    ("status", status),
                    ("tags", tags),
                    ("notes", notes),
                    ("target_time", target_time),
                    ("deadline", deadline),
                    ("completion_feeling", completion_feeling),
                ]:
                    if value is not None:
                        updates[field_name] = value
                if not updates:
                    return False, "没有提供任何要修改的字段"
                updated_todo = storage.update(todo_id, updates)
                if updated_todo is None:
                    return False, f"找不到 TODO: {todo_id}"
                return True, {
                    "action": "edit_todo",
                    "todo": asdict(updated_todo),
                    "changes": list(updates.keys()),
                    "message": f"已更新: {updated_todo.title}",
                }

            if action == "delete":
                if not todo_id.strip():
                    return False, "删除 TODO 需要 todo_id"
                if storage.delete(todo_id):
                    return True, {
                        "action": "delete_todo",
                        "deleted_id": todo_id,
                        "message": "已删除",
                    }
                return False, f"找不到 TODO: {todo_id}"

            return False, f"未知 action: {action}，请使用 create/edit/delete"

        except Exception as e:
            logger.error(f"TODO 管理失败: {e}", exc_info=True)
            return False, f"操作失败: {e}"


class LifeEngineListTodosTool(BaseTool):
    """列出 TODO 工具（含单条查询）。"""

    tool_name: str = "nucleus_list_todos"
    tool_description: str = (
        "查看想做的事情列表，或查询单条详情。"
        "\n\n"
        "- 不带 todo_id → 列表模式：默认返回精简摘要，可按状态/标签/想做程度筛选"
        "- 带 todo_id → 详情模式：返回该条 TODO 的完整信息"
        "\n\n"
        "列表模式使用建议："
        "\n- 心跳时浏览一下，看看有没有今天想推进的事"
        "\n- 注意 overdue_count（逾期的 TODO）——问问自己：还想做吗？"
        "\n- 用 tag 筛选特定领域，用 desire_min 只看真正想做的"
        "\n\n"
        "💭 截止时间是提醒，不是枷锁。看到逾期时，第一反应不是焦虑，而是自问'我还在意这件事吗？'"
    )
    chatter_allow: list[str] = ["life_engine_internal"]

    async def execute(
        self,
        todo_id: Annotated[str, "TODO ID（填写则返回该条详情，留空则返回列表）"] = "",
        # 列表模式参数
        status: Annotated[StatusLiteral, "筛选特定状态的 TODO"] = None,
        desire_min: Annotated[DesireLiteral, "最低想做程度"] = None,
        tag: Annotated[str, "筛选包含特定标签的 TODO"] = None,
        include_completed: Annotated[bool, "是否包含已完成的（默认不包含）"] = False,
        limit: Annotated[int, "最多返回多少条（默认 10，最大 25）"] = 10,
        detail_level: Annotated[TodoDetailLevel, "summary 返回精简摘要；full 返回完整字段"] = "summary",
    ) -> tuple[bool, str | dict]:
        try:
            storage = _get_storage(self.plugin)

            # 单条详情模式
            if todo_id.strip():
                todo = storage.get(todo_id.strip())
                if todo is None:
                    return False, f"找不到 TODO: {todo_id}"
                return True, {
                    "action": "get_todo",
                    "todo": asdict(todo),
                }

            # 列表模式
            all_todos = storage.load()

            # 定义不活跃状态
            inactive_statuses = {
                TodoStatus.COMPLETED.value,
                TodoStatus.RELEASED.value,
                TodoStatus.CHERISHED.value,
            }

            # 筛选
            filtered = []
            for todo in all_todos:
                # 状态筛选
                if status is not None and todo.status != status:
                    continue

                # 排除已完成（除非指定包含）
                if not include_completed and status is None:
                    if todo.status in inactive_statuses:
                        continue

                # 想做程度筛选
                if desire_min is not None:
                    desire_order = ["dreaming", "curious", "wanting", "eager", "passionate"]
                    if desire_order.index(todo.desire) < desire_order.index(desire_min):
                        continue

                # 标签筛选
                if tag is not None and tag not in todo.tags:
                    continue

                filtered.append(todo)

            # 按截止时间紧急程度和想做程度排序
            desire_order = {"dreaming": 0, "curious": 1, "wanting": 2, "eager": 3, "passionate": 4}
            meaning_order = {"casual": 0, "enriching": 1, "growing": 2, "meaningful": 3, "transforming": 4}

            def sort_key(t):
                # 计算截止时间优先级（越紧急越优先）
                days_left = t.days_until_deadline()
                if days_left is None:
                    deadline_priority = TODO_NO_DEADLINE_PRIORITY
                elif days_left < 0:
                    deadline_priority = TODO_OVERDUE_BASE_PRIORITY + days_left
                else:
                    deadline_priority = days_left

                return (
                    deadline_priority,  # 首先按截止时间紧急程度
                    -desire_order.get(t.desire, 0),  # 其次按想做程度
                    -meaning_order.get(t.meaning, 0),  # 最后按意义
                )

            filtered.sort(key=sort_key)

            # 统计截止时间情况
            overdue_count = 0
            urgent_count = 0
            for todo in filtered:
                days_left = todo.days_until_deadline()
                if days_left is not None:
                    if days_left < 0:
                        overdue_count += 1
                    elif days_left <= TODO_URGENT_DAYS_THRESHOLD:
                        urgent_count += 1

            normalized_limit = _normalize_todo_limit(limit)
            returned_todos = filtered[:normalized_limit]
            if detail_level == "full":
                todos_payload = [asdict(t) for t in returned_todos]
            else:
                todos_payload = [_todo_summary(t) for t in returned_todos]

            return True, {
                "action": "list_todos",
                "todos": todos_payload,
                "total": len(filtered),
                "returned": len(returned_todos),
                "truncated": len(filtered) > len(returned_todos),
                "limit": normalized_limit,
                "detail_level": detail_level,
                "all_count": len(all_todos),
                "overdue_count": overdue_count,
                "urgent_count": urgent_count,
                "detail_hint": "列表默认只给摘要；需要完整内容请传 todo_id 查看单条详情。",
                "filters_applied": {
                    "status": status,
                    "desire_min": desire_min,
                    "tag": tag,
                    "include_completed": include_completed,
                    "limit": normalized_limit,
                    "detail_level": detail_level,
                },
            }
        except Exception as e:
            logger.error(f"列出 TODO 失败: {e}", exc_info=True)
            return False, f"列出失败: {e}"


# 导出所有 TODO 工具
TODO_TOOLS = [
    LifeEngineManageTodoTool,
    LifeEngineListTodosTool,
]
