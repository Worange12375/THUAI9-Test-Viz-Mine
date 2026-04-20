"""棋子卡片/状态行刷新相关 service。

边界：
- 搬运 `MainUI` 中“左上 6 卡 + 行动状态行”相关的计算与刷新逻辑；
- 不改变现有 UI 行为，仅下沉实现，`main_ui` 作为状态容器传入。

约定：
- 函数第一个参数为 `main_ui`，通过 duck-typing 访问其字段/方法。
"""

from __future__ import annotations

from typing import Any


def get_mock_last_actor_id(main_ui: Any) -> int:
	"""从 mock 回放数据中提取“上一回合第一条 action 的 soldierId”。

	用于：在 6 卡里高亮最近行动者。
	"""
	game_data = getattr(getattr(main_ui, "controller", None), "game_data", None)
	if not isinstance(game_data, dict):
		return -1
	rounds = game_data.get("rounds", [])
	if not isinstance(rounds, list) or int(getattr(getattr(main_ui, "controller", None), "current_round", 0)) <= 0:
		return -1
	idx = int(getattr(main_ui.controller, "current_round", 0)) - 1
	if idx < 0 or idx >= len(rounds):
		return -1
	round_info = rounds[idx]
	actions = round_info.get("actions", []) if isinstance(round_info, dict) else []
	if not isinstance(actions, list) or not actions:
		return -1
	first_action = actions[0]
	if isinstance(first_action, dict):
		return int(first_action.get("soldierId", -1))
	return int(getattr(first_action, "soldierId", -1))


def update_cards_from_env(main_ui: Any) -> None:
	env = main_ui.controller.environment
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

	_ = (p1_hp, p2_hp, curr_pos)
	refresh_piece_action_status_line(main_ui)


def get_piece_action_status_text(main_ui: Any) -> str:
	if main_ui.controller.runtime_source == "runtime_env" and main_ui.controller.environment is not None:
		piece = main_ui._get_runtime_current_piece(main_ui.controller.environment)
		if piece is not None:
			piece_code = main_ui._get_piece_short_code(piece)
			pos = getattr(piece, "position", None)
			px = int(getattr(pos, "x", -1)) if pos is not None else -1
			py = int(getattr(pos, "y", -1)) if pos is not None else -1
			ap = int(getattr(piece, "action_points", 0))
			max_ap = int(getattr(piece, "max_action_points", ap))
			sp = int(getattr(piece, "spell_slots", 0))
			max_sp = int(getattr(piece, "max_spell_slots", sp))
			return (
				f"当前行动棋子: {piece_code} | 坐标({px}, {py})"
				f" | 行动{ap}/{max_ap} | 法术{sp}/{max_sp}"
			)
		return "当前行动棋子: 无"
	return "当前模式暂不提供行动时段驱动"


def refresh_piece_action_status_line(main_ui: Any) -> None:
	label = main_ui.action_panel_status_label
	if label is None:
		return
	try:
		if not bool(label.winfo_exists()):
			main_ui.action_panel_status_label = None
			return
		label.configure(text=get_piece_action_status_text(main_ui))
	except Exception:
		pass


