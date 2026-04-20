from __future__ import annotations

from typing import Any, Optional

import tkinter as tk
from tkinter import ttk


def sync_replay_round_var(main_ui: Any) -> None:
	"""同步回放区显示的当前回合。"""
	if main_ui.controller.runtime_source == "runtime_env" and main_ui.controller.environment is not None:
		round_number = int(getattr(main_ui.controller.environment, "round_number", 0))
		main_ui.replay_round_var.set(max(1, round_number + 1))
		return
	total = get_mock_total_rounds(main_ui)
	next_round = int(main_ui.controller.current_round) + 1
	if total > 0:
		next_round = max(1, min(next_round, total))
	else:
		next_round = max(1, next_round)
	main_ui.replay_round_var.set(next_round)


def get_mock_total_rounds(main_ui: Any) -> int:
	game_data = main_ui.controller.game_data
	if not isinstance(game_data, dict):
		return 0
	rounds = game_data.get("rounds", [])
	return len(rounds) if isinstance(rounds, list) else 0


def show_interval_range_warning(main_ui: Any) -> None:
	"""弹窗提示播放间隔输入越界。"""
	window = tk.Toplevel(main_ui.root)
	window.title("提示")
	window.transient(main_ui.root)
	window.resizable(False, False)
	window.grab_set()
	frame = ttk.Frame(window, padding=12)
	frame.pack(fill="both", expand=True)
	ttk.Label(frame, text="间隔的合法范围是100-2000ms！").pack(anchor="w")
	window.update_idletasks()
	parent_x = main_ui.root.winfo_rootx()
	parent_y = main_ui.root.winfo_rooty()
	parent_w = main_ui.root.winfo_width()
	parent_h = main_ui.root.winfo_height()
	win_w = window.winfo_width()
	win_h = window.winfo_height()
	target_x = parent_x + max((parent_w - win_w) // 2, 0)
	target_y = parent_y + max((parent_h - win_h) // 2, 0)
	window.geometry(f"+{target_x}+{target_y}")


def apply_replay_speed_from_input(main_ui: Any, *, from_text_input: bool = False) -> None:
	"""从输入框读取回放间隔（毫秒）。"""
	try:
		raw_value = int(main_ui.replay_speed_var.get())
	except Exception:
		raw_value = main_ui.replay_speed_ms

	if from_text_input and (raw_value < 100 or raw_value > 2000):
		show_interval_range_warning(main_ui)

	value = max(100, min(raw_value, 2000))
	main_ui.replay_speed_ms = value
	main_ui.replay_speed_var.set(value)


def rebuild_mock_state_to_round(main_ui: Any, target_round: int) -> None:
	"""重建 mock 缓存到指定回合（用于后退/跳转）。"""
	initialize_mock_positions(main_ui)
	game_data = main_ui.controller.game_data
	if not isinstance(game_data, dict):
		return

	rounds = game_data.get("rounds", [])
	if not isinstance(rounds, list):
		return

	for idx in range(max(0, min(target_round, len(rounds)))):
		round_info = rounds[idx]
		if not isinstance(round_info, dict):
			continue

		actions = round_info.get("actions", [])
		if isinstance(actions, list):
			for action in actions:
				soldier_id = int(getattr(action, "soldierId", -1))
				path = getattr(action, "path", [])
				if isinstance(action, dict):
					soldier_id = int(action.get("soldierId", soldier_id))
					path = action.get("path", path)
				if soldier_id < 0 or not isinstance(path, list) or not path:
					continue
				last_point = path[-1]
				x = int(getattr(last_point, "x", -1))
				y = int(getattr(last_point, "y", -1))
				if isinstance(last_point, dict):
					x = int(last_point.get("x", x))
					y = int(last_point.get("y", y))
				main_ui.mock_last_positions_by_id[soldier_id] = (x, y)

		health_map = extract_mock_round_stats_health(main_ui, round_info)
		if health_map:
			main_ui.mock_last_health_by_id.update(health_map)


def apply_round_for_replay(main_ui: Any, target_round: int) -> None:
	"""设置目标回合并刷新界面（回合号语义为“该回合开始前”）。"""
	if main_ui.controller.runtime_source == "runtime_env":
		main_ui.right_info_panel.append_content("\n[UI] 后端实时环境暂不支持跳转/回退回合")
		sync_replay_round_var(main_ui)
		return

	total = get_mock_total_rounds(main_ui)
	target_display = max(1, min(int(target_round), total if total > 0 else 1))
	target_index = max(0, target_display - 1)
	main_ui.controller.current_round = target_index
	rebuild_mock_state_to_round(main_ui, target_index)
	sync_replay_round_var(main_ui)
	main_ui._refresh_piece_cards()
	main_ui._refresh_board_view()


def update_replay_play_pause_button_text(main_ui: Any) -> None:
	if main_ui.replay_play_pause_button is None:
		return
	main_ui.replay_play_pause_button.configure(text="暂停" if main_ui.running else "播放")


def on_replay_back(main_ui: Any) -> None:
	if main_ui.running:
		main_ui._on_click_pause()
	apply_round_for_replay(main_ui, int(main_ui.replay_round_var.get()) - 1)


def on_replay_forward(main_ui: Any) -> None:
	if main_ui.running:
		main_ui._on_click_pause()
	if not main_ui.loaded:
		main_ui.right_info_panel.append_content("\n[UI] 请先选择模式并加载数据")
		return
	if main_ui.controller.runtime_source == "runtime_env":
		main_ui._on_click_step()
		return
	apply_round_for_replay(main_ui, int(main_ui.replay_round_var.get()) + 1)


def on_replay_restart(main_ui: Any) -> None:
	if main_ui.running:
		main_ui._on_click_pause()
	apply_round_for_replay(main_ui, 1)


def on_replay_jump_to_round(main_ui: Any) -> None:
	try:
		target = int(main_ui.replay_round_var.get())
	except Exception:
		target = int(main_ui.controller.current_round)
	apply_round_for_replay(main_ui, target)


def on_replay_toggle_play_pause(main_ui: Any) -> None:
	apply_replay_speed_from_input(main_ui, from_text_input=False)
	if main_ui.running:
		main_ui._on_click_pause()
	else:
		main_ui._on_click_start()
	update_replay_play_pause_button_text(main_ui)


def close_replay_mode_ui(main_ui: Any) -> None:
	"""关闭回放模式并清理可变区。"""
	if main_ui.running:
		main_ui._on_click_pause()
	main_ui.replay_controls_visible = False
	main_ui.replay_play_pause_button = None
	main_ui.right_top_composite_panel.clear_variable_area()
	ttk.Label(
		main_ui.right_top_composite_panel.variable_frame,
		text="（可变区占位，后续根据模式放置内容）",
		anchor="center",
		foreground="#999999",
	).pack(fill="both", expand=True)


def on_click_replay_mode(main_ui: Any) -> None:
	"""点击“回放模式”后，显示回放控制区并接入功能。"""
	main_ui.right_top_composite_panel.clear_variable_area()

	container = ttk.Frame(main_ui.right_top_composite_panel.variable_frame)
	container.pack(fill="both", expand=True)
	container.columnconfigure(0, weight=1)

	player_row = ttk.Frame(container)
	player_row.grid(row=0, column=0, sticky="ew", pady=(0, 8))
	player_row.columnconfigure(0, weight=1)
	player_row.columnconfigure(1, weight=1)
	player_row.columnconfigure(2, weight=1)
	player_row.columnconfigure(3, weight=1)

	ttk.Button(player_row, text="重新开始", command=main_ui._on_replay_restart).grid(
		row=0, column=0, sticky="ew", padx=(0, 4)
	)
	ttk.Button(player_row, text="后退", command=main_ui._on_replay_back).grid(row=0, column=1, sticky="ew", padx=4)
	main_ui.replay_play_pause_button = ttk.Button(player_row, text="播放", command=main_ui._on_replay_toggle_play_pause)
	main_ui.replay_play_pause_button.grid(row=0, column=2, sticky="ew", padx=4)
	ttk.Button(player_row, text="前进", command=main_ui._on_replay_forward).grid(row=0, column=3, sticky="ew", padx=(4, 0))

	speed_row = ttk.Frame(container)
	speed_row.grid(row=1, column=0, sticky="ew", pady=(0, 6))
	ttk.Label(speed_row, text="播放间隔(ms):").pack(side="left")
	speed_spin = tk.Spinbox(
		speed_row,
		from_=100,
		to=2000,
		increment=50,
		width=8,
		textvariable=main_ui.replay_speed_var,
		command=lambda: main_ui._apply_replay_speed_from_input(from_text_input=False),
	)
	speed_spin.pack(side="left", padx=(6, 6))
	speed_spin.bind("<Return>", lambda _e: main_ui._apply_replay_speed_from_input(from_text_input=True))
	speed_spin.bind("<FocusOut>", lambda _e: main_ui._apply_replay_speed_from_input(from_text_input=True))

	round_row = ttk.Frame(container)
	round_row.grid(row=2, column=0, sticky="ew")
	ttk.Label(round_row, text="第").pack(side="left")
	round_spin = tk.Spinbox(
		round_row,
		from_=1,
		to=max(1, main_ui._get_mock_total_rounds()),
		increment=1,
		width=8,
		textvariable=main_ui.replay_round_var,
		command=main_ui._on_replay_jump_to_round,
	)
	round_spin.pack(side="left", padx=(4, 4))
	ttk.Label(round_row, text="回合").pack(side="left", padx=(0, 8))
	ttk.Button(round_row, text="跳转", command=main_ui._on_replay_jump_to_round).pack(side="left")

	round_spin.bind("<Return>", lambda _e: main_ui._on_replay_jump_to_round())
	round_spin.bind("<FocusOut>", lambda _e: main_ui._on_replay_jump_to_round())

	main_ui.replay_controls_visible = True
	sync_replay_round_var(main_ui)
	update_replay_play_pause_button_text(main_ui)
	main_ui.right_info_panel.append_content("\n[UI] 已进入回放模式：可变区显示回放控制")


def camp_to_team(camp: str, players: dict[str, Any]) -> int:
	"""将回放数据中的 camp 文本归一为 team=1/2。"""
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


def initialize_mock_positions(main_ui: Any) -> None:
	main_ui.mock_initial_positions = {}
	main_ui.mock_piece_stats_by_id = {}
	main_ui.mock_last_health_by_id = {}
	main_ui.mock_last_positions_by_id = {}
	main_ui.mock_piece_number_by_id = {}
	game_data = main_ui.controller.game_data
	if not isinstance(game_data, dict):
		return

	players = game_data.get("players", {})
	soldiers = game_data.get("soldiers", [])
	for soldier in soldiers:
		soldier_id = int(getattr(soldier, "ID", -1))
		camp = getattr(soldier, "camp", "")
		team = camp_to_team(camp, players if isinstance(players, dict) else {})
		position = getattr(soldier, "position", None)
		x = int(getattr(position, "x", -1)) if position is not None else -1
		y = int(getattr(position, "y", -1)) if position is not None else -1
		stats = getattr(soldier, "stats", {})
		health = int(stats.get("health", 0)) if isinstance(stats, dict) else 0
		main_ui.mock_initial_positions[soldier_id] = {"team": team, "x": x, "y": y}
		main_ui.mock_piece_stats_by_id[soldier_id] = stats if isinstance(stats, dict) else {}
		main_ui.mock_last_positions_by_id[soldier_id] = (x, y)
		main_ui.mock_last_health_by_id[soldier_id] = health

	team_to_ids: dict[int, list[int]] = {1: [], 2: []}
	for soldier_id, state in main_ui.mock_initial_positions.items():
		team_id = int(state.get("team", 1))
		if team_id not in team_to_ids:
			team_id = 1
		team_to_ids[team_id].append(soldier_id)

	for team_id in (1, 2):
		for index, soldier_id in enumerate(sorted(team_to_ids[team_id]), start=1):
			main_ui.mock_piece_number_by_id[soldier_id] = index


def format_team_piece_name(_main_ui: Any, team: int, piece_no: int) -> str:
	index = piece_no if piece_no > 0 else "?"
	return f"player{team}-{index}"


def extract_mock_round_stats_health(_main_ui: Any, round_info: Any) -> dict[int, int]:
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


def append_mock_round_details(main_ui: Any, round_number: int) -> None:
	game_data = main_ui.controller.game_data
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

			piece_state = main_ui.mock_initial_positions.get(soldier_id, {})
			team = int(piece_state.get("team", 1))
			if team not in team_lines:
				team = 1

			piece_no = int(main_ui.mock_piece_number_by_id.get(soldier_id, 0))
			piece_name = format_team_piece_name(main_ui, team, piece_no)
			action_lower = action_type.strip().lower()

			if isinstance(path, list) and len(path) > 0 and "move" in action_lower:
				start_pos = main_ui.mock_last_positions_by_id.get(soldier_id)
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
				main_ui.mock_last_positions_by_id[soldier_id] = (end_x, end_y)
			else:
				team_lines[team].append(f"{piece_name} 行动: {action_type or '未知'}")

			if isinstance(damage_dealt, list):
				for dmg in damage_dealt:
					if not isinstance(dmg, dict):
						continue
					target_id = int(dmg.get("targetId", -1))
					damage = int(dmg.get("damage", 0))
					target_team = int(main_ui.mock_initial_positions.get(target_id, {}).get("team", 1))
					target_no = int(main_ui.mock_piece_number_by_id.get(target_id, 0))
					target_name = format_team_piece_name(main_ui, target_team, target_no)
					team_lines[team].append(f"{piece_name} 对 {target_name} 造成伤害: {damage}")

	new_health_by_id = extract_mock_round_stats_health(main_ui, round_info)
	for soldier_id, new_hp in new_health_by_id.items():
		old_hp = int(main_ui.mock_last_health_by_id.get(soldier_id, new_hp))
		if old_hp != new_hp:
			team = int(main_ui.mock_initial_positions.get(soldier_id, {}).get("team", 1))
			if team not in team_lines:
				team = 1
			piece_no = int(main_ui.mock_piece_number_by_id.get(soldier_id, 0))
			piece_name = format_team_piece_name(main_ui, team, piece_no)
			delta = old_hp - new_hp
			if delta > 0:
				team_lines[team].append(f"{piece_name} 血量变化: {old_hp} -> {new_hp} (受到伤害 {delta})")
			else:
				team_lines[team].append(f"{piece_name} 血量变化: {old_hp} -> {new_hp}")

	main_ui.mock_last_health_by_id.update(new_health_by_id)

	main_ui.right_info_panel.append_content(f"\n[回合 {round_number} 详细信息]")
	for team in (1, 2):
		if team_lines[team]:
			for line in team_lines[team]:
				main_ui.right_info_panel.append_content(f"\n  player{team}: {line}")
		else:
			main_ui.right_info_panel.append_content(f"\n  player{team}: 本回合无行动信息")


def snapshot_runtime_piece_states(main_ui: Any) -> dict[int, dict[str, Any]]:
	env = main_ui.controller.environment
	if env is None:
		return {}

	states: dict[int, dict[str, Any]] = {}
	for team_id, player_attr in ((1, "player1"), (2, "player2")):
		player = getattr(env, player_attr, None)
		pieces = main_ui._coerce_piece_list(getattr(player, "pieces", None) if player is not None else None)
		if not pieces:
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
				"dy": bool(getattr(piece, "is_dying", False)),
			}
	return states


def append_runtime_round_details(
	main_ui: Any,
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
		piece_name = format_team_piece_name(main_ui, team, int(piece_no_map.get(piece_id, 0)))

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
			old_dy = bool(before_state.get("dy", False))
			new_dy = bool(after_state.get("dy", False))
			old_text = "💀" if old_dy and int(old_hp) <= 0 and bool(before_state.get("alive", True)) else str(old_hp)
			new_text = "💀" if new_dy and int(new_hp) <= 0 and bool(after_state.get("alive", True)) else str(new_hp)
			if delta > 0:
				team_lines[team].append(f"{piece_name} 血量变化: {old_text} -> {new_text} (受到伤害 {delta})")
			else:
				team_lines[team].append(f"{piece_name} 血量变化: {old_text} -> {new_text}")

	main_ui.right_info_panel.append_content(f"\n[回合 {round_number} 详细信息]")
	for team in (1, 2):
		if team_lines[team]:
			for line in team_lines[team]:
				main_ui.right_info_panel.append_content(f"\n  player{team}: {line}")
		else:
			main_ui.right_info_panel.append_content(f"\n  player{team}: 本回合无明显状态变化")


def append_round_details_after_step(main_ui: Any, runtime_before_states: Optional[dict[int, dict[str, Any]]] = None) -> None:
	if main_ui.controller.runtime_source == "runtime_env":
		env = main_ui.controller.environment
		if env is None:
			return
		after_states = main_ui._snapshot_runtime_piece_states()
		round_number = int(getattr(env, "round_number", 0))
		main_ui._append_runtime_round_details(round_number, runtime_before_states or {}, after_states)
		main_ui._flush_runtime_pending_messages(env)
		return

	round_number = int(main_ui.controller.current_round)
	main_ui._append_mock_round_details(round_number)


def build_mock_pieces_for_current_round(main_ui: Any) -> list[dict[str, Any]]:
	game_data = main_ui.controller.game_data
	if not isinstance(game_data, dict):
		return []
	if not main_ui.mock_initial_positions:
		main_ui._initialize_mock_positions()

	positions: dict[int, dict[str, Any]] = {
		sid: {"team": state["team"], "x": state["x"], "y": state["y"]}
		for sid, state in main_ui.mock_initial_positions.items()
	}

	rounds = game_data.get("rounds", [])
	current_round = max(0, min(int(main_ui.controller.current_round), len(rounds)))
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
					"label": f"player{team_id}\n{index}",
				}
			)
	return render_pieces


