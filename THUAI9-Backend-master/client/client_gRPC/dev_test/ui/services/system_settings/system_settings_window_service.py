"""System settings window framework service.

职责：
- 打开/复用系统设置窗口（Toplevel）
- 构建左侧导航与右侧内容区骨架
- 处理关闭逻辑：若存在未应用（dirty）修改，提示并回滚
- 切换一级页面（general/design/tutorial/dev）

约束：不改变 UX，仅做代码搬家。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from services.system_settings.system_settings_dirty_service import (
	discard_unapplied_system_settings_changes,
	has_any_system_settings_dirty,
)


def open_system_settings_window(main_ui: object) -> None:
	"""打开系统设置窗口（框架）。"""
	window = getattr(main_ui, "system_settings_window", None)
	if window is not None:
		try:
			if window.winfo_exists():
				window.deiconify()
				window.lift()
				window.focus_force()
				switch_system_settings_page(main_ui, "general")
				return
		except Exception:
			pass

	# 关闭系统设置时若存在“未应用（dirty）”修改：按产品约定应自动还原（丢弃未应用）。
	# 注意：综合设置页可能在本次 UI 进程中从未点击过“应用”，因此这里需要建立基线快照，
	# 否则“关闭并丢弃”无法回滚到进入窗口前的状态。
	try:
		if not isinstance(getattr(main_ui, "_applied_system_general_settings_snapshot", None), dict):
			setattr(
				main_ui,
				"_applied_system_general_settings_snapshot",
				getattr(main_ui, "_collect_system_general_settings_snapshot_from_vars")(),
			)
	except Exception:
		pass

	root = getattr(main_ui, "root")	
	window = tk.Toplevel(root)
	window.title("系统设置")
	window.transient(root)
	window.resizable(True, True)
	window.geometry("900x520")
	window.minsize(780, 420)
	setattr(main_ui, "system_settings_window", window)

	main = ttk.Frame(window, padding=10)
	main.pack(fill="both", expand=True)
	main.columnconfigure(0, weight=0)
	main.columnconfigure(1, weight=1)
	main.rowconfigure(0, weight=1)

	nav = ttk.LabelFrame(main, text="分类", padding=8)
	nav.grid(row=0, column=0, sticky="ns", padx=(0, 10))
	nav.columnconfigure(0, weight=1)

	content = ttk.LabelFrame(main, text="系统内容", padding=10)
	content.grid(row=0, column=1, sticky="nsew")
	content.columnconfigure(0, weight=1)
	content.rowconfigure(0, weight=1)
	setattr(main_ui, "system_settings_content_frame", content)

	setattr(main_ui, "system_settings_nav_buttons", {})
	nav_items = [
		("general", "综合设置"),
		("design", "玩法设计"),
		("tutorial", "使用教程"),
		("dev", "开发信息"),
	]
	for row_idx, (page_key, title) in enumerate(nav_items):
		btn = ttk.Button(nav, text=title, command=lambda key=page_key: switch_system_settings_page(main_ui, key))
		btn.grid(row=row_idx, column=0, sticky="ew", pady=(0, 8))
		getattr(main_ui, "system_settings_nav_buttons")[page_key] = btn

	def on_close() -> None:
		# 若存在未应用修改：提示确认。
		try:
			if has_any_system_settings_dirty(main_ui):
				ok = getattr(main_ui, "_show_confirm_dialog")(
					"提示",
					"系统设置存在未应用的修改。\n确定关闭并丢弃这些未应用的修改吗？",
					yes_text="关闭",
					no_text="返回",
				)
				if not ok:
					return
				# 选择“关闭”：回滚到最近一次已应用的状态，并清空 dirty 标记。
				discard_unapplied_system_settings_changes(main_ui)
		except Exception:
			pass

		setattr(main_ui, "system_settings_window", None)
		setattr(main_ui, "system_settings_content_frame", None)
		setattr(main_ui, "system_settings_nav_buttons", {})
		try:
			setattr(main_ui, "_system_settings_dirty_label_vars", {})
		except Exception:
			pass
		window.destroy()

	window.protocol("WM_DELETE_WINDOW", on_close)
	getattr(main_ui, "_center_popup_window")(window)
	switch_system_settings_page(main_ui, "general")


def switch_system_settings_page(main_ui: object, page_key: str) -> None:
	"""切换系统设置窗口的一级页面（框架）。"""
	content = getattr(main_ui, "system_settings_content_frame", None)
	if content is None:
		return
	for widget in content.winfo_children():
		widget.destroy()

	builders = {
		"general": getattr(main_ui, "_build_system_settings_general_page"),
		"design": getattr(main_ui, "_build_system_settings_design_page"),
		"tutorial": getattr(main_ui, "_build_system_settings_tutorial_page"),
		"dev": getattr(main_ui, "_build_system_settings_dev_page"),
	}
	builder = builders.get(page_key)
	if callable(builder):
		builder(content)
		try:
			getattr(main_ui, "right_info_panel").append_content(f"\n[UI] 系统设置页面切换: {page_key}")
		except Exception:
			pass
		return
	getattr(main_ui, "_build_system_settings_general_page")(content)
