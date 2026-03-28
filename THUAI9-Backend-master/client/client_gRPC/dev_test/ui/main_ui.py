"""主界面入口。

该文件只负责“界面装配”：
1. 创建主窗口
2. 按 2:1 划分左右区域
3. 调用 components.py 中的可复用组件完成基础布局
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from components import (
	ButtonPanel,
	ChessboardPanel,
	InfoPanel,
	PlayerSummaryCard,
	RightTopCompositePanel,
)


class MainUI:
	"""测试后端逻辑用的基础界面。

	当前阶段目标：
	- 完成窗口基础骨架
	- 预留左上信息展示区域
	- 预留右侧按键区与信息展示区
	"""

	def __init__(self, root: tk.Tk) -> None:
		self.root = root
		self.root.title("THUAI9 后端逻辑测试 UI")
		# 初始化状态基线：用于“初始化”按钮一键恢复。
		# 具体数值待定
		self.initial_player1_state = {
			"player_id": "P1",
			"position": "(3, 7)",
			"hp": "100",
			"power": "18",
			"agility": "12",
			"intelligence": "9",
			"weapon": "长枪",
			"armor": "轻甲",
		}
		# 具体数值待定
		self.initial_player2_state = {
			"player_id": "P2",
			"position": "(14, 11)",
			"hp": "95",
			"power": "14",
			"agility": "16",
			"intelligence": "11",
			"weapon": "弓",
			"armor": "中甲",
		}
		# 折中布局：适度增加默认宽度，给右侧信息区更多范围。
		# 同时配合最小尺寸约束，保证左侧棋盘在较小窗口下也能完整显示。
		self.root.geometry("1280x900")
		self.root.minsize(1200, 760)

		# 主容器填满整个窗口，并作为左右分栏的承载层。
		main_container = ttk.Frame(self.root, padding=12)
		main_container.pack(fill="both", expand=True)

		# 左右两列保持原有布局结构，仅做比例微调（由 5:3 调整为 5:4）。
		# 目的：给右侧新增复合区更多宽度，避免其内部内容拥挤。
		main_container.columnconfigure(0, weight=5)
		main_container.columnconfigure(1, weight=4)
		main_container.rowconfigure(0, weight=1)

		left_frame = ttk.Frame(main_container)
		right_frame = ttk.Frame(main_container)

		left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
		right_frame.grid(row=0, column=1, sticky="nsew")

		self._build_left_side(left_frame)
		self._build_right_side(right_frame)

	def _build_left_side(self, parent: ttk.Frame) -> None:
		"""构建左侧区域。

		左侧分为上下两块：
		- 上方：信息展示区域（已明确需求）
		- 下方：主内容预留区（后续可放棋盘/地图/时序面板）
		"""
		parent.columnconfigure(0, weight=1)
		parent.rowconfigure(0, weight=0)  # 顶部信息区固定预留高度
		parent.rowconfigure(1, weight=1)  # 下方主区域占据剩余空间

		# 左上信息区改为“左右等宽双栏”，用于分别展示 Player1 / Player2。
		# 区域内只常驻显示摘要字段（ID、棋子位置、HP）。
		# 详细属性通过“详细信息”按钮悬停弹窗展示。
		self.left_top_info = ttk.LabelFrame(parent, text="信息展示区", padding=8)
		self.left_top_info.configure(height=170)
		self.left_top_info.grid_propagate(False)
		self.left_top_info.grid(row=0, column=0, sticky="ew", pady=(0, 10))

		self.left_top_info.columnconfigure(0, weight=1)
		self.left_top_info.columnconfigure(1, weight=1)
		self.left_top_info.rowconfigure(0, weight=1)

		self.player1_card = PlayerSummaryCard(
			self.left_top_info,
			title="Player1",
			**self.initial_player1_state,
		)
		self.player1_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

		self.player2_card = PlayerSummaryCard(
			self.left_top_info,
			title="Player2",
			**self.initial_player2_state,
		)
		self.player2_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

		# 左下区域改为真实棋盘组件：20x20 正方形网格。
		# 棋盘绘制逻辑放在 components.py，主界面只负责装配与摆放。
		self.left_board_panel = ChessboardPanel(parent, title="棋盘区域（20 x 20）", grid_size=20)
		self.left_board_panel.grid(row=1, column=0, sticky="nsew")

	def _build_right_side(self, parent: ttk.Frame) -> None:
		"""构建右侧区域。

		右侧主要用于：
		- 新增上方复合区域
		- 操作按钮
		- 信息展示
		"""
		parent.columnconfigure(0, weight=1)
		parent.rowconfigure(0, weight=0)  # 新增上方区域
		parent.rowconfigure(1, weight=0)  # 操作区下移
		parent.rowconfigure(2, weight=1)  # 信息区吃满剩余空间（可被适当压缩）

		# 在操作区上方插入与操作区同量级高度的新区域。
		self.right_top_composite_panel = RightTopCompositePanel(
			parent,
			title="复合展示区",
			on_initialize=self._on_click_initialize,
		)
		self.right_top_composite_panel.configure(height=220)
		self.right_top_composite_panel.grid_propagate(False)
		self.right_top_composite_panel.grid(row=0, column=0, sticky="ew", pady=(0, 6))

		buttons = [
			("加载测试数据", self._on_click_load_data),
			("开始回放", self._on_click_start),
			("暂停", self._on_click_pause),
			("单步执行", self._on_click_step),
			("重置", self._on_click_reset),
		]
		self.right_button_panel = ButtonPanel(parent, title="操作区", buttons=buttons)
		self.right_button_panel.configure(height=220)
		self.right_button_panel.grid_propagate(False)
		self.right_button_panel.grid(row=1, column=0, sticky="ew", pady=(0, 6))

		# 右侧信息区保留在最下方，因新增区域和操作区下移，纵向空间会适度压缩。
		self.right_info_panel = InfoPanel(parent, title="右侧信息展示区", height=220)
		self.right_info_panel.grid(row=2, column=0, sticky="nsew")
		self.right_info_panel.set_content(
			"这里预留用于显示操作反馈、错误提示、关键变量与日志。\n"
			"按钮点击后会向此处追加示例文本，便于联调界面流程。"
		)

	# 以下按钮回调先提供最小可用行为，后续在 logic/controller.py 中接入真实逻辑。
	def _on_click_load_data(self) -> None:
		self.right_info_panel.append_content("\n[UI] 点击: 加载测试数据")

	def _on_click_start(self) -> None:
		self.right_info_panel.append_content("\n[UI] 点击: 开始回放")

	def _on_click_pause(self) -> None:
		self.right_info_panel.append_content("\n[UI] 点击: 暂停")

	def _on_click_step(self) -> None:
		self.right_info_panel.append_content("\n[UI] 点击: 单步执行")

	def _on_click_reset(self) -> None:
		self.right_info_panel.append_content("\n[UI] 点击: 重置")

	def _on_click_initialize(self) -> None:
		"""初始化流程框架。

		当前行为：
		1. 棋盘恢复初始网格状态
		2. Player1/Player2 属性回到初始值
		
		后续可在此接入：
		- 后端初始化接口调用
		- 本地缓存与回放状态清空
		"""
		self.left_board_panel.reset_board_state()
		self.player1_card.set_player_state(**self.initial_player1_state)
		self.player2_card.set_player_state(**self.initial_player2_state)

		self.right_info_panel.append_content("\n[UI] 点击: 初始化（棋盘与玩家状态已恢复）")


def launch() -> None:
	"""单独提供启动函数，便于 main.py 调用。"""
	root = tk.Tk()
	MainUI(root)
	root.mainloop()


if __name__ == "__main__":
	launch()