"""共享工具函数模块

供 `api/` 目录下的各 API 模块使用的公共校验工具。
"""

from __future__ import annotations


def _validate_non_empty(value: str, name: str) -> None:
    """校验字符串参数非空。

    Args:
        value: 待校验的字符串
        name: 参数名称

    Returns:
        None
    """
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} 不能为空")
