"""属性设置窗口：地图属性页（map）。

本文件负责：
- 地图属性页 UI 构建（高度编辑、地图选点）。
- 选点覆盖层与非法点击引导弹窗。
- 高度颜色预览与写入（runtime_env / mock 两种数据源）。

阶段说明：
- Phase 3：MainUI 拆分进行中；以“搬家不改逻辑”为原则，接收 `main_ui` 实例并直接访问其字段/方法。
"""

from __future__ import annotations

from typing import Any

import tkinter as tk
from tkinter import ttk


def is_map_edit_available(main_ui: Any) -> bool:
	if main_ui.controller.runtime_source == "runtime_env":
		return main_ui.controller.environment is not None
	game_data = main_ui.controller.game_data
	if not isinstance(game_data, dict):
		return False
	board = game_data.get("map", {})
	rows = board.get("rows", []) if isinstance(board, dict) else []
	return isinstance(rows, list) and len(rows) > 0


def get_current_map_height(main_ui: Any, x: int, y: int) -> int | None:
	if main_ui.controller.runtime_source == "runtime_env":
		env = main_ui.controller.environment
		if env is None or getattr(env, "board", None) is None:
			return None
		board = env.board
		width = int(getattr(board, "width", 0))
		height = int(getattr(board, "height", 0))
		if not (0 <= x < width and 0 <= y < height):
			return None
		height_map = getattr(board, "height_map", None)
		if height_map is None:
			return None
		try:
			return int(height_map[x][y])
		except Exception:
			return None

	rows = main_ui._extract_mock_visual_rows()
	if y < 0 or y >= len(rows):
		return None
	row = rows[y]
	if x < 0 or x >= len(row):
		return None
	return int(row[x])


def show_map_apply_feedback(main_ui: Any, message: str) -> None:
	label = main_ui.attribute_map_apply_status_label
	if label is None:
		return
	label.configure(text=message, foreground="#059669")


def map_height_to_color(_main_ui: Any, height_value: int) -> str:
	if height_value == -1:
		return "#6B7280"
	if height_value == 0:
		return "#B7E4C7"
	if height_value == 1:
		return "#B08968"
	if height_value == 2:
		return "#5B3A29"
	return "#6b7280"


def update_map_height_preview(main_ui: Any) -> None:
	canvas = main_ui.attribute_map_height_color_canvas
	if canvas is None or not canvas.winfo_exists():
		return
	height_value = main_ui._safe_int(main_ui.attribute_map_height_var.get(), 0)
	fill = map_height_to_color(main_ui, height_value)
	canvas.delete("all")
	canvas.create_rectangle(2, 2, 20, 20, fill=fill, outline="#374151", width=1)


def apply_map_height_change(main_ui: Any) -> None:
	if not is_map_edit_available(main_ui):
		main_ui._show_notice_popup("提示", "当前数据源不支持地图高度编辑")
		return
	x = main_ui._safe_int(main_ui.attribute_map_x_var.get(), -1)
	y = main_ui._safe_int(main_ui.attribute_map_y_var.get(), -1)
	h = main_ui._safe_int(main_ui.attribute_map_height_var.get(), -999)
	if x < 0 or y < 0:
		main_ui._show_notice_popup("提示", "请先输入合法坐标 (X,Y)")
		return
	if h not in (-1, 0, 1, 2):
		main_ui._show_notice_popup("提示", "高度仅支持 -1/0/1/2（-1=不可行，0=地面，1/2=高地）")
		return

	if main_ui.controller.runtime_source == "runtime_env":
		env = main_ui.controller.environment
		board = env.board if env is not None else None
		if board is None:
			main_ui._show_notice_popup("提示", "地图未初始化，无法应用高度")
			return
		width = int(getattr(board, "width", 0))
		height = int(getattr(board, "height", 0))
		if not (0 <= x < width and 0 <= y < height):
			main_ui._show_notice_popup("提示", "坐标越界，请修改后重试")
			return
		try:
			board.height_map[x][y] = int(h)
		except Exception as e:
			main_ui._show_notice_popup("提示", f"高度写入失败: {e}")
			return
	else:
		rows = main_ui._extract_mock_visual_rows()
		if y < 0 or y >= len(rows) or x < 0 or x >= len(rows[y]):
			main_ui._show_notice_popup("提示", "坐标越界，请修改后重试")
			return
		main_ui.mock_map_height_overrides[(x, y)] = int(h)

	show_map_apply_feedback(main_ui, "应用成功")
	main_ui.right_info_panel.append_content(f"\n[UI] 地图高度已更新: ({x}, {y}) -> {h}")
	main_ui._refresh_board_view()


