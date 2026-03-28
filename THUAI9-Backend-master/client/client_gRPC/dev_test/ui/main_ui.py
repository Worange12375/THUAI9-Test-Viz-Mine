"""主界面入口。

该文件只负责“界面装配”：
1. 创建主窗口
2. 按 2:1 划分左右区域
3. 调用 components.py 中的可复用组件完成基础布局
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any, Optional

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from env import ActionSet, PieceArg, Point
from logic.controller import Controller
from core.events import EventType

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

		self.controller = Controller(mode="manual")
		self.loaded = False
		self.running = False
		self.loop_job: Optional[str] = None
		self.selected_source = "runtime"
		self.selected_mock_dataset: Optional[str] = None
		self.mock_initial_positions: dict[int, dict[str, Any]] = {}
		self.mock_last_health_by_id: dict[int, int] = {}
		self.mock_last_positions_by_id: dict[int, tuple[int, int]] = {}
		self.mock_piece_number_by_id: dict[int, int] = {}

		self.controller.event_bus.subscribe(EventType.GAME_LOADED, self._on_event_game_loaded)
		self.controller.event_bus.subscribe(EventType.ROUND_STARTED, self._on_event_round_started)
		self.controller.event_bus.subscribe(EventType.ROUND_FINISHED, self._on_event_round_finished)
		self.controller.event_bus.subscribe(EventType.GAME_OVER, self._on_event_game_over)

		self._build_left_side(left_frame)
		self._build_right_side(right_frame)
		self.root.after(100, self._startup_load_with_source_dialog)

	def _show_source_selection_dialog(self, title: str = "选择数据源") -> Optional[str]:
		"""弹窗选择数据源：后端玩法环境或 mock 回放。"""
		choice = {"value": None}
		# 这里是新增的独立弹窗逻辑：用 Toplevel 创建一个模式对话框。
		window = tk.Toplevel(self.root)
		window.title(title)
		window.transient(self.root)
		window.grab_set()
		window.resizable(False, False)

		frame = ttk.Frame(window, padding=12)
		frame.pack(fill="both", expand=True)

		ttk.Label(frame, text="请选择本次测试的数据源：").pack(anchor="w", pady=(0, 8))
		var = tk.StringVar(value=self.selected_source)

		ttk.Radiobutton(frame, text="后端玩法环境（推荐）", value="runtime", variable=var).pack(anchor="w")
		ttk.Radiobutton(frame, text="mock 回放数据", value="mock", variable=var).pack(anchor="w", pady=(0, 8))

		button_row = ttk.Frame(frame)
		button_row.pack(fill="x", pady=(8, 0))

		def on_ok() -> None:
			choice["value"] = var.get()
			window.destroy()

		def on_cancel() -> None:
			choice["value"] = None
			window.destroy()

		ttk.Button(button_row, text="取消", command=on_cancel).pack(side="right")
		ttk.Button(button_row, text="确定", command=on_ok).pack(side="right", padx=(0, 6))

		# 将弹窗定位到主窗口中央，避免首次弹出时偏到屏幕角落。
		window.update_idletasks()
		parent_x = self.root.winfo_rootx()
		parent_y = self.root.winfo_rooty()
		parent_w = self.root.winfo_width()
		parent_h = self.root.winfo_height()
		win_w = window.winfo_width()
		win_h = window.winfo_height()
		target_x = parent_x + max((parent_w - win_w) // 2, 0)
		target_y = parent_y + max((parent_h - win_h) // 2, 0)
		window.geometry(f"+{target_x}+{target_y}")

		window.protocol("WM_DELETE_WINDOW", on_cancel)
		self.root.wait_window(window)
		return choice["value"]

	def _show_mock_dataset_dialog(self, title: str = "选择 mock 数据集") -> Optional[str]:
		"""弹窗选择 mock 数据集：用于回放不同测试样例。"""
		datasets = self.controller.list_mock_datasets()
		if not datasets:
			raise RuntimeError("当前没有可用的 mock 数据集")

		choice = {"value": None}
		# 这里是新增的第二个弹窗逻辑：当用户选择 mock 后继续细分数据集。
		window = tk.Toplevel(self.root)
		window.title(title)
		window.transient(self.root)
		window.grab_set()
		window.resizable(False, False)

		frame = ttk.Frame(window, padding=12)
		frame.pack(fill="both", expand=True)

		ttk.Label(frame, text="请选择要加载的 mock 回放数据集：").pack(anchor="w", pady=(0, 8))
		default_value = self.selected_mock_dataset if self.selected_mock_dataset in datasets else datasets[0]
		var = tk.StringVar(value=default_value)

		combo = ttk.Combobox(frame, textvariable=var, values=datasets, state="readonly", width=36)
		combo.pack(fill="x")
		combo.current(datasets.index(default_value))

		button_row = ttk.Frame(frame)
		button_row.pack(fill="x", pady=(8, 0))

		def on_ok() -> None:
			choice["value"] = var.get()
			window.destroy()

		def on_cancel() -> None:
			choice["value"] = None
			window.destroy()

		ttk.Button(button_row, text="取消", command=on_cancel).pack(side="right")
		ttk.Button(button_row, text="确定", command=on_ok).pack(side="right", padx=(0, 6))

		# 与数据源弹窗一致：数据集弹窗也保持在主窗口中央。
		window.update_idletasks()
		parent_x = self.root.winfo_rootx()
		parent_y = self.root.winfo_rooty()
		parent_w = self.root.winfo_width()
		parent_h = self.root.winfo_height()
		win_w = window.winfo_width()
		win_h = window.winfo_height()
		target_x = parent_x + max((parent_w - win_w) // 2, 0)
		target_y = parent_y + max((parent_h - win_h) // 2, 0)
		window.geometry(f"+{target_x}+{target_y}")

		window.protocol("WM_DELETE_WINDOW", on_cancel)
		self.root.wait_window(window)
		return choice["value"]

	def _startup_load_with_source_dialog(self) -> None:
		choice = self._show_source_selection_dialog("进入测试：选择数据源")
		if choice is None:
			self.right_info_panel.append_content("\n[UI] 未选择数据源，默认使用后端玩法环境")
			self.selected_source = "runtime"
		else:
			self.selected_source = choice
		self._on_click_load_data()

	def _auto_init_handler(self, init_message: Any):
		piece_args = []
		width = init_message.board.width
		height = init_message.board.height
		boarder = init_message.board.boarder

		candidates = []
		for y in range(height):
			if init_message.id == 1 and y >= boarder:
				continue
			if init_message.id == 2 and y <= boarder:
				continue
			for x in range(width):
				if init_message.board.grid[x][y].state == 1:
					candidates.append((x, y))

		for i in range(init_message.piece_cnt):
			x, y = candidates[i]
			arg = PieceArg()
			arg.strength = 10
			arg.dexterity = 10
			arg.intelligence = 10
			arg.equip = Point(1, 1)
			arg.pos = Point(x, y)
			piece_args.append(arg)
		return piece_args

	def _noop_action_handler(self, _env: Any) -> ActionSet:
		action = ActionSet()
		action.move = False
		action.attack = False
		action.spell = False
		return action

	def _attach_runtime_input(self) -> None:
		self.controller.set_function_input_methods(self._auto_init_handler, self._noop_action_handler)

	def _update_cards_from_env(self) -> None:
		env = self.controller.environment
		if env is None:
			return

		p1_hp = "0"
		p2_hp = "0"
		if getattr(env.player1, "pieces", None) is not None:
			p1_hp = str(sum(getattr(p, "health", 0) for p in env.player1.pieces if getattr(p, "is_alive", False)))
		if getattr(env.player2, "pieces", None) is not None:
			p2_hp = str(sum(getattr(p, "health", 0) for p in env.player2.pieces if getattr(p, "is_alive", False)))

		curr = getattr(env, "current_piece", None)
		curr_pos = "-"
		if curr is not None and getattr(curr, "position", None) is not None:
			curr_pos = f"({curr.position.x}, {curr.position.y})"

		self.player1_card.set_player_state(
			player_id="P1",
			position=curr_pos if curr is not None and getattr(curr, "team", 0) == 1 else "-",
			hp=p1_hp,
			power="-",
			agility="-",
			intelligence="-",
			weapon="-",
			armor="-",
		)
		self.player2_card.set_player_state(
			player_id="P2",
			position=curr_pos if curr is not None and getattr(curr, "team", 0) == 2 else "-",
			hp=p2_hp,
			power="-",
			agility="-",
			intelligence="-",
			weapon="-",
			armor="-",
		)

	def _camp_to_team(self, camp: str, players: dict[str, Any]) -> int:
		camp_lower = str(camp).strip().lower()
		player1_camp = str(players.get("player1", "")).strip().lower()
		player2_camp = str(players.get("player2", "")).strip().lower()
		if camp_lower and camp_lower == player1_camp:
			return 1
		if camp_lower and camp_lower == player2_camp:
			return 2
		if camp_lower in ("red", "player1", "p1", "team1", "1"):
			return 1
		if camp_lower in ("blue", "player2", "p2", "team2", "2"):
			return 2
		return 1

	def _extract_runtime_map_rows(self) -> list[list[int]]:
		env = self.controller.environment
		if env is None or not hasattr(env, "board"):
			return []
		board = env.board
		width = int(getattr(board, "width", 0))
		height = int(getattr(board, "height", 0))
		grid = getattr(board, "grid", None)
		if not isinstance(grid, list) or width <= 0 or height <= 0:
			return []

		rows: list[list[int]] = []
		for y in range(height):
			row: list[int] = []
			for x in range(width):
				cell_value = 0
				try:
					cell = grid[x][y]
					cell_value = int(getattr(cell, "state", 0))
				except Exception:
					cell_value = 0
				row.append(cell_value)
			rows.append(row)
		return rows

	def _extract_runtime_pieces(self) -> list[dict[str, Any]]:
		env = self.controller.environment
		if env is None:
			return []

		team_pieces: dict[int, list[Any]] = {1: [], 2: []}
		for team_id, player_attr in ((1, "player1"), (2, "player2")):
			player = getattr(env, player_attr, None)
			pieces = getattr(player, "pieces", None) if player is not None else None
			if not isinstance(pieces, list):
				continue
			for piece in pieces:
				if not bool(getattr(piece, "is_alive", True)):
					continue
				team_pieces[team_id].append(piece)

		render_pieces: list[dict[str, Any]] = []
		for team_id in (1, 2):
			sorted_pieces = sorted(team_pieces[team_id], key=lambda p: int(getattr(p, "id", 0)))
			for idx, piece in enumerate(sorted_pieces, start=1):
				pos = getattr(piece, "position", None)
				x = int(getattr(pos, "x", -1)) if pos is not None else -1
				y = int(getattr(pos, "y", -1)) if pos is not None else -1
				render_pieces.append(
					{
						"team": team_id,
						"x": x,
						"y": y,
						"label": f"player{team_id}\\n{idx}",
					}
				)
		return render_pieces

	def _initialize_mock_positions(self) -> None:
		self.mock_initial_positions = {}
		self.mock_last_health_by_id = {}
		self.mock_last_positions_by_id = {}
		self.mock_piece_number_by_id = {}
		game_data = self.controller.game_data
		if not isinstance(game_data, dict):
			return

		players = game_data.get("players", {})
		soldiers = game_data.get("soldiers", [])
		for soldier in soldiers:
			soldier_id = int(getattr(soldier, "ID", -1))
			camp = getattr(soldier, "camp", "")
			team = self._camp_to_team(camp, players if isinstance(players, dict) else {})
			position = getattr(soldier, "position", None)
			x = int(getattr(position, "x", -1)) if position is not None else -1
			y = int(getattr(position, "y", -1)) if position is not None else -1
			stats = getattr(soldier, "stats", {})
			health = int(stats.get("health", 0)) if isinstance(stats, dict) else 0
			self.mock_initial_positions[soldier_id] = {"team": team, "x": x, "y": y}
			self.mock_last_positions_by_id[soldier_id] = (x, y)
			self.mock_last_health_by_id[soldier_id] = health

		team_to_ids: dict[int, list[int]] = {1: [], 2: []}
		for soldier_id, state in self.mock_initial_positions.items():
			team_id = int(state.get("team", 1))
			if team_id not in team_to_ids:
				team_id = 1
			team_to_ids[team_id].append(soldier_id)

		for team_id in (1, 2):
			for index, soldier_id in enumerate(sorted(team_to_ids[team_id]), start=1):
				self.mock_piece_number_by_id[soldier_id] = index

	def _format_team_piece_name(self, team: int, piece_no: int) -> str:
		index = piece_no if piece_no > 0 else "?"
		return f"player{team}-{index}"

	def _extract_mock_round_stats_health(self, round_info: Any) -> dict[int, int]:
		health_by_id: dict[int, int] = {}
		stats = round_info.get("stats", []) if isinstance(round_info, dict) else []
		if not isinstance(stats, list):
			return health_by_id

		for item in stats:
			if not isinstance(item, dict):
				continue
			soldier_id = int(item.get("soldierId", -1))
			stats_obj = item.get("Stats", {})
			if soldier_id < 0 or not isinstance(stats_obj, dict):
				continue
			health_by_id[soldier_id] = int(stats_obj.get("health", 0))
		return health_by_id

	def _append_mock_round_details(self, round_number: int) -> None:
		game_data = self.controller.game_data
		if not isinstance(game_data, dict):
			return

		rounds = game_data.get("rounds", [])
		idx = int(round_number) - 1
		if idx < 0 or idx >= len(rounds):
			return

		round_info = rounds[idx]
		if not isinstance(round_info, dict):
			return

		team_lines: dict[int, list[str]] = {1: [], 2: []}
		actions = round_info.get("actions", [])
		if isinstance(actions, list):
			for action in actions:
				soldier_id = int(getattr(action, "soldierId", -1))
				action_type = str(getattr(action, "actionType", ""))
				path = getattr(action, "path", [])
				damage_dealt = getattr(action, "damageDealt", [])

				if isinstance(action, dict):
					soldier_id = int(action.get("soldierId", soldier_id))
					action_type = str(action.get("actionType", action_type))
					path = action.get("path", path)
					damage_dealt = action.get("damageDealt", damage_dealt)

				piece_state = self.mock_initial_positions.get(soldier_id, {})
				team = int(piece_state.get("team", 1))
				if team not in team_lines:
					team = 1

				piece_no = int(self.mock_piece_number_by_id.get(soldier_id, 0))
				piece_name = self._format_team_piece_name(team, piece_no)
				action_lower = action_type.strip().lower()

				if isinstance(path, list) and len(path) > 0 and "move" in action_lower:
					start_pos = self.mock_last_positions_by_id.get(soldier_id)
					last_point = path[-1]
					end_x = int(getattr(last_point, "x", -1))
					end_y = int(getattr(last_point, "y", -1))
					if isinstance(last_point, dict):
						end_x = int(last_point.get("x", end_x))
						end_y = int(last_point.get("y", end_y))

					if start_pos is not None:
						team_lines[team].append(
							f"{piece_name} 移动: ({start_pos[0]}, {start_pos[1]}) -> ({end_x}, {end_y})"
						)
					else:
						team_lines[team].append(f"{piece_name} 移动到: ({end_x}, {end_y})")
					self.mock_last_positions_by_id[soldier_id] = (end_x, end_y)
				else:
					team_lines[team].append(f"{piece_name} 行动: {action_type or '未知'}")

				if isinstance(damage_dealt, list):
					for dmg in damage_dealt:
						if not isinstance(dmg, dict):
							continue
						target_id = int(dmg.get("targetId", -1))
						damage = int(dmg.get("damage", 0))
						target_team = int(self.mock_initial_positions.get(target_id, {}).get("team", 1))
						target_no = int(self.mock_piece_number_by_id.get(target_id, 0))
						target_name = self._format_team_piece_name(target_team, target_no)
						team_lines[team].append(f"{piece_name} 对 {target_name} 造成伤害: {damage}")

		new_health_by_id = self._extract_mock_round_stats_health(round_info)
		for soldier_id, new_hp in new_health_by_id.items():
			old_hp = int(self.mock_last_health_by_id.get(soldier_id, new_hp))
			if old_hp != new_hp:
				team = int(self.mock_initial_positions.get(soldier_id, {}).get("team", 1))
				if team not in team_lines:
					team = 1
				piece_no = int(self.mock_piece_number_by_id.get(soldier_id, 0))
				piece_name = self._format_team_piece_name(team, piece_no)
				delta = old_hp - new_hp
				if delta > 0:
					team_lines[team].append(f"{piece_name} 血量变化: {old_hp} -> {new_hp} (受到伤害 {delta})")
				else:
					team_lines[team].append(f"{piece_name} 血量变化: {old_hp} -> {new_hp}")

		self.mock_last_health_by_id.update(new_health_by_id)

		self.right_info_panel.append_content(f"\n[回合 {round_number} 详细信息]")
		for team in (1, 2):
			if team_lines[team]:
				for line in team_lines[team]:
					self.right_info_panel.append_content(f"\n  player{team}: {line}")
			else:
				self.right_info_panel.append_content(f"\n  player{team}: 本回合无行动信息")

	def _snapshot_runtime_piece_states(self) -> dict[int, dict[str, Any]]:
		env = self.controller.environment
		if env is None:
			return {}

		states: dict[int, dict[str, Any]] = {}
		for team_id, player_attr in ((1, "player1"), (2, "player2")):
			player = getattr(env, player_attr, None)
			pieces = getattr(player, "pieces", None) if player is not None else None
			if not isinstance(pieces, list):
				continue
			for piece in pieces:
				piece_id = int(getattr(piece, "id", -1))
				if piece_id < 0:
					continue
				pos = getattr(piece, "position", None)
				x = int(getattr(pos, "x", -1)) if pos is not None else -1
				y = int(getattr(pos, "y", -1)) if pos is not None else -1
				states[piece_id] = {
					"team": team_id,
					"x": x,
					"y": y,
					"hp": int(getattr(piece, "health", 0)),
					"alive": bool(getattr(piece, "is_alive", True)),
				}
		return states

	def _append_runtime_round_details(
		self,
		round_number: int,
		before_states: dict[int, dict[str, Any]],
		after_states: dict[int, dict[str, Any]],
	) -> None:
		team_lines: dict[int, list[str]] = {1: [], 2: []}
		team_piece_ids: dict[int, list[int]] = {1: [], 2: []}

		for piece_id, state in after_states.items():
			team = int(state.get("team", 1))
			if team not in team_piece_ids:
				team = 1
			team_piece_ids[team].append(piece_id)

		piece_no_map: dict[int, int] = {}
		for team in (1, 2):
			for idx, piece_id in enumerate(sorted(team_piece_ids[team]), start=1):
				piece_no_map[piece_id] = idx

		for piece_id, after_state in after_states.items():
			before_state = before_states.get(piece_id)
			team = int(after_state.get("team", 1))
			if team not in team_lines:
				team = 1
			piece_name = self._format_team_piece_name(team, int(piece_no_map.get(piece_id, 0)))

			if before_state is None:
				continue

			old_x, old_y = int(before_state.get("x", -1)), int(before_state.get("y", -1))
			new_x, new_y = int(after_state.get("x", -1)), int(after_state.get("y", -1))
			if old_x != new_x or old_y != new_y:
				team_lines[team].append(f"{piece_name} 移动: ({old_x}, {old_y}) -> ({new_x}, {new_y})")

			old_hp = int(before_state.get("hp", 0))
			new_hp = int(after_state.get("hp", 0))
			if old_hp != new_hp:
				delta = old_hp - new_hp
				if delta > 0:
					team_lines[team].append(f"{piece_name} 血量变化: {old_hp} -> {new_hp} (受到伤害 {delta})")
				else:
					team_lines[team].append(f"{piece_name} 血量变化: {old_hp} -> {new_hp}")

		self.right_info_panel.append_content(f"\n[回合 {round_number} 详细信息]")
		for team in (1, 2):
			if team_lines[team]:
				for line in team_lines[team]:
					self.right_info_panel.append_content(f"\n  player{team}: {line}")
			else:
				self.right_info_panel.append_content(f"\n  player{team}: 本回合无明显状态变化")

	def _append_round_details_after_step(self, runtime_before_states: Optional[dict[int, dict[str, Any]]] = None) -> None:
		if self.controller.runtime_source == "runtime_env":
			env = self.controller.environment
			if env is None:
				return
			after_states = self._snapshot_runtime_piece_states()
			round_number = int(getattr(env, "round_number", 0))
			self._append_runtime_round_details(round_number, runtime_before_states or {}, after_states)
			return

		round_number = int(self.controller.current_round)
		self._append_mock_round_details(round_number)

	def _build_mock_pieces_for_current_round(self) -> list[dict[str, Any]]:
		game_data = self.controller.game_data
		if not isinstance(game_data, dict):
			return []
		if not self.mock_initial_positions:
			self._initialize_mock_positions()

		positions: dict[int, dict[str, Any]] = {
			sid: {"team": state["team"], "x": state["x"], "y": state["y"]}
			for sid, state in self.mock_initial_positions.items()
		}

		rounds = game_data.get("rounds", [])
		current_round = max(0, min(int(self.controller.current_round), len(rounds)))
		for idx in range(current_round):
			round_info = rounds[idx]
			actions = getattr(round_info, "actions", None)
			if actions is None and isinstance(round_info, dict):
				actions = round_info.get("actions", [])
			if not isinstance(actions, list):
				continue

			for action in actions:
				soldier_id = int(getattr(action, "soldierId", -1))
				path = getattr(action, "path", None)
				if path is None and isinstance(action, dict):
					soldier_id = int(action.get("soldierId", -1))
					path = action.get("path", [])
				if not isinstance(path, list) or not path:
					continue
				last_point = path[-1]
				x = int(getattr(last_point, "x", -1))
				y = int(getattr(last_point, "y", -1))
				if soldier_id in positions:
					positions[soldier_id]["x"] = x
					positions[soldier_id]["y"] = y

		team_to_ids: dict[int, list[int]] = {1: [], 2: []}
		for soldier_id, state in positions.items():
			team = int(state.get("team", 1))
			if team not in team_to_ids:
				team = 1
			team_to_ids[team].append(soldier_id)

		render_pieces: list[dict[str, Any]] = []
		for team_id in (1, 2):
			sorted_ids = sorted(team_to_ids[team_id])
			for index, soldier_id in enumerate(sorted_ids, start=1):
				state = positions[soldier_id]
				render_pieces.append(
					{
						"team": team_id,
						"x": int(state.get("x", -1)),
						"y": int(state.get("y", -1)),
						"label": f"player{team_id}\\n{index}",
					}
				)
		return render_pieces

	def _refresh_board_view(self) -> None:
		"""刷新棋盘底图和棋子位置。"""
		game_data = self.controller.game_data
		if not isinstance(game_data, dict):
			self.left_board_panel.set_board_state([], [])
			return

		if self.controller.runtime_source == "runtime_env" and self.controller.environment is not None:
			map_rows = self._extract_runtime_map_rows()
			pieces = self._extract_runtime_pieces()
			self.left_board_panel.set_board_state(map_rows, pieces)
			return

		board = game_data.get("map", {})
		map_rows = board.get("rows", []) if isinstance(board, dict) else []
		pieces = self._build_mock_pieces_for_current_round()
		self.left_board_panel.set_board_state(map_rows if isinstance(map_rows, list) else [], pieces)

	def _event_loop_tick(self) -> None:
		if not self.running:
			return
		try:
			runtime_before_states = self._snapshot_runtime_piece_states() if self.controller.runtime_source == "runtime_env" else None
			should_continue = self.controller.run_round()
			self._update_cards_from_env()
			self._refresh_board_view()
			self._append_round_details_after_step(runtime_before_states=runtime_before_states)
			if should_continue:
				self.loop_job = self.root.after(1000, self._event_loop_tick)
			else:
				self.running = False
				self.loop_job = None
				self.right_info_panel.append_content("\n[UI] 对局结束")
		except Exception as e:
			self.running = False
			self.loop_job = None
			self.right_info_panel.append_content(f"\n[UI] 循环执行异常: {e}")

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
		self.right_info_panel.text.configure(fg="#f97316")
		self.right_info_panel.set_content(
			"这里预留用于显示操作反馈、错误提示、关键变量与日志。\n"
			"按钮点击后会向此处追加示例文本，便于联调界面流程。"
		)

	# 以下按钮回调先提供最小可用行为，后续在 logic/controller.py 中接入真实逻辑。
	def _on_click_load_data(self) -> None:
		try:
			self.controller.select_mode("manual")
			if self.selected_source == "runtime":
				try:
					self.controller.load_game_data(prefer_runtime=True)
					self._attach_runtime_input()
					self.right_info_panel.append_content("\n[UI] 已加载后端玩法环境（本地运行）")
				except Exception as runtime_err:
					self.right_info_panel.append_content(f"\n[UI] 后端玩法环境加载失败，自动切换 mock：{runtime_err}")
					fallback_dataset = self._show_mock_dataset_dialog("后端失败：选择 mock 数据集")
					if fallback_dataset is None:
						self.right_info_panel.append_content("\n[UI] 未选择 mock 数据集，取消加载")
						return
					self.selected_mock_dataset = fallback_dataset
					self.controller.load_game_data(prefer_runtime=False, mock_dataset=self.selected_mock_dataset)
					self.selected_source = "mock"
					self.right_info_panel.append_content(f"\n[UI] 已加载 mock 回放数据: {self.selected_mock_dataset}")
			else:
				if not self.selected_mock_dataset:
					selected = self._show_mock_dataset_dialog()
					if selected is None:
						self.right_info_panel.append_content("\n[UI] 未选择 mock 数据集，取消加载")
						return
					self.selected_mock_dataset = selected
				self.controller.load_game_data(prefer_runtime=False, mock_dataset=self.selected_mock_dataset)
				self.right_info_panel.append_content(f"\n[UI] 已加载 mock 回放数据: {self.selected_mock_dataset}")

			self.loaded = True
			self._initialize_mock_positions()
			self._refresh_board_view()
		except Exception as e:
			self.right_info_panel.append_content(f"\n[UI] 加载失败: {e}")

	def _on_click_start(self) -> None:
		if not self.loaded:
			self._on_click_load_data()
			if not self.loaded:
				return
		if self.running:
			self.right_info_panel.append_content("\n[UI] 已在运行中")
			return
		self.running = True
		self.right_info_panel.append_content("\n[UI] 开始运行")
		self._event_loop_tick()

	def _on_click_pause(self) -> None:
		self.running = False
		if self.loop_job is not None:
			self.root.after_cancel(self.loop_job)
			self.loop_job = None
		self.right_info_panel.append_content("\n[UI] 已暂停")

	def _on_click_step(self) -> None:
		if not self.loaded:
			self._on_click_load_data()
			if not self.loaded:
				return
		try:
			runtime_before_states = self._snapshot_runtime_piece_states() if self.controller.runtime_source == "runtime_env" else None
			ok = self.controller.run_round()
			self._update_cards_from_env()
			self._refresh_board_view()
			self._append_round_details_after_step(runtime_before_states=runtime_before_states)
			self.right_info_panel.append_content(f"\n[UI] 单步执行完成, continue={ok}")
		except Exception as e:
			self.right_info_panel.append_content(f"\n[UI] 单步执行失败: {e}")

	def _on_click_reset(self) -> None:
		self._on_click_pause()
		try:
			if self.controller.runtime_source == "runtime_env":
				self.controller.reset_environment()
			self.loaded = False
			self.mock_initial_positions = {}
			self.mock_last_health_by_id = {}
			self.mock_last_positions_by_id = {}
			self.mock_piece_number_by_id = {}
			self.left_board_panel.reset_board_state()
			self.player1_card.set_player_state(**self.initial_player1_state)
			self.player2_card.set_player_state(**self.initial_player2_state)
			choice = self._show_source_selection_dialog("重置后：选择数据源")
			if choice is not None:
				self.selected_source = choice
			if self.selected_source == "mock":
				selected = self._show_mock_dataset_dialog("重置后：选择 mock 数据集")
				if selected is not None:
					self.selected_mock_dataset = selected
			self.right_info_panel.append_content("\n[UI] 重置完成，正在按选择加载数据")
			self._on_click_load_data()
		except Exception as e:
			self.right_info_panel.append_content(f"\n[UI] 重置失败: {e}")

	def _on_event_game_loaded(self, event) -> None:
		self.right_info_panel.append_content(
			f"\n[EVENT] GAME_LOADED source={event.payload.get('source')} mode={event.payload.get('mode')}"
		)

	def _on_event_round_started(self, event) -> None:
		self.right_info_panel.append_content(
			f"\n[EVENT] ROUND_STARTED round={event.payload.get('round_number')} source={event.payload.get('source')}"
		)

	def _on_event_round_finished(self, event) -> None:
		self.right_info_panel.append_content(
			f"\n[EVENT] ROUND_FINISHED round={event.payload.get('round_number')} game_over={event.payload.get('is_game_over')}"
		)

	def _on_event_game_over(self, _event) -> None:
		self.right_info_panel.append_content("\n[EVENT] GAME_OVER")

	def _on_click_initialize(self) -> None:
		"""初始化流程框架。

		当前行为：
		1. 棋盘恢复初始网格状态
		2. Player1/Player2 属性回到初始值
		
		后续可在此接入：
		- 后端初始化接口调用
		- 本地缓存与回放状态清空
		"""
		self._on_click_reset()
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