def event_loop_tick(main_ui: Any) -> None:
	if not main_ui.running:
		return
	try:
		runtime_before_states = (
			main_ui._snapshot_runtime_piece_states() if main_ui.controller.runtime_source == "runtime_env" else None
		)
		should_continue = main_ui.controller.run_round()
		main_ui._update_cards_from_env()
		main_ui._refresh_piece_cards()
		main_ui._refresh_board_view()
		main_ui._append_round_details_after_step(runtime_before_states=runtime_before_states)
		main_ui._sync_replay_round_var()
		if should_continue:
			main_ui.loop_job = main_ui.root.after(max(50, int(main_ui.replay_speed_ms)), main_ui._event_loop_tick)
		else:
			main_ui.running = False
			main_ui.loop_job = None
			main_ui._update_replay_play_pause_button_text()
			main_ui.right_info_panel.append_content("\n对局结束")
			if main_ui.controller.runtime_source == "runtime_env":
				main_ui._show_game_over_reset_dialog()
	except Exception as e:
		main_ui.running = False
		main_ui.loop_job = None
		main_ui._update_replay_play_pause_button_text()
		main_ui.right_info_panel.append_content(f"\n[UI] 循环执行异常: {e}")


def run_single_round_once(main_ui: Any, source_tag: str = "UI") -> None:
	"""执行一回合并刷新 UI，用于行动提交后立即生效。"""
	if not main_ui.loaded:
		main_ui.right_info_panel.append_content("\n[UI] 尚未加载数据，无法执行回合")
		return
	try:
		runtime_before_states = (
			main_ui._snapshot_runtime_piece_states() if main_ui.controller.runtime_source == "runtime_env" else None
		)
		ok = main_ui.controller.run_round()
		main_ui._update_cards_from_env()
		main_ui._refresh_piece_cards()
		main_ui._refresh_board_view()
		main_ui._append_round_details_after_step(runtime_before_states=runtime_before_states)
		main_ui._sync_replay_round_var()
		main_ui.right_info_panel.append_content(f"\n[UI] {source_tag}触发单回合完成, continue={ok}")
	except Exception as e:
		main_ui.right_info_panel.append_content(f"\n[UI] {source_tag}触发单回合失败: {e}")