def stop_map_point_pick(main_ui: Any) -> None:
	main_ui.attribute_map_pick_waiting = False
	overlay = main_ui.attribute_map_pick_overlay
	main_ui.attribute_map_pick_overlay = None
	if overlay is not None and overlay.winfo_exists():
		overlay.destroy()
	popup = main_ui.attribute_map_pick_invalid_popup
	main_ui.attribute_map_pick_invalid_popup = None
	if popup is not None and popup.winfo_exists():
		popup.destroy()


def restore_map_attribute_page_after_pick(main_ui: Any) -> None:
	"""结束选点并回到地图属性页，不修改本次坐标。"""
	stop_map_point_pick(main_ui)
	if main_ui.attribute_settings_window is not None and main_ui.attribute_settings_window.winfo_exists():
		main_ui.attribute_settings_window.deiconify()
		main_ui.attribute_settings_window.lift()
		main_ui.attribute_settings_window.focus_force()
		main_ui._switch_attribute_settings_page("map")


def show_map_pick_invalid_popup(main_ui: Any) -> None:
	"""地图选点时点击非法区域后的引导弹窗。"""
	existing = main_ui.attribute_map_pick_invalid_popup
	if existing is not None and existing.winfo_exists():
		existing.lift()
		return

	window = tk.Toplevel(main_ui.root)
	window.title("提示")
	window.transient(main_ui.root)
	window.resizable(False, False)
	window.attributes("-topmost", True)
	main_ui.attribute_map_pick_invalid_popup = window

	frame = ttk.Frame(window, padding=12)
	frame.pack(fill="both", expand=True)
	ttk.Label(frame, text="请选择合法位置", justify="left").pack(anchor="w")

	button_row = ttk.Frame(frame)
	button_row.pack(anchor="e", pady=(10, 0))

	def _resume_pick_overlay() -> None:
		"""继续选点时恢复覆盖层焦点，避免点击穿透。"""
		main_ui.attribute_map_pick_waiting = True
		overlay = main_ui.attribute_map_pick_overlay
		if overlay is None or not overlay.winfo_exists():
			begin_map_point_pick(main_ui)
			return
		overlay.attributes("-topmost", True)
		overlay.lift(main_ui.root)
		main_ui.right_info_panel.append_content("\n[UI] 继续地图选点：请点击棋盘中的一个格子")

	def on_continue_pick() -> None:
		if main_ui.attribute_map_pick_invalid_popup is not None:
			main_ui.attribute_map_pick_invalid_popup = None
		window.destroy()
		_resume_pick_overlay()

	def on_exit_pick() -> None:
		if main_ui.attribute_map_pick_invalid_popup is not None:
			main_ui.attribute_map_pick_invalid_popup = None
		window.destroy()
		restore_map_attribute_page_after_pick(main_ui)
		main_ui.right_info_panel.append_content("\n[UI] 已退出地图选点，返回地图属性页")

	ttk.Button(button_row, text="继续选点", command=on_continue_pick).pack(side="left")
	ttk.Button(button_row, text="退出选点", command=on_exit_pick).pack(side="left", padx=(8, 0))
	window.protocol("WM_DELETE_WINDOW", on_exit_pick)

	main_ui._center_popup_window(window)
	window.lift()


def on_map_pick_overlay_click(main_ui: Any, event: Any) -> str:
	if not main_ui.attribute_map_pick_waiting:
		return "break"
	board_x, board_y = main_ui.left_board_panel.get_board_xy_from_root(int(event.x_root), int(event.y_root))
	if board_x is None or board_y is None:
		show_map_pick_invalid_popup(main_ui)
		return "break"

	h = get_current_map_height(main_ui, board_x, board_y)
	main_ui.attribute_map_x_var.set(str(board_x))
	main_ui.attribute_map_y_var.set(str(board_y))
	main_ui.attribute_map_height_var.set(str(h if h is not None else 0))
	stop_map_point_pick(main_ui)
	if main_ui.attribute_settings_window is not None and main_ui.attribute_settings_window.winfo_exists():
		main_ui.attribute_settings_window.deiconify()
		main_ui.attribute_settings_window.lift()
		main_ui.attribute_settings_window.focus_force()
		main_ui._switch_attribute_settings_page("map")
	show_map_apply_feedback(main_ui, f"已选定坐标 ({board_x}, {board_y})")
	main_ui.right_info_panel.append_content(f"\n[UI] 已选定地图坐标: ({board_x}, {board_y})")
	return "break"