def build_team_piece_view_data_runtime(main_ui: Any) -> dict[int, list[dict[str, Any]]]:
	env = main_ui.controller.environment
	data: dict[int, list[dict[str, Any]]] = {1: [], 2: []}
	if env is None:
		return data

	selected_piece = main_ui._get_runtime_current_piece(env)
	selected_id = int(getattr(selected_piece, "id", -1))
	for team_id, player_attr in ((1, "player1"), (2, "player2")):
		player = getattr(env, player_attr, None)
		pieces = main_ui._coerce_piece_list(getattr(player, "pieces", None) if player is not None else None)
		if not pieces:
			continue

		sorted_pieces = sorted(pieces, key=lambda p: int(getattr(p, "id", 0)))
		for idx, piece in enumerate(sorted_pieces, start=1):
			spell_cur = int(getattr(piece, "spell_slots", 0))
			spell_max = int(getattr(piece, "max_spell_slots", 0))
			action_cur = int(getattr(piece, "action_points", 0))
			action_max = int(getattr(piece, "max_action_points", 0))
			move_value = float(getattr(piece, "movement", 0.0))
			data[team_id].append(
				{
					"piece_id": int(getattr(piece, "id", -1)),
					"piece_no": idx,
					"hp": str(int(getattr(piece, "health", 0))),
					"physical_resist": str(int(getattr(piece, "physical_resist", 0))),
					"magic_resist": str(int(getattr(piece, "magic_resist", 0))),
					"spell_slots": f"{spell_cur}/{spell_max}",
					"action_points": f"{action_cur}/{action_max}",
					"movement": f"{move_value:.1f}",
					"is_selected": int(getattr(piece, "id", -1)) == selected_id,
				}
			)

		selected_items = [x for x in data[team_id] if x["is_selected"]]
		rest_items = [x for x in data[team_id] if not x["is_selected"]]
		ordered = (selected_items + rest_items)[:3]
		while len(ordered) < 3:
			ordered.append(
				{
					"piece_id": -1,
					"piece_no": len(ordered) + 1,
					"hp": "-",
					"physical_resist": "-",
					"magic_resist": "-",
					"spell_slots": "-/-",
					"action_points": "-/-",
					"movement": "-",
					"is_selected": False,
				}
			)
		data[team_id] = ordered

	return data


def build_team_piece_view_data_mock(main_ui: Any) -> dict[int, list[dict[str, Any]]]:
	data: dict[int, list[dict[str, Any]]] = {1: [], 2: []}
	if not main_ui.mock_initial_positions:
		return data

	selected_id = main_ui._get_mock_last_actor_id()
	for soldier_id, state in main_ui.mock_initial_positions.items():
		team = int(state.get("team", 1))
		if team not in data:
			team = 1
		piece_no = int(main_ui.mock_piece_number_by_id.get(soldier_id, 0))
		stats = main_ui.mock_piece_stats_by_id.get(soldier_id, {})
		spell_cur = stats.get("spell_slots", "-")
		spell_max = stats.get("max_spell_slots", "-")
		action_cur = stats.get("action_points", "-")
		action_max = stats.get("max_action_points", "-")
		hp_text = str(int(main_ui.mock_last_health_by_id.get(soldier_id, 0)))
		data[team].append(
			{
				"piece_id": int(soldier_id),
				"piece_no": piece_no if piece_no > 0 else 0,
				"hp": hp_text,
				"physical_resist": str(stats.get("physical_resist", "-")),
				"magic_resist": str(stats.get("magic_resist", "-")),
				"spell_slots": f"{spell_cur}/{spell_max}" if spell_cur != "-" and spell_max != "-" else "-/-",
				"action_points": f"{action_cur}/{action_max}" if action_cur != "-" and action_max != "-" else "-/-",
				"movement": str(stats.get("movement", "-")),
				"is_selected": int(soldier_id) == int(selected_id),
			}
		)

	for team in (1, 2):
		sorted_items = sorted(data[team], key=lambda x: int(x["piece_no"]) if int(x["piece_no"]) > 0 else 99)
		selected_items = [x for x in sorted_items if x["is_selected"]]
		rest_items = [x for x in sorted_items if not x["is_selected"]]
		ordered = (selected_items + rest_items)[:3]
		while len(ordered) < 3:
			ordered.append(
				{
					"piece_id": -1,
					"piece_no": len(ordered) + 1,
					"hp": "-",
					"physical_resist": "-",
					"magic_resist": "-",
					"spell_slots": "-/-",
					"action_points": "-/-",
					"movement": "-",
					"is_selected": False,
				}
			)
		data[team] = ordered

	return data


def slot_code(team: int, piece_no: int) -> str:
	letter = chr(ord("A") + max(0, piece_no - 1))
	return f"{team}{letter}"


