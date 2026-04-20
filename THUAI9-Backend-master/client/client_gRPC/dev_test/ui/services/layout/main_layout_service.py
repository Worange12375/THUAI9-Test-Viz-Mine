"""主窗口布局装配（从 MainUI 拆分）。

本文件负责：
- 装配 MainUI 的左侧区域（顶部 6 卡 + 底部棋盘）。
- 装配 MainUI 的右侧区域（复合展示区 + 操作按钮 + 信息展示）。

不负责：
- 业务逻辑与状态更新（仍由各 domain service / MainUI 薄委托协调）。

设计说明：
- 为保持行为不变，本 service 直接接收 `main_ui` 实例并写入其字段。
"""

from __future__ import annotations

from typing import Any

from tkinter import ttk

from components import (
	ButtonPanel,
	ChessboardPanel,
	InfoPanel,
	PieceSquareCard,
	RightTopCompositePanel,
)


def build_left_side(main_ui: Any, parent: ttk.Frame) -> None:
	"""构建左侧区域（6 卡 + 棋盘）。"""
	parent.columnconfigure(0, weight=1)
	parent.rowconfigure(0, weight=0)  # 顶部信息区固定预留高度
	parent.rowconfigure(1, weight=1)  # 下方主区域占据剩余空间

	# 左上信息区：6 个等尺寸卡片，保持区域总体宽高不变。
	main_ui.left_top_info = ttk.LabelFrame(parent, text="信息展示区", padding=8)
	main_ui.left_top_info.configure(height=180)
	main_ui.left_top_info.configure(width=620)
	main_ui.left_top_info.grid_propagate(False)
	main_ui.left_top_info.grid(row=0, column=0, sticky="ew", pady=(0, 10))

	square_row = ttk.Frame(main_ui.left_top_info)
	square_row.pack(fill="both", expand=True)

	# 六卡等权横向排列。
	for idx in range(6):
		square_row.columnconfigure(idx, weight=1, uniform="piece_col")
	square_row.rowconfigure(0, weight=1)
	card_height = 128

	main_ui.piece_cards = []
	for idx in range(6):
		card = PieceSquareCard(
			square_row,
			width=96,
			height=card_height,
			is_large=True,
		)
		pad_left = 0 if idx == 0 else 3
		pad_right = 0 if idx == 5 else 3
		card.grid(row=0, column=idx, sticky="sew", padx=(pad_left, pad_right), pady=(0, 0))
		main_ui.piece_cards.append(card)

	main_ui._refresh_piece_cards()

	# 左下区域改为真实棋盘组件：20x20 正方形网格。
	# 棋盘绘制逻辑放在 components.py，主界面只负责装配与摆放。
	main_ui.left_board_panel = ChessboardPanel(parent, title="棋盘区域（20 x 20）", grid_size=20)
	main_ui.left_board_panel.configure(width=620)
	main_ui.left_board_panel.grid(row=1, column=0, sticky="nsew")


def build_right_side(main_ui: Any, parent: ttk.Frame) -> None:
	"""构建右侧区域（复合区 + 按钮区 + 信息区）。"""
	parent.columnconfigure(0, weight=1)
	parent.rowconfigure(0, weight=0)  # 新增上方区域
	parent.rowconfigure(1, weight=0)  # 操作区下移
	parent.rowconfigure(2, weight=1)  # 信息区吃满剩余空间（可被适当压缩）

	# 在操作区上方插入与操作区同量级高度的新区域。
	main_ui.right_top_composite_panel = RightTopCompositePanel(
		parent,
		title="复合展示区",
		on_initialize=main_ui._on_right_composite_panel_initialize,
	)
	main_ui.right_top_composite_panel.configure(height=320)
	main_ui.right_top_composite_panel.grid_propagate(False)
	main_ui.right_top_composite_panel.grid(row=0, column=0, sticky="ew", pady=(0, 6))

	buttons = [
		("模式选择", main_ui._on_click_mode_selection),
		("回放模式", main_ui._on_click_replay_mode),
		("棋子行动", main_ui._on_click_piece_action),
		("属性设置", main_ui._on_click_attribute_settings),
		("系统设置", main_ui._on_click_system_settings),
		("退出测试", main_ui._on_click_exit),
	]
	main_ui.right_button_panel = ButtonPanel(parent, title="操作区", buttons=buttons)
	main_ui.right_button_panel.configure(height=250)
	main_ui.right_button_panel.grid_propagate(False)
	main_ui.right_button_panel.grid(row=1, column=0, sticky="ew", pady=(0, 6))

	# 右侧信息区保留在最下方，因新增区域和操作区下移，纵向空间会适度压缩。
	main_ui.right_info_panel = InfoPanel(parent, title="右侧信息展示区", height=150)
	main_ui.right_info_panel.grid(row=2, column=0, sticky="nsew")
	main_ui.right_info_panel.set_content(
		"这里预留用于显示操作反馈、错误提示、关键变量与日志。\n"
		"按钮点击后会向此处追加示例文本，便于联调界面流程。"
	)


def on_right_composite_panel_initialize(main_ui: Any) -> None:
	"""右侧复合展示区的初始化回调（当前仅输出日志，占位）。"""
	main_ui.right_info_panel.append_content("\n[UI] 复合展示区已初始化")
