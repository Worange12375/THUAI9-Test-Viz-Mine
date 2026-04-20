"""属性设置窗口装配（Phase 3：MainUI 拆分进行中）。

本文件负责：
- 创建与打开“属性设置（Attribute Settings）”Toplevel 窗口。
- 管理窗口关闭逻辑（force init 模式下的拦截、资源清理）。

不负责：
- 各页面（棋子/地图/行动）具体内容的渲染与交互细节（仍在 MainUI 的 `_switch_attribute_settings_page` 等方法中）。

设计说明：
- 本阶段目标是“搬家不改逻辑”，因此这里接收 `main_ui` 实例并直接访问其字段/方法。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


def open_attribute_settings_window(main_ui: Any, *, force_runtime_init: bool = False) -> None:
	"""打开属性设置窗口。

	参数：
	- force_runtime_init: True 时进入“强制初始化”模式，要求用户完成必要配置才能关闭窗口。
	"""
	if force_runtime_init:
		main_ui.attribute_settings_force_init_mode = True
		main_ui.runtime_init_config_ready = False
	else:
		main_ui.attribute_settings_force_init_mode = False

	if hasattr(main_ui, "attribute_settings_window") and main_ui.attribute_settings_window is not None:
		try:
			if main_ui.attribute_settings_window.winfo_exists():
				main_ui.attribute_settings_window.deiconify()
				main_ui.attribute_settings_window.lift()
				main_ui.attribute_settings_window.focus_force()
				main_ui._switch_attribute_settings_page("piece")
				if force_runtime_init:
					main_ui.root.wait_window(main_ui.attribute_settings_window)
				return
		except Exception:
			pass

	window = tk.Toplevel(main_ui.root)
	window.title("属性设置")
	window.transient(main_ui.root)
	window.resizable(True, True)
	window.geometry("860x460")
	window.minsize(760, 380)
	main_ui.attribute_settings_window = window

	main = ttk.Frame(window, padding=10)
	main.pack(fill="both", expand=True)
	main.columnconfigure(0, weight=0)
	main.columnconfigure(1, weight=1)
	main.rowconfigure(0, weight=1)

	nav = ttk.LabelFrame(main, text="分类", padding=8)
	nav.grid(row=0, column=0, sticky="ns", padx=(0, 10))
	nav.columnconfigure(0, weight=1)

	content = ttk.LabelFrame(main, text="属性内容", padding=10)
	content.grid(row=0, column=1, sticky="nsew")
	content.columnconfigure(0, weight=1)
	content.rowconfigure(0, weight=1)
	main_ui.attribute_settings_content_frame = content

	main_ui.attribute_settings_nav_buttons = {}
	nav_items = [
		("piece", "棋子"),
		("map", "地图"),
		("action", "行动"),
	]
	for row_idx, (page_key, title) in enumerate(nav_items):
		btn = ttk.Button(nav, text=title, command=lambda key=page_key: main_ui._switch_attribute_settings_page(key))
		btn.grid(row=row_idx, column=0, sticky="ew", pady=(0, 8))
		main_ui.attribute_settings_nav_buttons[page_key] = btn
		if main_ui.attribute_settings_force_init_mode and page_key != "piece":
			btn.configure(state="disabled")

	def on_close() -> None:
		if main_ui.attribute_settings_force_init_mode and not main_ui.runtime_init_config_ready:
			msg = main_ui._runtime_init_incomplete_message()
			main_ui._show_notice_popup("提示", msg)
			main_ui._switch_attribute_settings_page("piece")
			return

		main_ui._stop_map_point_pick()
		main_ui.attribute_settings_force_init_mode = False
		main_ui.attribute_settings_window = None
		main_ui.attribute_settings_content_frame = None
		main_ui.attribute_piece_apply_status_label = None
		main_ui.attribute_piece_apply_status_job = None
		main_ui.attribute_piece_warning_label = None
		main_ui.attribute_piece_warning_job = None
		main_ui.attribute_map_apply_status_label = None
		window.destroy()

	window.protocol("WM_DELETE_WINDOW", on_close)
	main_ui._center_popup_window(window)
	main_ui._switch_attribute_settings_page("piece")
	if force_runtime_init:
		main_ui.root.wait_window(window)
