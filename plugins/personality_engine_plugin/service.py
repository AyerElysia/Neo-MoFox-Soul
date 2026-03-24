"""personality_engine_plugin 服务。"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from src.app.plugin_system.base import BaseService
from src.app.plugin_system.api import llm_api
from src.kernel.llm import LLMContextManager
from src.kernel.llm.payload import LLMPayload, Text
from src.kernel.llm.roles import ROLE
from src.kernel.logger import get_logger

from .config import PersonalityEngineConfig
from .prompts import (
    build_prompt_block,
    build_reflection_reason,
    build_selector_system_prompt,
    build_selector_user_prompt,
)


logger = get_logger("personality_engine_plugin")

_STATE_VERSION = 1
_STREAM_LOCKS: dict[str, asyncio.Lock] = {}
_SERVICE_INSTANCE: "PersonalityEngineService | None" = None

FUNCTIONS: tuple[str, ...] = ("Ti", "Te", "Fi", "Fe", "Ni", "Ne", "Si", "Se")

DEFAULT_WEIGHTS: dict[str, dict[str, float]] = {
    "INTP": {"Ti": 0.47, "Ne": 0.23, "Si": 0.05, "Fe": 0.05, "Te": 0.05, "Ni": 0.05, "Se": 0.05, "Fi": 0.05},
    "INTJ": {"Ti": 0.05, "Ne": 0.05, "Si": 0.05, "Fe": 0.05, "Te": 0.22, "Ni": 0.48, "Se": 0.05, "Fi": 0.05},
    "INFP": {"Ti": 0.05, "Ne": 0.28, "Si": 0.05, "Fe": 0.05, "Te": 0.05, "Ni": 0.05, "Se": 0.05, "Fi": 0.42},
    "INFJ": {"Ti": 0.05, "Ne": 0.05, "Si": 0.05, "Fe": 0.27, "Te": 0.05, "Ni": 0.43, "Se": 0.05, "Fi": 0.05},
    "ISTP": {"Ti": 0.46, "Ne": 0.05, "Si": 0.05, "Fe": 0.05, "Te": 0.05, "Ni": 0.05, "Se": 0.24, "Fi": 0.05},
    "ISTJ": {"Ti": 0.05, "Ne": 0.05, "Si": 0.44, "Fe": 0.05, "Te": 0.26, "Ni": 0.05, "Se": 0.05, "Fi": 0.05},
    "ISFP": {"Ti": 0.05, "Ne": 0.05, "Si": 0.05, "Fe": 0.05, "Te": 0.05, "Ni": 0.05, "Se": 0.21, "Fi": 0.49},
    "ISFJ": {"Ti": 0.05, "Ne": 0.05, "Si": 0.45, "Fe": 0.25, "Te": 0.05, "Ni": 0.05, "Se": 0.05, "Fi": 0.05},
    "ENFP": {"Ti": 0.05, "Ne": 0.41, "Si": 0.05, "Fe": 0.05, "Te": 0.05, "Ni": 0.05, "Se": 0.05, "Fi": 0.29},
    "ENFJ": {"Ti": 0.05, "Ne": 0.05, "Si": 0.05, "Fe": 0.55, "Te": 0.05, "Ni": 0.15, "Se": 0.05, "Fi": 0.05},
    "ENTP": {"Ti": 0.20, "Ne": 0.50, "Si": 0.05, "Fe": 0.05, "Te": 0.05, "Ni": 0.05, "Se": 0.05, "Fi": 0.05},
    "ENTJ": {"Ti": 0.05, "Ne": 0.05, "Si": 0.05, "Fe": 0.05, "Te": 0.53, "Ni": 0.17, "Se": 0.05, "Fi": 0.05},
    "ESFP": {"Ti": 0.05, "Ne": 0.05, "Si": 0.05, "Fe": 0.05, "Te": 0.05, "Ni": 0.05, "Se": 0.52, "Fi": 0.18},
    "ESFJ": {"Ti": 0.05, "Ne": 0.05, "Si": 0.30, "Fe": 0.40, "Te": 0.05, "Ni": 0.05, "Se": 0.05, "Fi": 0.05},
    "ESTP": {"Ti": 0.19, "Ne": 0.05, "Si": 0.05, "Fe": 0.05, "Te": 0.05, "Ni": 0.05, "Se": 0.51, "Fi": 0.05},
    "ESTJ": {"Ti": 0.05, "Ne": 0.05, "Si": 0.16, "Fe": 0.05, "Te": 0.54, "Ni": 0.05, "Se": 0.05, "Fi": 0.05},
}

MBTI_TO_FUNCTION: dict[str, dict[str, str]] = {
    "INTP": {"main": "Ti", "aux": "Ne"},
    "ISTP": {"main": "Ti", "aux": "Se"},
    "ENFP": {"main": "Ne", "aux": "Fi"},
    "ESFP": {"main": "Se", "aux": "Fi"},
    "INTJ": {"main": "Ni", "aux": "Te"},
    "ISTJ": {"main": "Si", "aux": "Te"},
    "ENFJ": {"main": "Fe", "aux": "Ni"},
    "ESFJ": {"main": "Fe", "aux": "Si"},
    "INFP": {"main": "Fi", "aux": "Ne"},
    "ISFP": {"main": "Fi", "aux": "Se"},
    "ENTP": {"main": "Ne", "aux": "Ti"},
    "ESTP": {"main": "Se", "aux": "Ti"},
    "INFJ": {"main": "Ni", "aux": "Fe"},
    "ISFJ": {"main": "Si", "aux": "Fe"},
    "ENTJ": {"main": "Te", "aux": "Ni"},
    "ESTJ": {"main": "Te", "aux": "Si"},
}

FUNCTION_TO_MBTI: dict[str, str] = {
    "TiNe": "INTP",
    "NiTe": "INTJ",
    "FiNe": "INFP",
    "NiFe": "INFJ",
    "TiSe": "ISTP",
    "SiTe": "ISTJ",
    "FiSe": "ISFP",
    "SiFe": "ISFJ",
    "NeFi": "ENFP",
    "FeNi": "ENFJ",
    "NeTi": "ENTP",
    "TeNi": "ENTJ",
    "SeFi": "ESFP",
    "FeSi": "ESFJ",
    "SeTi": "ESTP",
    "TeSi": "ESTJ",
}

CHANGE_LIST: dict[str, str] = {
    "Ti": "Fi",
    "Fi": "Ti",
    "Te": "Fe",
    "Fe": "Te",
    "Ni": "Si",
    "Si": "Ni",
    "Ne": "Se",
    "Se": "Ne",
}

MAIN_TO_AUX: dict[str, list[str]] = {
    "Ti": ["Ne", "Se"],
    "Te": ["Ni", "Si"],
    "Ni": ["Te", "Fe"],
    "Ne": ["Fi", "Ti"],
    "Fi": ["Ne", "Se"],
    "Fe": ["Ni", "Si"],
    "Si": ["Fe", "Te"],
    "Se": ["Fi", "Ti"],
}


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _clean_weights(weights: dict[str, Any]) -> dict[str, float]:
    result: dict[str, float] = {}
    for func in FUNCTIONS:
        try:
            value = float(weights.get(func, 0.0))
        except Exception:
            value = 0.0
        result[func] = max(0.0, value)
    total = sum(result.values())
    if total <= 0:
        step = 1.0 / len(FUNCTIONS)
        for func in FUNCTIONS:
            result[func] = step
        return result
    for func in FUNCTIONS:
        result[func] = result[func] / total
    return result


def _clean_change_history(change_history: dict[str, Any] | None = None) -> dict[str, float]:
    result: dict[str, float] = {}
    source = change_history or {}
    for func in FUNCTIONS:
        try:
            value = float(source.get(func, 0.0))
        except Exception:
            value = 0.0
        result[func] = max(0.0, value)
    return result


@dataclass
class PersonalityChangeRecord:
    """人格结构变化记录。"""

    changed_at: str
    trigger: str
    selected_function: str
    old_mbti: str
    new_mbti: str
    reason: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonalityChangeRecord":
        return cls(
            changed_at=str(data.get("changed_at", "")),
            trigger=str(data.get("trigger", "")),
            selected_function=str(data.get("selected_function", "")),
            old_mbti=str(data.get("old_mbti", "")),
            new_mbti=str(data.get("new_mbti", "")),
            reason=str(data.get("reason", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "changed_at": self.changed_at,
            "trigger": self.trigger,
            "selected_function": self.selected_function,
            "old_mbti": self.old_mbti,
            "new_mbti": self.new_mbti,
            "reason": self.reason,
        }


@dataclass
class PersonalityState:
    """单个聊天流的人格状态。"""

    stream_id: str
    chat_type: str
    platform: str = ""
    stream_name: str = ""
    updated_at: str = ""
    message_count_since_scan: int = 0
    mbti: str = "INTJ"
    weights: dict[str, float] = field(default_factory=dict)
    change_history: dict[str, float] = field(default_factory=dict)
    last_selected_function: str = ""
    current_hypothesis: str = ""
    history: list[PersonalityChangeRecord] = field(default_factory=list)

    @classmethod
    def empty(
        cls,
        *,
        stream_id: str,
        chat_type: str,
        mbti: str,
        platform: str = "",
        stream_name: str = "",
    ) -> "PersonalityState":
        default_weights = DEFAULT_WEIGHTS.get(mbti) or DEFAULT_WEIGHTS["INTJ"]
        return cls(
            stream_id=stream_id,
            chat_type=chat_type,
            platform=platform,
            stream_name=stream_name,
            updated_at=_now_iso(),
            message_count_since_scan=0,
            mbti=mbti,
            weights=_clean_weights(default_weights),
            change_history=_clean_change_history(),
            last_selected_function="",
            current_hypothesis="",
            history=[],
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PersonalityState":
        history_raw = data.get("history", [])
        records = [
            PersonalityChangeRecord.from_dict(item)
            for item in history_raw
            if isinstance(item, dict)
        ]
        return cls(
            stream_id=str(data.get("stream_id", "")),
            chat_type=str(data.get("chat_type", "private")),
            platform=str(data.get("platform", "")),
            stream_name=str(data.get("stream_name", "")),
            updated_at=str(data.get("updated_at", "")),
            message_count_since_scan=int(data.get("message_count_since_scan", 0) or 0),
            mbti=str(data.get("mbti", "INTJ")),
            weights=_clean_weights(data.get("weights", {})),
            change_history=_clean_change_history(data.get("change_history", {})),
            last_selected_function=str(data.get("last_selected_function", "")),
            current_hypothesis=str(data.get("current_hypothesis", "")),
            history=records,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": _STATE_VERSION,
            "stream_id": self.stream_id,
            "chat_type": self.chat_type,
            "platform": self.platform,
            "stream_name": self.stream_name,
            "updated_at": self.updated_at,
            "message_count_since_scan": self.message_count_since_scan,
            "mbti": self.mbti,
            "weights": dict(self.weights),
            "change_history": dict(self.change_history),
            "last_selected_function": self.last_selected_function,
            "current_hypothesis": self.current_hypothesis,
            "history": [item.to_dict() for item in self.history],
        }


def get_personality_engine_service() -> "PersonalityEngineService | None":
    """获取人格服务单例。"""
    return _SERVICE_INSTANCE


class PersonalityEngineService(BaseService):
    """人格引擎服务。"""

    service_name = "personality_engine_service"
    service_description = "按聊天流维护 JPAF 人格状态并持续推进"
    version = "1.0.0"

    def __init__(self, plugin: Any) -> None:
        super().__init__(plugin)

    def _cfg(self) -> PersonalityEngineConfig:
        cfg = getattr(self.plugin, "config", None)
        if not isinstance(cfg, PersonalityEngineConfig):
            raise RuntimeError("personality_engine_plugin config 未正确加载")
        return cfg

    def _is_enabled(self) -> bool:
        try:
            return bool(self._cfg().plugin.enabled)
        except RuntimeError:
            return False

    def _normalize_chat_type(self, chat_type: str | None) -> str:
        raw = str(chat_type or "").lower().strip()
        if raw in {"private", "group", "discuss"}:
            return raw
        if raw == "guild":
            return "group"
        return "private"

    def _get_base_path(self) -> Path:
        return Path(self._cfg().storage.base_path)

    def _default_mbti(self) -> str:
        mbti = str(self._cfg().personality.default_mbti or "INTJ").upper().strip()
        if mbti in DEFAULT_WEIGHTS:
            return mbti
        return "INTJ"

    def _get_state_path(self, stream_id: str, chat_type: str) -> Path:
        path = self._get_base_path() / self._normalize_chat_type(chat_type) / f"{stream_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _find_existing_state_path(self, stream_id: str) -> tuple[str, Path] | None:
        for chat_type in ("private", "group", "discuss"):
            path = self._get_state_path(stream_id, chat_type)
            if path.exists():
                return chat_type, path
        return None

    def _load_state_from_path(
        self,
        path: Path,
        *,
        stream_id: str,
        chat_type: str,
        platform: str = "",
        stream_name: str = "",
    ) -> PersonalityState:
        if not path.exists():
            return PersonalityState.empty(
                stream_id=stream_id,
                chat_type=self._normalize_chat_type(chat_type),
                mbti=self._default_mbti(),
                platform=platform,
                stream_name=stream_name,
            )

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error(f"读取人格状态失败：{path} - {exc}")
            return PersonalityState.empty(
                stream_id=stream_id,
                chat_type=self._normalize_chat_type(chat_type),
                mbti=self._default_mbti(),
                platform=platform,
                stream_name=stream_name,
            )

        state = PersonalityState.from_dict(data)
        if not state.stream_id:
            state.stream_id = stream_id
        state.chat_type = self._normalize_chat_type(state.chat_type or chat_type)
        if platform and not state.platform:
            state.platform = platform
        if stream_name and not state.stream_name:
            state.stream_name = stream_name
        if state.mbti not in DEFAULT_WEIGHTS:
            state.mbti = self._default_mbti()
            state.weights = _clean_weights(DEFAULT_WEIGHTS[state.mbti])
            state.change_history = _clean_change_history()
        return state

    def _save_state(self, state: PersonalityState) -> None:
        state.updated_at = _now_iso()
        state.weights = _clean_weights(state.weights)
        state.change_history = _clean_change_history(state.change_history)
        path = self._get_state_path(state.stream_id, state.chat_type)
        path.write_text(
            json.dumps(state.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _get_lock(self, stream_id: str) -> asyncio.Lock:
        lock = _STREAM_LOCKS.get(stream_id)
        if lock is None:
            lock = asyncio.Lock()
            _STREAM_LOCKS[stream_id] = lock
        return lock

    def get_state(
        self,
        stream_id: str,
        chat_type: str | None = None,
        *,
        platform: str = "",
        stream_name: str = "",
    ) -> PersonalityState:
        normalized = self._normalize_chat_type(chat_type)
        if chat_type is None:
            found = self._find_existing_state_path(stream_id)
            if found is not None:
                normalized, path = found
                return self._load_state_from_path(
                    path,
                    stream_id=stream_id,
                    chat_type=normalized,
                    platform=platform,
                    stream_name=stream_name,
                )
        path = self._get_state_path(stream_id, normalized)
        return self._load_state_from_path(
            path,
            stream_id=stream_id,
            chat_type=normalized,
            platform=platform,
            stream_name=stream_name,
        )

    def _get_stream(self, stream_id: str) -> Any | None:
        try:
            from src.core.managers import get_stream_manager

            return get_stream_manager()._streams.get(stream_id)
        except Exception:
            return None

    def _get_stream_meta(
        self,
        stream_id: str,
        chat_type: str | None = None,
        *,
        platform: str = "",
        stream_name: str = "",
    ) -> tuple[str, str, str]:
        stream = self._get_stream(stream_id)
        if stream is not None:
            chat_type = str(getattr(stream, "chat_type", chat_type or "private"))
            platform = str(getattr(stream, "platform", platform or ""))
            stream_name = str(getattr(stream, "stream_name", stream_name or ""))
        return (
            self._normalize_chat_type(chat_type),
            platform or "",
            stream_name or "",
        )

    def _collect_recent_messages(self, stream_id: str, window_size: int) -> str:
        stream = self._get_stream(stream_id)
        if stream is None:
            return ""
        context = getattr(stream, "context", None)
        if context is None:
            return ""

        history = list(getattr(context, "history_messages", []) or [])
        unread = list(getattr(context, "unread_messages", []) or [])
        merged = history + unread
        recent = merged[-window_size:] if len(merged) > window_size else merged

        lines: list[str] = []
        for msg in recent:
            sender = str(
                getattr(msg, "sender_name", "")
                or getattr(msg, "sender_id", "")
                or "unknown"
            )
            content = str(
                getattr(msg, "processed_plain_text", "")
                or getattr(msg, "content", "")
                or ""
            ).strip()
            if content:
                lines.append(f"{sender}: {content}")
        return "\n".join(lines)

    def _parse_json_blob(self, raw: str) -> dict[str, Any] | None:
        if not raw:
            return None
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return None
        return None

    def _select_function_heuristic(self, text: str, mbti: str) -> tuple[str, str, str]:
        lowered = text.lower()
        rules: list[tuple[str, tuple[str, ...], str]] = [
            ("Ti", ("logic", "analy", "principle", "reason"), "更偏向内部逻辑分析"),
            ("Te", ("plan", "organize", "efficien", "execute"), "更偏向外部执行与组织"),
            ("Fi", ("value", "moral", "authentic", "inner feeling"), "更偏向个人价值判断"),
            ("Fe", ("relationship", "harmony", "others", "social"), "更偏向关系协调"),
            ("Ni", ("pattern", "insight", "future", "trend"), "更偏向抽象洞察"),
            ("Ne", ("idea", "possibilit", "brainstorm", "explore"), "更偏向可能性探索"),
            ("Si", ("memory", "detail", "past", "habit"), "更偏向经验回溯"),
            ("Se", ("immediate", "action", "now", "sensory"), "更偏向即时行动"),
        ]
        for func, keywords, reason in rules:
            if any(keyword in lowered for keyword in keywords):
                return func, reason, f"启发式判定：{func} 活跃"
        main_func = MBTI_TO_FUNCTION.get(mbti, {}).get("main", "Ni")
        return main_func, "无显著关键词，回退主导功能", f"回退到主导功能 {main_func}"

    def _build_model_set(self) -> list[dict[str, Any]] | None:
        task_name = str(self._cfg().model.task_name or "").strip() or "actor"
        fallback_task_name = str(self._cfg().model.fallback_task_name or "").strip() or "diary"
        try:
            return llm_api.get_model_set_by_task(task_name)
        except Exception:
            try:
                return llm_api.get_model_set_by_task(fallback_task_name)
            except Exception as exc:
                logger.warning(f"人格引擎模型获取失败：{task_name}/{fallback_task_name} - {exc}")
                return None

    async def _select_function_with_llm(
        self,
        *,
        trigger: str,
        state: PersonalityState,
        recent_messages: str,
    ) -> tuple[str, str, str] | None:
        if not self._cfg().model.enable_llm_selector:
            return None

        model_set = self._build_model_set()
        if not model_set:
            return None

        retries = self._cfg().personality.max_parse_retries + 1
        for _ in range(retries):
            request = llm_api.create_llm_request(
                model_set=model_set,
                request_name="personality_engine_select_function",
                context_manager=LLMContextManager(max_payloads=4),
            )
            request.add_payload(
                LLMPayload(ROLE.SYSTEM, Text(build_selector_system_prompt()))
            )
            request.add_payload(
                LLMPayload(
                    ROLE.USER,
                    Text(
                        build_selector_user_prompt(
                            trigger=trigger,
                            mbti=state.mbti,
                            weights=state.weights,
                            recent_messages=recent_messages,
                        )
                    ),
                )
            )

            try:
                response = await request.send(stream=False)
                result_text = response.message or await response
            except Exception as exc:
                logger.warning(f"人格引擎功能选择调用失败：{exc}")
                return None

            parsed = self._parse_json_blob(str(result_text or ""))
            if parsed is None:
                continue

            function_name = str(parsed.get("function", "")).strip()
            reason = str(parsed.get("reason", "")).strip()
            hypothesis = str(parsed.get("hypothesis", "")).strip()
            if function_name in FUNCTIONS:
                return function_name, reason or "LLM 选择", hypothesis

        return None

    def _temp_weight(self, state: PersonalityState, func: str) -> float:
        return float(state.weights.get(func, 0.0) + state.change_history.get(func, 0.0))

    def _normalize_weights_with_change_history(self, state: PersonalityState) -> None:
        merged: dict[str, float] = {}
        for func in FUNCTIONS:
            merged[func] = max(0.0, self._temp_weight(state, func))
        state.weights = _clean_weights(merged)
        state.change_history = _clean_change_history()

    def _apply_mbti_change(
        self,
        state: PersonalityState,
        *,
        new_main: str,
        new_aux: str,
    ) -> str:
        key = f"{new_main}{new_aux}"
        new_mbti = FUNCTION_TO_MBTI.get(key, state.mbti)

        # 结构变更时，降低旧主辅，提升新主辅，然后整体归一
        old_main = MBTI_TO_FUNCTION.get(state.mbti, {}).get("main", "")
        old_aux = MBTI_TO_FUNCTION.get(state.mbti, {}).get("aux", "")

        if old_main in state.weights:
            state.weights[old_main] = min(state.weights[old_main], 0.30)
        if old_aux in state.weights:
            state.weights[old_aux] = min(state.weights[old_aux], 0.06)

        state.weights[new_main] = max(self._temp_weight(state, new_main), 0.31)
        state.weights[new_aux] = max(self._temp_weight(state, new_aux), 0.07)

        state.weights = _clean_weights(state.weights)
        state.change_history = _clean_change_history()
        state.mbti = new_mbti
        return new_mbti

    def _decay_change_history(self, state: PersonalityState) -> None:
        decay = float(self._cfg().personality.change_history_decay)
        for func in FUNCTIONS:
            state.change_history[func] = max(
                0.0,
                float(state.change_history.get(func, 0.0)) * decay,
            )

    def _apply_reflection(
        self,
        state: PersonalityState,
        *,
        selected_function: str,
        trigger: str,
    ) -> tuple[bool, str]:
        old_mbti = state.mbti
        mapping = MBTI_TO_FUNCTION.get(state.mbti)
        if mapping is None:
            state.mbti = self._default_mbti()
            state.weights = _clean_weights(DEFAULT_WEIGHTS[state.mbti])
            state.change_history = _clean_change_history()
            return False, "invalid_mbti_reset"

        main_func = mapping["main"]
        aux_func = mapping["aux"]
        selected_temp = self._temp_weight(state, selected_function)
        main_weight = float(state.weights.get(main_func, 0.0))
        aux_weight = float(state.weights.get(aux_func, 0.0))

        # reflection1: 辅助功能超过主导 -> 主辅互换
        if selected_function == aux_func and selected_temp >= main_weight:
            new_mbti = self._apply_mbti_change(
                state,
                new_main=aux_func,
                new_aux=main_func,
            )
            return True, build_reflection_reason(
                action="swap_main_aux",
                old_mbti=old_mbti,
                new_mbti=new_mbti,
                selected_function=selected_function,
            )

        # main 功能过高时直接归一（短期稳定）
        if selected_function == main_func:
            threshold = float(self._cfg().personality.normalize_main_threshold)
            if selected_temp >= threshold:
                self._normalize_weights_with_change_history(state)
                return False, "normalize_main_threshold"
            self._decay_change_history(state)
            return False, "main_selected_decay"

        if selected_function not in {main_func, aux_func}:
            counterpart = CHANGE_LIST.get(selected_function, "")

            # reflection2: 仅主导变化
            if counterpart == main_func and selected_temp >= main_weight:
                new_mbti = self._apply_mbti_change(
                    state,
                    new_main=selected_function,
                    new_aux=aux_func,
                )
                return True, build_reflection_reason(
                    action="change_main",
                    old_mbti=old_mbti,
                    new_mbti=new_mbti,
                    selected_function=selected_function,
                )

            # reflection3: 仅辅助变化
            if counterpart == aux_func and selected_temp >= aux_weight:
                new_mbti = self._apply_mbti_change(
                    state,
                    new_main=main_func,
                    new_aux=selected_function,
                )
                return True, build_reflection_reason(
                    action="change_aux",
                    old_mbti=old_mbti,
                    new_mbti=new_mbti,
                    selected_function=selected_function,
                )

            # reflection4: 主辅重构
            if selected_temp >= main_weight:
                candidates = MAIN_TO_AUX.get(selected_function, [aux_func, main_func])
                best_aux = max(candidates, key=lambda func: self._temp_weight(state, func))
                new_mbti = self._apply_mbti_change(
                    state,
                    new_main=selected_function,
                    new_aux=best_aux,
                )
                return True, build_reflection_reason(
                    action="reorganize_main_aux",
                    old_mbti=old_mbti,
                    new_mbti=new_mbti,
                    selected_function=selected_function,
                    extra={"new_aux": best_aux},
                )

        self._decay_change_history(state)
        return False, "no_structure_change"

    async def advance_personality_step(
        self,
        *,
        stream_id: str,
        chat_type: str,
        platform: str = "",
        stream_name: str = "",
        trigger: str = "auto",
    ) -> tuple[bool, str]:
        """推进一次人格更新。"""
        if not self._is_enabled():
            return False, "personality_engine_plugin 未启用"

        normalized_chat_type, platform, stream_name = self._get_stream_meta(
            stream_id,
            chat_type,
            platform=platform,
            stream_name=stream_name,
        )

        async with self._get_lock(stream_id):
            state = self.get_state(
                stream_id=stream_id,
                chat_type=normalized_chat_type,
                platform=platform,
                stream_name=stream_name,
            )

            recent_messages = self._collect_recent_messages(
                stream_id,
                self._cfg().scan.max_context_messages,
            )
            selection = await self._select_function_with_llm(
                trigger=trigger,
                state=state,
                recent_messages=recent_messages,
            )
            if selection is None:
                selection = self._select_function_heuristic(recent_messages, state.mbti)
            selected_function, reason, hypothesis = selection
            if selected_function not in FUNCTIONS:
                selected_function = MBTI_TO_FUNCTION.get(state.mbti, {}).get("main", "Ni")

            state.last_selected_function = selected_function
            state.current_hypothesis = hypothesis or reason or "暂无"
            state.change_history[selected_function] = (
                float(state.change_history.get(selected_function, 0.0))
                + float(self._cfg().personality.change_weight)
            )

            old_mbti = state.mbti
            changed, reflection_reason = self._apply_reflection(
                state,
                selected_function=selected_function,
                trigger=trigger,
            )
            if changed:
                state.history.insert(
                    0,
                    PersonalityChangeRecord(
                        changed_at=_now_iso(),
                        trigger=trigger,
                        selected_function=selected_function,
                        old_mbti=old_mbti,
                        new_mbti=state.mbti,
                        reason=reflection_reason,
                    ),
                )
                state.history = state.history[: self._cfg().storage.max_history_records]

            state.message_count_since_scan = 0
            self._save_state(state)
            return True, self.render_state_summary(
                stream_id=stream_id,
                chat_type=normalized_chat_type,
            )

    async def observe_chat_turn(
        self,
        *,
        stream_id: str,
        chat_type: str,
        platform: str = "",
        stream_name: str = "",
        trigger: str = "auto",
    ) -> tuple[bool, str]:
        """记录一次对话推进，达到阈值时触发人格更新。"""
        if not self._is_enabled():
            return False, "personality_engine_plugin 未启用"

        normalized_chat_type, platform, stream_name = self._get_stream_meta(
            stream_id,
            chat_type,
            platform=platform,
            stream_name=stream_name,
        )

        async with self._get_lock(stream_id):
            state = self.get_state(
                stream_id=stream_id,
                chat_type=normalized_chat_type,
                platform=platform,
                stream_name=stream_name,
            )
            state.message_count_since_scan += 1
            threshold = int(self._cfg().scan.trigger_every_n_messages)
            should_advance = state.message_count_since_scan >= threshold
            if not should_advance:
                self._save_state(state)
                return True, self.render_state_summary(
                    stream_id=stream_id,
                    chat_type=normalized_chat_type,
                )

        return await self.advance_personality_step(
            stream_id=stream_id,
            chat_type=normalized_chat_type,
            platform=platform,
            stream_name=stream_name,
            trigger=trigger,
        )

    def render_state_summary(
        self,
        *,
        stream_id: str,
        chat_type: str | None = None,
    ) -> str:
        """渲染当前人格状态摘要。"""
        state = self.get_state(stream_id=stream_id, chat_type=chat_type)
        mapping = MBTI_TO_FUNCTION.get(state.mbti, {"main": "?", "aux": "?"})
        lines = [
            "【人格状态】",
            f"- 聊天流: {state.stream_id[:8]} / {state.chat_type}",
            f"- MBTI: {state.mbti}",
            f"- 主辅: {mapping['main']}-{mapping['aux']}",
            f"- 本轮补偿: {state.last_selected_function or '暂无'}",
            f"- 假设: {state.current_hypothesis or '暂无'}",
            f"- 推进计数: {state.message_count_since_scan}",
        ]
        return "\n".join(lines)

    def render_prompt_block(
        self,
        *,
        stream_id: str,
        chat_type: str | None = None,
    ) -> str:
        """渲染 prompt 注入块。"""
        if not self._cfg().plugin.inject_prompt:
            return ""
        state = self.get_state(stream_id=stream_id, chat_type=chat_type)
        mapping = MBTI_TO_FUNCTION.get(state.mbti)
        if mapping is None:
            return ""
        detail = str(self._cfg().prompt.inject_detail_level).strip().lower() == "detail"
        return build_prompt_block(
            title=self._cfg().prompt.prompt_title,
            mbti=state.mbti,
            main_func=mapping["main"],
            aux_func=mapping["aux"],
            selected_function=state.last_selected_function,
            hypothesis=state.current_hypothesis,
            weights=state.weights,
            detail=detail,
        )

    def reset_state(
        self,
        *,
        stream_id: str,
        chat_type: str,
        platform: str = "",
        stream_name: str = "",
    ) -> tuple[bool, str]:
        """重置聊天流人格状态。"""
        mbti = self._default_mbti()
        state = PersonalityState.empty(
            stream_id=stream_id,
            chat_type=self._normalize_chat_type(chat_type),
            mbti=mbti,
            platform=platform,
            stream_name=stream_name,
        )
        self._save_state(state)
        return True, f"已重置人格状态为 {mbti}"

    def set_mbti(
        self,
        *,
        stream_id: str,
        chat_type: str,
        mbti: str,
        platform: str = "",
        stream_name: str = "",
    ) -> tuple[bool, str]:
        """设置指定聊天流 MBTI。"""
        normalized = str(mbti or "").upper().strip()
        if normalized not in DEFAULT_WEIGHTS:
            return False, f"无效 MBTI: {normalized}"
        state = PersonalityState.empty(
            stream_id=stream_id,
            chat_type=self._normalize_chat_type(chat_type),
            mbti=normalized,
            platform=platform,
            stream_name=stream_name,
        )
        self._save_state(state)
        return True, f"已设置 MBTI 为 {normalized}"


def initialize_personality_engine_service(plugin: Any) -> PersonalityEngineService:
    """初始化人格引擎服务单例。"""
    global _SERVICE_INSTANCE
    if _SERVICE_INSTANCE is None:
        _SERVICE_INSTANCE = PersonalityEngineService(plugin)
        logger.info("personality_engine_service 已初始化")
    else:
        _SERVICE_INSTANCE.plugin = plugin
    return _SERVICE_INSTANCE

