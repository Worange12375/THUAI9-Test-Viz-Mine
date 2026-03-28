"""可复用 UI 组件定义。

本文件只放可复用的界面组件，不放具体业务逻辑：
1. 信息展示框（标题 + 文本展示区）
2. 统一风格按钮区（纵向按钮列表）
3. 棋盘绘制组件（20x20 正方形网格）
4. 玩家信息卡片（摘要分块 + 悬停详情）
5. 右侧上方复合区域（几何分区示意）
"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from typing import Any, Sequence
from tkinter import ttk


class InfoPanel(ttk.LabelFrame):
	"""通用信息展示面板。

	该组件用于显示文本信息，例如：
	- 对局状态
	- 日志摘要
	- 回合信息
	- 调试提示

	参数说明：
	- parent: 父容器
	- title: 面板标题
	- height: 期望高度（像素），通过禁止自动收缩来保证预留区域可见
	"""

	def __init__(self, parent: tk.Misc, title: str, height: int = 180) -> None:
		super().__init__(parent, text=title, padding=10)

		# 固定预留高度，防止内容较少时区域被压缩到几乎不可见。
		self.configure(height=height)
		self.pack_propagate(False)

		# 文本框用于展示可滚动信息，默认只读。
		self.text = tk.Text(self, wrap="word", font=("Microsoft YaHei UI", 10), relief="flat")
		self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
		self.text.configure(yscrollcommand=self.scrollbar.set)

		self.text.pack(side="left", fill="both", expand=True)
		self.scrollbar.pack(side="right", fill="y")

		# 初始设置为只读，避免用户误编辑展示内容。
		self.set_readonly(True)

	def set_content(self, content: str) -> None:
		"""覆盖式写入内容，用于刷新展示文本。"""
		self.set_readonly(False)
		self.text.delete("1.0", "end")
		self.text.insert("1.0", content)
		self.set_readonly(True)

	def append_content(self, content: str) -> None:
		"""追加内容，用于持续输出日志或状态流。"""
		self.set_readonly(False)
		self.text.insert("end", content)
		self.text.see("end")
		self.set_readonly(True)

	def set_readonly(self, readonly: bool = True) -> None:
		"""切换文本框是否可编辑。"""
		self.text.configure(state="disabled" if readonly else "normal")


class ButtonPanel(ttk.LabelFrame):
	"""通用按钮面板。

	通过传入按钮配置列表快速生成统一风格的按钮区域，
	便于在主界面中复用并集中管理控件样式。
	"""

	def __init__(
		self,
		parent: tk.Misc,
		title: str,
		buttons: Sequence[tuple[str, Callable[[], None] | None]],
	) -> None:
		super().__init__(parent, text=title, padding=10)

		# 纵向布局按钮，每个按钮占满一行，保持视觉整齐。
		self.columnconfigure(0, weight=1)

		for row_idx, (label, command) in enumerate(buttons):
			# 当未提供回调时，使用空函数占位，避免类型与运行时报错。
			safe_command = command if command is not None else (lambda: None)
			btn = ttk.Button(self, text=label, command=safe_command)
			btn.grid(row=row_idx, column=0, sticky="ew", pady=(0, 8))


class HoverTip:
	"""悬停提示弹窗。

	用于在鼠标停留时弹出详细信息，鼠标移出后自动关闭。
	这里使用 Toplevel 而不是 Tooltip 库，避免额外依赖，便于后续项目内复用。
	"""

	def __init__(self, owner: tk.Widget, text: str) -> None:
		self.owner = owner
		self.text = text
		self.tip_window: tk.Toplevel | None = None
		self.pinned = False

	def show(self) -> None:
		"""显示提示框。"""
		if self.tip_window is not None:
			return

		x = self.owner.winfo_rootx() + 14
		y = self.owner.winfo_rooty() + self.owner.winfo_height() + 8

		self.tip_window = tk.Toplevel(self.owner)
		self.tip_window.wm_overrideredirect(True)
		self.tip_window.wm_geometry(f"+{x}+{y}")

		# 采用简洁高对比样式，保证提示内容可读。
		label = tk.Label(
			self.tip_window,
			text=self.text,
			justify="left",
			background="#fffbe6",
			relief="solid",
			borderwidth=1,
			padx=12,
			pady=10,
			font=("Microsoft YaHei UI", 10),
			wraplength=320,
		)
		label.pack()

	def hide(self) -> None:
		"""关闭提示框。"""
		# 已固定时不随鼠标移出而隐藏。
		if self.pinned:
			return

		if self.tip_window is None:
			return
		self.tip_window.destroy()
		self.tip_window = None

	def toggle_pin(self) -> None:
		"""切换固定状态。

		- 第一次点击：固定并显示详细信息
		- 第二次点击：取消固定并关闭详细信息
		"""
		if not self.pinned:
			self.pinned = True
			self.show()
			return

		self.pinned = False
		if self.tip_window is not None:
			self.tip_window.destroy()
			self.tip_window = None


class PlayerSummaryCard(ttk.LabelFrame):
	"""玩家摘要信息卡片。

	卡片内容分为两层：
	1. 常驻展示（分块展示）：ID、棋子位置、HP
	2. 悬停展示（详细信息）：力量、敏捷、智力、武器、防具
	"""

	def __init__(
		self,
		parent: tk.Misc,
		title: str,
		player_id: str,
		position: str,
		hp: str,
		power: str,
		agility: str,
		intelligence: str,
		weapon: str,
		armor: str,
	) -> None:
		super().__init__(parent, text=title, padding=6)
		self.title_name = title

		# 目标布局：
		# 1. 卡片先分左右两栏（1:1）
		# 2. 右栏再分上下（3:5）
		# 3. 右栏下半再分左右（1:1）
		self.columnconfigure(0, weight=1)
		self.rowconfigure(0, weight=1)

		root_layout = ttk.Frame(self)
		root_layout.grid(row=0, column=0, sticky="nsew")
		root_layout.columnconfigure(0, weight=1)
		root_layout.columnconfigure(1, weight=1)
		root_layout.rowconfigure(0, weight=1)

		# 左栏（完整一列）：放 ID 信息块。
		id_block, self.id_value_label = self._create_value_block(root_layout, "ID", player_id)
		id_block.grid(row=0, column=0, sticky="nsew", padx=(0, 4))

		# 右栏：上下 3:5。
		right_column = ttk.Frame(root_layout)
		right_column.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
		right_column.columnconfigure(0, weight=1)
		right_column.rowconfigure(0, weight=3)
		right_column.rowconfigure(1, weight=5)

		# 右栏上半：棋子位置。
		position_block, self.position_value_label = self._create_value_block(right_column, "棋子位置", position)
		position_block.grid(row=0, column=0, sticky="nsew", pady=(0, 4))

		# 右栏下半：再分左右 1:1。
		right_bottom = ttk.Frame(right_column)
		right_bottom.grid(row=1, column=0, sticky="nsew")
		right_bottom.columnconfigure(0, weight=1)
		right_bottom.columnconfigure(1, weight=1)
		right_bottom.rowconfigure(0, weight=1)

		# 右下区域左格：HP。
		hp_block, self.hp_value_label = self._create_value_block(right_bottom, "HP", hp)
		hp_block.grid(row=0, column=0, sticky="nsew", padx=(0, 3))

		# 右下区域右格：详细信息按钮，放在该格子的右下角。
		action_block = ttk.LabelFrame(right_bottom, text="操作", padding=(6, 3))
		action_block.grid(row=0, column=1, sticky="nsew", padx=(3, 0))
		action_block.columnconfigure(0, weight=1)
		action_block.rowconfigure(0, weight=1)

		detail_btn = ttk.Button(action_block, text="详细信息")
		detail_btn.grid(row=0, column=0, sticky="se")

		# 保存详细属性，初始化及后续更新会统一刷新悬停文案。
		self.power = power
		self.agility = agility
		self.intelligence = intelligence
		self.weapon = weapon
		self.armor = armor

		self._tip = HoverTip(detail_btn, "")
		self._refresh_detail_text()
		detail_btn.configure(command=self._tip.toggle_pin)
		detail_btn.bind("<Enter>", lambda _event: self._tip.show())
		detail_btn.bind("<Leave>", lambda _event: self._tip.hide())

	def _create_value_block(self, parent: ttk.Frame, title: str, value: str) -> tuple[ttk.LabelFrame, ttk.Label]:
		"""创建单个摘要信息块，并返回块与值标签引用（便于后续更新）。"""
		block = ttk.LabelFrame(parent, text=title, padding=(6, 3))
		value_label = ttk.Label(block, text=value, anchor="center", justify="center")
		value_label.pack(fill="both", expand=True)
		return block, value_label

	def _refresh_detail_text(self) -> None:
		"""根据当前字段刷新悬停详情文本。"""
		self._tip.text = (
			f"Player: {self.title_name}\n"
			f"ID: {self.id_value_label.cget('text')}\n"
			f"棋子位置: {self.position_value_label.cget('text')}\n"
			f"HP: {self.hp_value_label.cget('text')}\n"
			f"力量: {self.power}\n"
			f"敏捷: {self.agility}\n"
			f"智力: {self.intelligence}\n"
			f"武器: {self.weapon}\n"
			f"防具: {self.armor}"
		)

	def set_player_state(
		self,
		*,
		player_id: str,
		position: str,
		hp: str,
		power: str,
		agility: str,
		intelligence: str,
		weapon: str,
		armor: str,
	) -> None:
		"""更新玩家卡片状态。

		用于接收初始化/回放等流程传入的新状态并刷新：
		- 左上摘要字段
		- 悬停详细字段
		"""
		self.id_value_label.configure(text=player_id)
		self.position_value_label.configure(text=position)
		self.hp_value_label.configure(text=hp)
		self.power = power
		self.agility = agility
		self.intelligence = intelligence
		self.weapon = weapon
		self.armor = armor
		self._refresh_detail_text()


class RightTopCompositePanel(ttk.LabelFrame):
	"""右侧上方复合区域。

	结构要求：
	1. 整体分左右两列
	2. 左列为正方形占位区域（不绘制图形）
	3. 右列分上下两部分
	4. 右列下半再均分为左右两块

	本组件额外提供：
	- 左侧正方形区内的“初始化”按钮
	- 默认空实现初始化函数，后续可接入真实初始化流程
	"""

	def __init__(
		self,
		parent: tk.Misc,
		title: str = "状态区",
		on_initialize: Callable[[], None] | None = None,
	) -> None:
		super().__init__(parent, text=title, padding=8)
		self.on_initialize = on_initialize

		# 第一层：左右两列，左列占较小比例，右列占较大比例，具体比例为 5:8。
		self.columnconfigure(0, weight=5)
		self.columnconfigure(1, weight=8)
		self.rowconfigure(0, weight=1)

		# 左列：保持正方形“占位”，不绘制几何图案。
		left_block = ttk.LabelFrame(self, text="左侧正方形区", padding=6)
		left_block.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
		left_block.columnconfigure(0, weight=1)
		left_block.rowconfigure(0, weight=1)

		self.square_placeholder = ttk.Frame(left_block)
		# 使用 place 在容器中居中放置正方形占位块，确保“形状”由布局控制。
		self.square_placeholder.place(x=0, y=0, width=1, height=1)
		left_block.bind("<Configure>", self._layout_square_placeholder)

		# 在正方形占位区中放置“初始化”按钮，按钮大小随占位区自适应填充。
		# 通过 command 绑定初始化函数，当前为占位空实现，后续可直接补全逻辑。
		self.init_button = ttk.Button(self.square_placeholder, text="初始化", command=self._initialize)
		self.init_button.pack(fill="both", expand=True)

		# 右列：先上下两块（默认等分，后续如需比例可直接改 rowconfigure 权重）。
		right_col = ttk.Frame(self)
		right_col.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
		right_col.columnconfigure(0, weight=1)
		right_col.rowconfigure(0, weight=1)
		right_col.rowconfigure(1, weight=1)

		right_top = ttk.LabelFrame(right_col, text="右上区", padding=6)
		right_top.grid(row=0, column=0, sticky="nsew", pady=(0, 4))
		ttk.Label(right_top, text="THU AI", anchor="center").pack(fill="both", expand=True)

		right_bottom = ttk.Frame(right_col)
		right_bottom.grid(row=1, column=0, sticky="nsew")
		right_bottom.columnconfigure(0, weight=1)
		right_bottom.columnconfigure(1, weight=1)
		right_bottom.rowconfigure(0, weight=1)

		right_bottom_left = ttk.LabelFrame(right_bottom, text="右下左区", padding=6)
		right_bottom_left.grid(row=0, column=0, sticky="nsew", padx=(0, 2))
		ttk.Label(right_bottom_left, text="可放统计 A", anchor="center").pack(fill="both", expand=True)

		right_bottom_right = ttk.LabelFrame(right_bottom, text="右下右区", padding=6)
		right_bottom_right.grid(row=0, column=1, sticky="nsew", padx=(2, 0))
		ttk.Label(right_bottom_right, text="可放统计 B", anchor="center").pack(fill="both", expand=True)

	def _layout_square_placeholder(self, event: tk.Event) -> None:
		"""根据左列可用尺寸，居中布局正方形占位块。"""
		width = event.width
		height = event.height
		if width <= 2 or height <= 2:
			return

		# 留出内边距，避免占位块过大贴边，同时保留按钮可读性。
		max_square = min(width, height) - 12
		size = max(max_square, 1)
		x = (width - size) // 2
		y = (height - size) // 2

		self.square_placeholder.place(x=x, y=y, width=size, height=size)

	def _initialize(self) -> None:
		"""初始化按钮回调。

		若外部提供 on_initialize 回调，则调用外部初始化流程。
		否则回退到本地空实现，避免按钮点击报错。
		"""
		if self.on_initialize is not None:
			self.on_initialize()
			return

		# 具体数值待定：此处仅保留兜底占位行为。
		pass


class ChessboardPanel(ttk.LabelFrame):
	"""20x20 棋盘绘制组件。

	设计目标：
	- 固定逻辑网格为 20 列 x 20 行
	- 绘制区域始终保持“正方形”
	- 当父容器尺寸变化时自动重绘，保证棋盘清晰且居中
	"""

	def __init__(self, parent: tk.Misc, title: str = "棋盘区域", grid_size: int = 20) -> None:
		super().__init__(parent, text=title, padding=10)

		# grid_size 表示棋盘边长格数，当前需求为 20。
		# 注意：不能命名为 grid_size，该名字与 Tk 内置方法同名。
		self.board_grid_size = grid_size

		# 使用 Canvas 承担图形绘制工作，背景设为浅色便于观察网格线。
		self.canvas = tk.Canvas(self, background="#f9f9f9", highlightthickness=0)
		self.canvas.pack(fill="both", expand=True)

		# 记录当前棋盘的绘制参数，后续若要绘制棋子可直接复用。
		self.board_origin_x = 0
		self.board_origin_y = 0
		self.board_pixel_size = 0
		self.cell_size = 0.0
		self.map_rows: list[list[int]] = []
		self.pieces: list[dict[str, Any]] = []

		# 监听尺寸变化：窗口拉伸时自动重绘，保持棋盘为正方形。
		self.canvas.bind("<Configure>", self._on_canvas_resize)

	def set_board_state(self, map_rows: list[list[int]] | None, pieces: list[dict[str, Any]] | None) -> None:
		"""设置地图与棋子状态并触发重绘。"""
		self.map_rows = map_rows if isinstance(map_rows, list) else []
		self.pieces = pieces if isinstance(pieces, list) else []
		self._draw_board(self.canvas.winfo_width(), self.canvas.winfo_height())

	def _on_canvas_resize(self, event: tk.Event) -> None:
		"""Canvas 尺寸变化时触发重绘。"""
		self._draw_board(event.width, event.height)

	def _draw_board(self, canvas_width: int, canvas_height: int) -> None:
		"""绘制 20x20 正方形棋盘。

		关键计算：
		- board_pixel_size = min(canvas_width, canvas_height)
		  取最小边长，确保棋盘不会超出可用区域。
		- board_origin_x / board_origin_y
		  用于将棋盘在 Canvas 中居中显示。
		"""
		self.canvas.delete("all")

		if canvas_width <= 2 or canvas_height <= 2:
			return

		# 预留少量内边距，避免边框贴边导致视觉拥挤。
		padding = 8
		usable_width = max(canvas_width - 2 * padding, 1)
		usable_height = max(canvas_height - 2 * padding, 1)

		self.board_pixel_size = min(usable_width, usable_height)
		self.board_origin_x = (canvas_width - self.board_pixel_size) // 2
		self.board_origin_y = (canvas_height - self.board_pixel_size) // 2
		self.cell_size = self.board_pixel_size / self.board_grid_size

		x0 = self.board_origin_x
		y0 = self.board_origin_y
		x1 = x0 + self.board_pixel_size
		y1 = y0 + self.board_pixel_size

		# 先画 20x20 格子底色。
		for row in range(self.board_grid_size):
			for col in range(self.board_grid_size):
				cell_value = self._get_map_value(col, row)
				fill_color = "#B7E4C7" if cell_value == 1 else "#5B3A29"
				cx0 = x0 + col * self.cell_size
				cy0 = y0 + row * self.cell_size
				cx1 = cx0 + self.cell_size
				cy1 = cy0 + self.cell_size
				self.canvas.create_rectangle(cx0, cy0, cx1, cy1, fill=fill_color, outline="")

		# 先画棋盘外框，线条稍粗，便于与内部网格区分。
		self.canvas.create_rectangle(x0, y0, x1, y1, outline="#1f2937", width=2)

		# 逐条绘制内部网格线：
		# board_grid_size=20 时，需要 19 条内部竖线 + 19 条内部横线。
		for i in range(1, self.board_grid_size):
			line_offset = i * self.cell_size

			# 竖线
			vx = x0 + line_offset
			self.canvas.create_line(vx, y0, vx, y1, fill="#9ca3af", width=1)

			# 横线
			hy = y0 + line_offset
			self.canvas.create_line(x0, hy, x1, hy, fill="#9ca3af", width=1)

		self._draw_pieces()

	def _get_map_value(self, x: int, y: int) -> int:
		"""获取地图格值。越界或缺失时按不可行处理。"""
		if y < 0 or y >= len(self.map_rows):
			return 0
		row = self.map_rows[y]
		if not isinstance(row, list) or x < 0 or x >= len(row):
			return 0
		value = row[x]
		return value if isinstance(value, int) else 0

	def _draw_pieces(self) -> None:
		"""在对应格子绘制棋子与白字标注。"""
		if self.cell_size <= 0:
			return

		for piece in self.pieces:
			x = piece.get("x")
			y = piece.get("y")
			team = piece.get("team")
			label = piece.get("label")
			if not isinstance(x, int) or not isinstance(y, int):
				continue
			if x < 0 or y < 0 or x >= self.board_grid_size or y >= self.board_grid_size:
				continue

			cx0 = self.board_origin_x + x * self.cell_size
			cy0 = self.board_origin_y + y * self.cell_size
			cx1 = cx0 + self.cell_size
			cy1 = cy0 + self.cell_size
			piece_color = "#D62828" if team == 1 else "#1D4ED8"

			pad = self.cell_size * 0.12
			self.canvas.create_rectangle(
				cx0 + pad,
				cy0 + pad,
				cx1 - pad,
				cy1 - pad,
				fill=piece_color,
				outline="#111827",
				width=1,
			)

			if isinstance(label, str) and label:
				font_size = max(7, int(self.cell_size * 0.22))
				self.canvas.create_text(
					(cx0 + cx1) / 2,
					(cy0 + cy1) / 2,
					text=label,
					fill="#FFFFFF",
					font=("Microsoft YaHei UI", font_size, "bold"),
					justify="center",
				)

	def reset_board_state(self) -> None:
		"""重置棋盘到初始状态。

		当前版本的棋盘仅包含网格，因此重置逻辑为“清空并重绘网格”。
		后续若加入棋子/障碍绘制，可在这里统一清理并恢复初始局面。
		"""
		self.map_rows = []
		self.pieces = []
		self._draw_board(self.canvas.winfo_width(), self.canvas.winfo_height())