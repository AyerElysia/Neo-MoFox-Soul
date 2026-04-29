"""Default Chatter 上下文压缩工具。"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from typing import Any

from src.kernel.llm import LLMPayload, ROLE, Text, ToolCall, ToolResult

_MAX_SUMMARY_GROUPS = 8
_MAX_SUMMARY_CHARS = 3200
_MAX_TEXT_CHARS = 220
_MAX_TOOL_RESULT_CHARS = 220
_MAX_TOOL_ARGS_CHARS = 900
_MAX_LIST_ITEMS = 8
_NOISE_TEXTS = {"__SUSPEND__"}


def build_default_chatter_compression_hook() -> Callable[[list[list[LLMPayload]], list[LLMPayload]], list[LLMPayload]]:
    """构建 default_chatter 的确定性压缩钩子。"""

    def _hook(
        dropped_groups: list[list[LLMPayload]],
        _remaining_payloads: list[LLMPayload],
    ) -> list[LLMPayload]:
        summary_text = _build_summary_text(dropped_groups)
        if not summary_text:
            return []
        return [LLMPayload(ROLE.USER, Text(summary_text))]

    return _hook


def _build_summary_text(dropped_groups: list[list[LLMPayload]]) -> str:
    if not dropped_groups:
        return ""

    groups = dropped_groups[-_MAX_SUMMARY_GROUPS:]
    skipped_groups = max(0, len(dropped_groups) - len(groups))
    rendered_groups: list[str] = []

    for index, group in enumerate(groups, start=1):
        rendered = _render_group(index, group)
        if not rendered:
            continue
        candidate = _render_summary([*rendered_groups, rendered], skipped_groups)
        if len(candidate) > _MAX_SUMMARY_CHARS:
            break
        rendered_groups.append(rendered)

    if not rendered_groups:
        return ""

    return _render_summary(rendered_groups, skipped_groups)


def _render_summary(rendered_groups: list[str], skipped_groups: int) -> str:
    prefix_lines = [
        "【系统自动压缩的更早 payload 转录】",
        "以下内容来自被裁剪的旧轮 payload，按旧结构保留关键信息，供你延续工具状态与对话上下文时参考。",
    ]
    if skipped_groups > 0:
        prefix_lines.append(f"更早的 {skipped_groups} 轮已进一步省略。")
    return "\n\n".join([*prefix_lines, *rendered_groups])


def _render_group(index: int, group: list[LLMPayload]) -> str:
    lines: list[str] = [f"### 旧轮 {index}"]

    for payload in group:
        payload_lines = _render_payload(payload)
        if payload_lines:
            lines.extend(payload_lines)

    if len(lines) == 1:
        return ""
    return "\n".join(lines)


def _render_payload(payload: LLMPayload) -> list[str]:
    lines: list[str] = []

    for part in payload.content:
        if isinstance(part, Text):
            normalized = _normalize_text(part.text)
            if not normalized:
                continue
            if payload.role == ROLE.USER:
                lines.append(f"- USER: {_shorten(normalized, _MAX_TEXT_CHARS)}")
            elif payload.role == ROLE.ASSISTANT:
                lines.append(f"- ASSISTANT: {_shorten(normalized, _MAX_TEXT_CHARS)}")
            elif payload.role == ROLE.TOOL_RESULT:
                lines.append(f"- TOOL_RESULT: {_shorten(normalized, _MAX_TOOL_RESULT_CHARS)}")
            continue

        if isinstance(part, ToolCall):
            rendered_call = _render_tool_call(part)
            if rendered_call:
                lines.append(f"- TOOL_CALL: {rendered_call}")
            continue

        if isinstance(part, ToolResult):
            rendered_result = _render_tool_result(part)
            if rendered_result:
                lines.append(f"- TOOL_RESULT: {rendered_result}")

    return lines


def _render_tool_call(call: ToolCall) -> str:
    name = str(call.name or "").strip()
    if not name:
        return ""

    if isinstance(call.args, dict):
        cleaned_args = _clean_tool_args(name, call.args)
        try:
            args_text = json.dumps(
                cleaned_args,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        except Exception:
            args_text = str(cleaned_args)
    else:
        args_text = _shorten(_normalize_text(str(call.args or "")), _MAX_TOOL_ARGS_CHARS)

    return f"ToolCall(name={name!r}, args={_shorten(args_text, _MAX_TOOL_ARGS_CHARS)})"


def _render_tool_result(result: ToolResult) -> str:
    tool_name = str(result.name or "tool").strip() or "tool"
    if isinstance(result.value, str):
        value_text = result.value
    else:
        try:
            value_text = result.to_text()
        except Exception:
            value_text = str(result.value)
    normalized = _normalize_text(value_text)
    if not normalized:
        return ""
    return f"{tool_name} => {_shorten(normalized, _MAX_TOOL_RESULT_CHARS)}"


def _clean_tool_args(name: str, args: dict[str, Any]) -> dict[str, Any]:
    filtered = {
        key: value
        for key, value in args.items()
        if key != "reason" and value not in (None, "", [], {})
    }

    ordered_keys: list[str] | None = None
    if name == "action-think":
        ordered_keys = ["decision", "expected_response", "mood", "thought"]
    elif name in {"action-send_text", "send_text"}:
        ordered_keys = ["content", "reply_to"]
    elif name == "action-pass_and_wait":
        ordered_keys = []

    if ordered_keys is not None:
        ordered: dict[str, Any] = {}
        for key in ordered_keys:
            if key in filtered:
                ordered[key] = _clip_json_value(filtered[key])
        for key, value in filtered.items():
            if key not in ordered:
                ordered[key] = _clip_json_value(value)
        return ordered

    return {key: _clip_json_value(value) for key, value in filtered.items()}


def _clip_json_value(value: Any) -> Any:
    if isinstance(value, str):
        return _shorten(_normalize_text(value), 360)
    if isinstance(value, list):
        clipped_items = [_clip_json_value(item) for item in value[:_MAX_LIST_ITEMS]]
        if len(value) > _MAX_LIST_ITEMS:
            clipped_items.append("...(已截断)")
        return clipped_items
    if isinstance(value, dict):
        items = list(value.items())
        clipped: dict[str, Any] = {}
        for index, (key, sub_value) in enumerate(items):
            if index >= _MAX_LIST_ITEMS:
                clipped["..."] = "(已截断)"
                break
            clipped[str(key)] = _clip_json_value(sub_value)
        return clipped
    return value


def _normalize_text(text: str) -> str:
    normalized = re.sub(r"\s+", " ", str(text or "")).strip()
    if normalized in _NOISE_TEXTS:
        return ""
    return normalized


def _shorten(text: str, limit: int) -> str:
    normalized = _normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 3)].rstrip() + "..."