def begin_map_point_pick(main_ui: Any) -> None:
	if not is_map_edit_available(main_ui):
		main_ui._show_notice_popup("提示", "当前数据源不支持地图选点")
		return
	stop_map_point_pick(main_ui)
	main_ui.attribute_map_pick_waiting = True
	if main_ui.attribute_settings_window is not None and main_ui.attribute_settings_window.winfo_exists():
		main_ui.attribute_settings_window.withdraw()

	overlay = tk.Toplevel(main_ui.root)
	overlay.overrideredirect(True)
	overlay.attributes("-alpha", 0.01)
	overlay.attributes("-topmost", True)
	overlay.lift(main_ui.root)
	overlay.geometry(
		f"{main_ui.root.winfo_width()}x{main_ui.root.winfo_height()}+{main_ui.root.winfo_rootx()}+{main_ui.root.winfo_rooty()}"
	)
	overlay.bind("<Button-1>", lambda e: on_map_pick_overlay_click(main_ui, e))
	overlay.bind("<ButtonRelease-1>", lambda _e: "break")
	main_ui.attribute_map_pick_overlay = overlay
	main_ui.right_info_panel.append_content("\n[UI] 地图选点模式：请点击棋盘中的一个格子")


def build_attribute_map_page(main_ui: Any, content: ttk.LabelFrame) -> None:
	wrapper = ttk.Frame(content)
	wrapper.grid(row=0, column=0, sticky="nsew")
	wrapper.columnconfigure(0, weight=1)
	wrapper.rowconfigure(4, weight=1)

	ttk.Label(wrapper, text="地图属性", font=("Microsoft YaHei UI", 12, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)

	note_text = "高度说明：-1=不可行，0=地面，1=黄棕高地，2=深棕高地"
	ttk.Label(wrapper, text=note_text, foreground="#4b5563").grid(row=1, column=0, sticky="w", pady=(0, 8))

	form = ttk.Frame(wrapper)
	form.grid(row=2, column=0, sticky="w")

	ttk.Label(form, text="将（").grid(row=0, column=0, sticky="w")
	tk.Entry(form, textvariable=main_ui.attribute_map_x_var, width=4).grid(row=0, column=1, sticky="w")
	ttk.Label(form, text="，").grid(row=0, column=2, sticky="w")
	tk.Entry(form, textvariable=main_ui.attribute_map_y_var, width=4).grid(row=0, column=3, sticky="w")
	ttk.Label(form, text="）处的高度更改为").grid(row=0, column=4, sticky="w")
	tk.Entry(form, textvariable=main_ui.attribute_map_height_var, width=4).grid(row=0, column=5, sticky="w")
	main_ui.attribute_map_height_color_canvas = tk.Canvas(form, width=22, height=22, highlightthickness=0, bg="#f8fafc")
	main_ui.attribute_map_height_color_canvas.grid(row=0, column=6, sticky="w", padx=(8, 0))
	update_map_height_preview(main_ui)

	btn_row = ttk.Frame(wrapper)
	btn_row.grid(row=3, column=0, sticky="w", pady=(10, 0))
	ttk.Button(btn_row, text="地图选点", command=lambda: begin_map_point_pick(main_ui)).pack(side="left")
	ttk.Button(btn_row, text="应用高度", command=lambda: apply_map_height_change(main_ui)).pack(side="left", padx=(8, 0))
	main_ui.attribute_map_apply_status_label = ttk.Label(btn_row, text="", foreground="#059669")
	main_ui.attribute_map_apply_status_label.pack(side="left", padx=(10, 0))

	if not is_map_edit_available(main_ui):
		ttk.Label(
			wrapper,
			text="当前数据源不支持高度编辑。",
			foreground="#b45309",
		).grid(row=4, column=0, sticky="w", pady=(8, 0))