def initialize_runtime_card_slots(main_ui: Any) -> None:
	"""按开局行动队列固定 6 个卡槽顺序；缺失棋子补到末尾。"""
	env = main_ui.controller.environment
	main_ui.runtime_card_slots = []
	if env is None:
		return

	piece_identity_to_slot: dict[int, tuple[int, int, str]] = {}
	slot_code_to_piece: dict[str, Any] = {}
	runtime_map = main_ui._runtime_piece_slot_map()
	for slot_key, piece in runtime_map.items():
		team_id = int(slot_key[1])
		idx = int(slot_key[-1])
		code = slot_code(team_id, idx)
		piece_identity_to_slot[id(piece)] = (team_id, idx, code)
		slot_code_to_piece[code] = piece

	action_queue = main_ui._coerce_piece_list(getattr(env, "action_queue", []))
	seen_codes: set[str] = set()
	for piece in action_queue:
		slot_meta = piece_identity_to_slot.get(id(piece))
		if slot_meta is None:
			continue
		team_id, piece_no, code = slot_meta
		if code in seen_codes:
			continue
		main_ui.runtime_card_slots.append(
			{
				"team": team_id,
				"piece_no": piece_no,
				"slot_code": code,
				"piece": piece,
			}
		)
		seen_codes.add(code)

	for team_id in (1, 2):
		for piece_no in (1, 2, 3):
			code = slot_code(team_id, piece_no)
			if code in seen_codes:
				continue
			main_ui.runtime_card_slots.append(
				{
					"team": team_id,
					"piece_no": piece_no,
					"slot_code": code,
					"piece": slot_code_to_piece.get(code),
				}
			)
			seen_codes.add(code)

	main_ui.runtime_card_slots = main_ui.runtime_card_slots[:6]


def initialize_mock_card_slots(main_ui: Any) -> None:
	"""mock 模式下固定 6 卡槽顺序：按回放首次行动顺序，缺失棋子补尾。"""
	main_ui.mock_card_slots = []
	game_data = main_ui.controller.game_data
	if not isinstance(game_data, dict):
		return

	code_to_soldier_id: dict[str, int] = {}
	for soldier_id, state in main_ui.mock_initial_positions.items():
		team = int(state.get("team", 1))
		piece_no = int(main_ui.mock_piece_number_by_id.get(soldier_id, 0))
		if team not in (1, 2) or piece_no not in (1, 2, 3):
			continue
		code = slot_code(team, piece_no)
		code_to_soldier_id[code] = int(soldier_id)

	ordered_codes: list[str] = []
	seen_ids: set[int] = set()
	rounds = game_data.get("rounds", [])
	if isinstance(rounds, list):
		for round_info in rounds:
			actions = round_info.get("actions", []) if isinstance(round_info, dict) else []
			if not isinstance(actions, list):
				continue
			for action in actions:
				soldier_id = int(action.get("soldierId", -1)) if isinstance(action, dict) else int(getattr(action, "soldierId", -1))
				if soldier_id < 0 or soldier_id in seen_ids:
					continue
				team = int(main_ui.mock_initial_positions.get(soldier_id, {}).get("team", 1))
				piece_no = int(main_ui.mock_piece_number_by_id.get(soldier_id, 0))
				if team not in (1, 2) or piece_no not in (1, 2, 3):
					continue
				ordered_codes.append(slot_code(team, piece_no))
				seen_ids.add(soldier_id)

	for team in (1, 2):
		for piece_no in (1, 2, 3):
			code = slot_code(team, piece_no)
			if code not in ordered_codes:
				ordered_codes.append(code)

	for code in ordered_codes[:6]:
		team = int(code[0]) if code and code[0].isdigit() else 1
		piece_no = ord(code[1]) - ord("A") + 1 if len(code) >= 2 else 1
		main_ui.mock_card_slots.append(
			{
				"team": team,
				"piece_no": piece_no,
				"slot_code": code,
				"soldier_id": code_to_soldier_id.get(code),
			}
		)