def on_click_start(main_ui: Any) -> None:
	if not main_ui.loaded:
		main_ui.right_info_panel.append_content("\n[UI] 尚未加载数据，请先点击“模式选择”")
		return
	if main_ui.running:
		main_ui.right_info_panel.append_content("\n[UI] 已在运行中")
		return
	main_ui.running = True
	main_ui.right_info_panel.append_content("\n[UI] 开始运行")
	main_ui._update_replay_play_pause_button_text()
	main_ui._event_loop_tick()


def on_click_pause(main_ui: Any) -> None:
	main_ui.running = False
	if main_ui.loop_job is not None:
		main_ui.root.after_cancel(main_ui.loop_job)
		main_ui.loop_job = None
	main_ui._update_replay_play_pause_button_text()
	main_ui.right_info_panel.append_content("\n[UI] 已暂停")


def on_click_step(main_ui: Any) -> None:
	if not main_ui.loaded:
		main_ui.right_info_panel.append_content("\n[UI] 尚未加载数据，请先点击“模式选择”")
		return
	try:
		runtime_before_states = (
			main_ui._snapshot_runtime_piece_states() if main_ui.controller.runtime_source == "runtime_env" else None
		)
		ok = main_ui.controller.run_round()
		main_ui._update_cards_from_env()
		main_ui._refresh_piece_cards()
		main_ui._refresh_board_view()
		main_ui._append_round_details_after_step(runtime_before_states=runtime_before_states)
		main_ui._sync_replay_round_var()
		main_ui.right_info_panel.append_content(f"\n[UI] 单步执行完成, continue={ok}")
	except Exception as e:
		main_ui.right_info_panel.append_content(f"\n[UI] 单步执行失败: {e}")
