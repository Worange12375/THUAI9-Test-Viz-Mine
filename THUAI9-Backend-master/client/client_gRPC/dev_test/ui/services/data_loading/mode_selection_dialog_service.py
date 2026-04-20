"""Mode selection dialogs service.

搬迁自 main_ui.py：
- _show_source_selection_dialog
- _show_mock_dataset_dialog

约束：保持原 UX/文案/交互完全一致。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Optional


def show_source_selection_dialog(main_ui: object, title: str = "选择数据源") -> Optional[str]:
	"""弹窗选择数据源：后端玩法环境或 mock 回放。"""
	choice: dict[str, Optional[str]] = {"value": None}
	window = tk.Toplevel(getattr(main_ui, "root"))
	window.title(title)
	window.transient(getattr(main_ui, "root"))
	window.grab_set()
	window.resizable(False, False)

	frame = ttk.Frame(window, padding=12)
	frame.pack(fill="both", expand=True)

	ttk.Label(frame, text="请选择本次测试的数据源：").pack(anchor="w", pady=(0, 8))
	var = tk.StringVar(value=getattr(main_ui, "_normalize_selected_source_value")(getattr(main_ui, "selected_source")))

	ttk.Radiobutton(frame, text="手动对局模式（自定义）", value="runtime_custom", variable=var).pack(anchor="w")
	ttk.Radiobutton(frame, text="手动对局模式（职业）", value="runtime_profession", variable=var).pack(anchor="w")
	ttk.Radiobutton(frame, text="mock数据模式", value="mock", variable=var).pack(anchor="w", pady=(0, 8))

	button_row = ttk.Frame(frame)
	button_row.pack(fill="x", pady=(8, 0))

	def on_ok() -> None:
		choice["value"] = getattr(main_ui, "_normalize_selected_source_value")(var.get())
		window.destroy()

	def on_cancel() -> None:
		choice["value"] = None
		window.destroy()

	ttk.Button(button_row, text="取消", command=on_cancel).pack(side="right")
	ttk.Button(button_row, text="确定", command=on_ok).pack(side="right", padx=(0, 6))

	window.protocol("WM_DELETE_WINDOW", on_cancel)
	# 统一走 main_ui 的居中方法（行为等价，但集中到 dialogs service）。
	try:
		getattr(main_ui, "_center_popup_window")(window)
	except Exception:
		pass
	getattr(main_ui, "root").wait_window(window)
	return choice["value"]


def show_mock_dataset_dialog(main_ui: object, title: str = "选择 mock 数据集") -> Optional[str]:
	"""弹窗选择 mock 数据集：用于回放不同测试样例。"""
	datasets = getattr(getattr(main_ui, "controller"), "list_mock_datasets")()
	if not datasets:
		raise RuntimeError("当前没有可用的 mock 数据集")

	choice: dict[str, Optional[str]] = {"value": None}
	window = tk.Toplevel(getattr(main_ui, "root"))
	window.title(title)
	window.transient(getattr(main_ui, "root"))
	window.grab_set()
	window.resizable(False, False)

	frame = ttk.Frame(window, padding=12)
	frame.pack(fill="both", expand=True)

	ttk.Label(frame, text="请选择要加载的 mock 回放数据集：").pack(anchor="w", pady=(0, 8))
	selected_mock_dataset = getattr(main_ui, "selected_mock_dataset", None)
	default_value = selected_mock_dataset if selected_mock_dataset in datasets else datasets[0]
	var = tk.StringVar(value=default_value)

	combo = ttk.Combobox(frame, textvariable=var, values=datasets, state="readonly", width=36)
	combo.pack(fill="x")
	combo.current(datasets.index(default_value))

	button_row = ttk.Frame(frame)
	button_row.pack(fill="x", pady=(8, 0))

	def on_ok() -> None:
		choice["value"] = str(var.get())
		window.destroy()

	def on_cancel() -> None:
		choice["value"] = None
		window.destroy()

	ttk.Button(button_row, text="取消", command=on_cancel).pack(side="right")
	ttk.Button(button_row, text="确定", command=on_ok).pack(side="right", padx=(0, 6))

	window.protocol("WM_DELETE_WINDOW", on_cancel)
	try:
		getattr(main_ui, "_center_popup_window")(window)
	except Exception:
		pass
	getattr(main_ui, "root").wait_window(window)
	return choice["value"]
