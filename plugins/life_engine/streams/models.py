"""ThoughtStream 数据模型。"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ThoughtStream:
    """思考流——爱莉持续在意的兴趣线索。

    不是 TODO（任务），不是 Project（项目），而是"我最近一直在琢磨这件事"的持久兴趣。
    给爱莉在心跳间有事可想、有事可追。
    同时承担"长期/中期注意力脑区"中可表达单元的角色。
    """

    id: str
    title: str                          # 人类可读的标题
    created_at: str                     # ISO timestamp
    last_advanced_at: str               # 上次推进时间
    advance_count: int = 0              # 推进次数
    curiosity_score: float = 0.7        # 当前好奇心强度 [0, 1]
    last_thought: str = ""              # 最近一次内心独白
    related_memories: list[str] = field(default_factory=list)  # 关联记忆节点ID
    status: str = "active"              # "active" | "dormant" | "completed"
    # ── 注意力脑区字段（轻量版） ──
    last_focused_at: str = ""           # 上次进入注意力焦点的时间，独立于 advance
    last_decay_at: str = ""             # lazy 半衰期衰减锚点
    revision: int = 0                   # 单调递增版本号（create/advance/retire/reactivate 时 +1）

    def is_active(self) -> bool:
        """检查思考流是否处于活跃状态。"""
        return self.status == "active"

    def should_go_dormant(self, dormancy_hours: int = 24) -> bool:
        """检查是否应该进入休眠。"""
        if self.status != "active":
            return False
        try:
            last = datetime.fromisoformat(self.last_advanced_at)
            now = datetime.now(timezone.utc)
            hours_since = (now - last).total_seconds() / 3600
            return hours_since > dormancy_hours
        except (ValueError, TypeError):
            return False

    def is_focused(self, focus_window_minutes: int) -> bool:
        """是否处于注意力焦点窗口内。

        判定基于独立的 last_focused_at（advance 时刷新；create 不刷新）。
        无 last_focused_at 视为非焦点。
        """
        if self.status != "active":
            return False
        if not self.last_focused_at:
            return False
        try:
            last = datetime.fromisoformat(self.last_focused_at)
            now = datetime.now(timezone.utc)
            minutes_since = (now - last).total_seconds() / 60
            return minutes_since <= focus_window_minutes
        except (ValueError, TypeError):
            return False
