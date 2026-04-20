"""Source/mode normalization utilities.

职责：
- 对 UI 中的 selected_source 值做归一化（兼容旧值 runtime）
- 提供 runtime/mock/profession 相关的判定

边界：
- 纯函数，不触碰 UI 控件与 controller。
- main_ui 保留同名方法做薄委托。
"""

from __future__ import annotations


def normalize_selected_source_value(value: str) -> str:
	"""兼容旧值：将 runtime 归一到 runtime_custom。"""
	value_norm = str(value or "").strip().lower()
	if value_norm == "runtime":
		return "runtime_custom"
	if value_norm in ("runtime_custom", "runtime_profession", "mock"):
		return value_norm
	return "runtime_custom"


def is_runtime_selected_source(selected_source: str) -> bool:
	return normalize_selected_source_value(selected_source) in ("runtime_custom", "runtime_profession")


def is_profession_mode(selected_source: str) -> bool:
	return normalize_selected_source_value(selected_source) == "runtime_profession"
