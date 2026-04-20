"""Popup/dialog services.

把 main_ui.py 里零散的弹窗逻辑集中在这里：
- 居中弹窗
- 简易确认框
- 只读提示弹窗
- 游戏结束重置确认
- 开局先攻详情

约束：不改变现有 UX/文案/交互，仅做代码搬家。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any


def center_popup_window(main_ui: object, window: tk.Toplevel) -> None:
	"""将弹窗居中到主窗口。"""
	try:
		root = getattr(main_ui, "root")
	except Exception:
		return

	window.update_idletasks()
	parent_x = root.winfo_rootx()
	parent_y = root.winfo_rooty()
	parent_w = root.winfo_width()
	parent_h = root.winfo_height()
	win_w = window.winfo_width()
	win_h = window.winfo_height()
	target_x = parent_x + max((parent_w - win_w) // 2, 0)
	target_y = parent_y + max((parent_h - win_h) // 2, 0)
	window.geometry(f"+{target_x}+{target_y}")


def show_confirm_dialog(
	main_ui: object,
	title: str,
	message: str,
	yes_text: str = "确定",
	no_text: str = "取消",
) -> bool:
	"""显示一个简单的“是/否”确认弹窗，返回是否选择 yes。"""
	choice: dict[str, bool] = {"value": False}
	root = getattr(main_ui, "root")
	window = tk.Toplevel(root)
	window.title(title)
	window.transient(root)
	window.resizable(False, False)
	window.grab_set()

	frame = ttk.Frame(window, padding=12)
	frame.pack(fill="both", expand=True)
	ttk.Label(frame, text=message, justify="left").pack(anchor="w")

	button_row = ttk.Frame(frame)
	button_row.pack(fill="x", pady=(10, 0))

	def on_yes() -> None:
		choice["value"] = True
		window.destroy()

	def on_no() -> None:
		choice["value"] = False
		window.destroy()

	ttk.Button(button_row, text=no_text, command=on_no).pack(side="right")
	ttk.Button(button_row, text=yes_text, command=on_yes).pack(side="right", padx=(0, 6))

	window.protocol("WM_DELETE_WINDOW", on_no)
	center_popup_window(main_ui, window)
	root.wait_window(window)
	return bool(choice["value"])


def show_notice_popup(main_ui: object, title: str, message: str, modal: bool = True) -> None:
	"""显示仅可关闭（右上角叉）的提示弹窗。"""
	root = getattr(main_ui, "root")
	window = tk.Toplevel(root)
	window.title(title)
	window.transient(root)
	window.resizable(False, False)
	if modal:
		window.grab_set()
	else:
		window.attributes("-topmost", True)
	frame = ttk.Frame(window, padding=12)
	frame.pack(fill="both", expand=True)
	ttk.Label(frame, text=message, justify="left").pack(anchor="w")
	window.protocol("WM_DELETE_WINDOW", window.destroy)
	center_popup_window(main_ui, window)
	if not modal:
		window.lift()


def show_game_over_reset_dialog(main_ui: object) -> None:
	"""游戏结束后弹窗确认：是否重置游戏。"""
	if bool(getattr(main_ui, "game_over_dialog_shown", False)):
		return
	setattr(main_ui, "game_over_dialog_shown", True)

	root = getattr(main_ui, "root")
	window = tk.Toplevel(root)
	window.title("游戏结束")
	window.transient(root)
	window.resizable(False, False)
	window.grab_set()

	frame = ttk.Frame(window, padding=12)
	frame.pack(fill="both", expand=True)
	ttk.Label(frame, text="是否重置游戏？", justify="left").pack(anchor="w")

	button_row = ttk.Frame(frame)
	button_row.pack(fill="x", pady=(10, 0))

	def _show_no_warning() -> None:
		show_notice_popup(
			main_ui,
			"提示",
			"目前在开发阶段，不重置可能存在bug，如想正常重开一局，请点击\"模式选择\"",
		)

	def on_yes() -> None:
		window.destroy()
		getattr(main_ui, "_on_click_reset")()

	def on_no_like_close() -> None:
		window.destroy()
		_show_no_warning()

	ttk.Button(button_row, text="否", command=on_no_like_close).pack(side="right")
	ttk.Button(button_row, text="是", command=on_yes).pack(side="right", padx=(0, 6))

	window.protocol("WM_DELETE_WINDOW", on_no_like_close)
	center_popup_window(main_ui, window)


def show_initiative_summary_popup(main_ui: object) -> None:
	"""显示开局先攻详情：属性值、随机值、总值、序号与最终顺序。"""
	env = getattr(getattr(main_ui, "controller"), "environment", None)
	if env is None:
		return

	details = list(getattr(main_ui, "runtime_initiative_snapshot", []))
	if not details:
		try:
			getattr(main_ui, "right_info_panel").append_content("\n[UI] 先攻详情不可用：未捕获到初始化掷骰信息")
		except Exception:
			pass
		return

	slot_by_piece: dict[int, str] = {}
	for slot in getattr(main_ui, "runtime_card_slots", []):
		piece = slot.get("piece")
		if piece is not None:
			slot_by_piece[id(piece)] = str(slot.get("slot_code", "?"))

	coerce_piece_list = getattr(main_ui, "_coerce_piece_list")
	action_queue = coerce_piece_list(getattr(env, "action_queue", []))
	order_by_piece: dict[int, int] = {}
	overall_codes: list[str] = []
	for idx, piece in enumerate(action_queue, start=1):
		if not bool(getattr(piece, "is_alive", True)):
			continue
		pid = id(piece)
		order_by_piece[pid] = idx
		overall_codes.append(slot_by_piece.get(pid, f"ID{int(getattr(piece, 'id', -1))}"))

	rows: list[tuple[int, str, int, int, int, int]] = []
	for item in details:
		piece = item.get("piece")
		if piece is None or not bool(getattr(piece, "is_alive", True)):
			continue
		pid = id(piece)
		seq = int(order_by_piece.get(pid, 999))
		code = slot_by_piece.get(pid, f"ID{int(getattr(piece, 'id', -1))}")
		attr_name = str(item.get("attr_name", "属性"))
		attr_value = int(item.get("attr_value", 0))
		roll_value = int(item.get("roll", 0))
		bonus_value = int(item.get("bonus", 0))
		total_value = int(item.get("total", roll_value + bonus_value))
		rows.append((seq, code, attr_name, attr_value, roll_value, bonus_value, total_value))

	rows.sort(key=lambda x: x[0])
	if not rows:
		return

	root = getattr(main_ui, "root")
	window = tk.Toplevel(root)
	window.title("开局先攻顺序信息")
	window.resizable(False, False)
	window.transient(root)
	window.attributes("-topmost", True)

	container = ttk.Frame(window, padding=12)
	container.pack(fill="both", expand=True)

	ttk.Label(container, text="先攻计算（按当前 env 实现）", font=("Microsoft YaHei UI", 11, "bold")).pack(anchor="w")
	text = tk.Text(container, width=76, height=12, wrap="none")
	text.pack(fill="both", expand=True, pady=(8, 8))
	text.insert("end", "序号  棋子  属性  属性值  随机(d20)  调整值  总值\n")
	text.insert("end", "------------------------------------------------\n")
	for seq, code, attr_name, attr_value, roll_value, bonus_value, total_value in rows:
		text.insert(
			"end",
			f"{seq:>2}    {code:<3}   {attr_name:<2}    {attr_value:>2}      {roll_value:>2}       {bonus_value:>2}    {total_value:>2}\n",
		)
	text.insert("end", "\n")
	text.insert("end", f"最终顺序：{' -> '.join(overall_codes)}")
	text.configure(state="disabled")

	button_row = ttk.Frame(container)
	button_row.pack(anchor="e")

	def _close() -> None:
		window.destroy()

	ttk.Button(button_row, text="确定", command=_close).pack(side="right")
	window.protocol("WM_DELETE_WINDOW", _close)
	window.grab_set()
	center_popup_window(main_ui, window)
	root.wait_window(window)