def refresh_piece_cards(main_ui: Any) -> None:
	if not hasattr(main_ui, "piece_cards"):
		return

	if main_ui.controller.runtime_source == "runtime_env" and main_ui.controller.environment is not None:
		if not main_ui.runtime_card_slots:
			initialize_runtime_card_slots(main_ui)

		current_piece = main_ui._get_runtime_current_piece(main_ui.controller.environment)

		def _role_display(piece_obj: Any) -> str:
			role_norm = str(getattr(piece_obj, "type", "") or "").strip().lower()
			weapon_id = main_ui._safe_int(str(getattr(piece_obj, "weapon", 0)), 0)
			if role_norm == "warrior":
				return "战士(短)" if weapon_id == 2 else "战士(长)"
			if role_norm == "mage":
				return "法师"
			if role_norm == "archer":
				return "射手"
			if role_norm == "custom":
				return "自定义"
			return str(getattr(piece_obj, "type", "") or "").strip()

		for idx, card in enumerate(main_ui.piece_cards):
			slot = main_ui.runtime_card_slots[idx] if idx < len(main_ui.runtime_card_slots) else None
			if slot is None:
				card.set_piece_state(
					team=1,
					piece_no=idx + 1,
					hp="-",
					physical_resist="-",
					magic_resist="-",
					spell_slots="-/-",
					action_points="-/-",
					movement="-",
					is_selected=False,
					header_text="--",
					position_text="(-,-)",
					physical_damage="-",
					magic_damage="-",
					dexterity="-",
					intelligence="-",
					strength="-",
					is_inactive=True,
				)
				continue

			team = int(slot.get("team", 1))
			piece_no = int(slot.get("piece_no", idx + 1))
			slot_code_text = str(slot.get("slot_code", slot_code(team, piece_no)))
			header_text = slot_code_text
			piece = slot.get("piece")

			if piece is None:
				card.set_piece_state(
					team=team,
					piece_no=piece_no,
					hp="-",
					physical_resist="-",
					magic_resist="-",
					spell_slots="-/-",
					action_points="-/-",
					movement="-",
					is_selected=False,
					header_text=header_text,
					position_text="(-,-)",
					physical_damage="-",
					magic_damage="-",
					dexterity="-",
					intelligence="-",
					strength="-",
					is_inactive=True,
				)
				continue

			alive = bool(getattr(piece, "is_alive", True))
			role_text = _role_display(piece)
			dy = bool(getattr(piece, "is_dying", False))
			if role_text:
				header_text = f"{slot_code_text} {role_text}"
			if dy:
				header_text = f"{header_text} [濒死]"
			hp_cur = int(getattr(piece, "health", 0)) if alive else 0
			hp_max = int(getattr(piece, "max_health", hp_cur))
			hp_text = f"{hp_cur}/{hp_max}"
			if dy and alive and hp_cur <= 0:
				hp_text = "💀"
			spell_cur = int(getattr(piece, "spell_slots", 0))
			spell_max = int(getattr(piece, "max_spell_slots", 0))
			action_cur = int(getattr(piece, "action_points", 0))
			action_max = int(getattr(piece, "max_action_points", 0))
			move_value = float(getattr(piece, "movement", 0.0))
			pos = getattr(piece, "position", None)
			pos_text = f"({int(getattr(pos, 'x', -1))},{int(getattr(pos, 'y', -1))})" if pos is not None else "(-,-)"
			current_id = int(getattr(current_piece, "id", -1)) if current_piece is not None else -1
			is_selected = int(getattr(piece, "id", -1)) == current_id and alive

			card.set_piece_state(
				team=team,
				piece_no=piece_no,
				hp=hp_text,
				position_text=pos_text,
				physical_damage=str(int(getattr(piece, "physical_damage", 0))),
				physical_resist=str(int(getattr(piece, "physical_resist", 0))),
				magic_damage=str(int(getattr(piece, "magic_damage", 0))),
				magic_resist=str(int(getattr(piece, "magic_resist", 0))),
				spell_slots=f"{spell_cur}/{spell_max}",
				action_points=f"{action_cur}/{action_max}",
				movement=f"{move_value:.1f}",
				dexterity=str(int(getattr(piece, "dexterity", 0))),
				intelligence=str(int(getattr(piece, "intelligence", 0))),
				strength=str(int(getattr(piece, "strength", 0))),
				is_selected=is_selected,
				header_text=header_text,
				is_dying=dy,
				is_inactive=not alive,
			)
		return

	# mock 模式：统一为固定顺序 6 槽位显示。
	if not main_ui.mock_card_slots:
		initialize_mock_card_slots(main_ui)

	selected_id = main_ui._get_mock_last_actor_id()
	for idx, card in enumerate(main_ui.piece_cards):
		slot = main_ui.mock_card_slots[idx] if idx < len(main_ui.mock_card_slots) else None
		if slot is None:
			card.set_piece_state(
				team=1,
				piece_no=idx + 1,
				hp="-",
				physical_resist="-",
				magic_resist="-",
				spell_slots="-/-",
				action_points="-/-",
				movement="-",
				is_selected=False,
				header_text="--",
				position_text="(-,-)",
				physical_damage="-",
				magic_damage="-",
				dexterity="-",
				intelligence="-",
				strength="-",
				is_inactive=True,
			)
			continue

		team = int(slot.get("team", 1))
		piece_no = int(slot.get("piece_no", idx + 1))
		header_text = str(slot.get("slot_code", slot_code(team, piece_no)))
		soldier_id = slot.get("soldier_id")

		if soldier_id is None:
			card.set_piece_state(
				team=team,
				piece_no=piece_no,
				hp="-",
				physical_resist="-",
				magic_resist="-",
				spell_slots="-/-",
				action_points="-/-",
				movement="-",
				is_selected=False,
				header_text=header_text,
				position_text="(-,-)",
				physical_damage="-",
				magic_damage="-",
				dexterity="-",
				intelligence="-",
				strength="-",
				is_inactive=True,
			)
			continue

		stats = main_ui.mock_piece_stats_by_id.get(int(soldier_id), {})
		hp_value = int(main_ui.mock_last_health_by_id.get(int(soldier_id), int(stats.get("health", 0) if isinstance(stats, dict) else 0)))
		hp_max = hp_value
		if isinstance(stats, dict):
			for key in ("max_health", "maxHealth", "health"):
				if key in stats:
					try:
						hp_max = int(stats.get(key, hp_value))
					except Exception:
						hp_max = hp_value
					break
		alive = hp_value > 0
		spell_cur = stats.get("spell_slots", "-") if isinstance(stats, dict) else "-"
		spell_max = stats.get("max_spell_slots", "-") if isinstance(stats, dict) else "-"
		action_cur = stats.get("action_points", "-") if isinstance(stats, dict) else "-"
		action_max = stats.get("max_action_points", "-") if isinstance(stats, dict) else "-"
		move_val = stats.get("movement", "-") if isinstance(stats, dict) else "-"
		is_selected = int(soldier_id) == int(selected_id) and alive

		card.set_piece_state(
			team=team,
			piece_no=piece_no,
			hp=f"{int(hp_value)}/{int(hp_max)}",
			position_text=f"({int(main_ui.mock_last_positions_by_id.get(int(soldier_id), (-1, -1))[0])},{int(main_ui.mock_last_positions_by_id.get(int(soldier_id), (-1, -1))[1])})",
			physical_damage=str(stats.get("physical_damage", "-") if isinstance(stats, dict) else "-"),
			physical_resist=str(stats.get("physical_resist", "-") if isinstance(stats, dict) else "-"),
			magic_damage=str(stats.get("magic_damage", "-") if isinstance(stats, dict) else "-"),
			magic_resist=str(stats.get("magic_resist", "-") if isinstance(stats, dict) else "-"),
			spell_slots=f"{spell_cur}/{spell_max}" if spell_cur != "-" and spell_max != "-" else "-/-",
			action_points=f"{action_cur}/{action_max}" if action_cur != "-" and action_max != "-" else "-/-",
			movement=str(move_val),
			dexterity=str(stats.get("dexterity", "-") if isinstance(stats, dict) else "-"),
			intelligence=str(stats.get("intelligence", "-") if isinstance(stats, dict) else "-"),
			strength=str(stats.get("strength", "-") if isinstance(stats, dict) else "-"),
			is_selected=is_selected,
			header_text=header_text,
			is_inactive=not alive,
		)
