"""Runtime init/input 服务。

本文件负责从 `main_ui.py` 下沉的“后端 runtime 模式初始化与输入”相关逻辑：
- 6 槽位初始化默认配置准备；
- 初始化配置应用到 runtime env（棋子属性/装备/位置/棋盘占用格）；
- init handler（把 UI 配置转换为后端 PieceArg 列表）；
- UI action handler/noop/current_piece 选择；
- runtime env 初始化阶段的先攻掷骰明细捕获。

约束：
- 不创建/布局 Tk 控件；
- 不 import main_ui（避免循环依赖）；
- 通过 duck-typing 访问 main_ui 的方法与字段，保持 UX/行为不变。
"""

from __future__ import annotations

from typing import Any, Optional

from env import ActionSet, PieceArg, Point


def prepare_runtime_piece_init_defaults(main_ui: Any) -> None:
	"""准备后端模式初始化阶段的 6 槽位默认配置。"""
	if getattr(main_ui, "runtime_piece_init_config", None):
		return

	width = 20
	height = 20
	border = height // 2
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	if env is not None and getattr(env, "board", None) is not None:
		board = env.board
		width = int(getattr(board, "width", width))
		height = int(getattr(board, "height", height))
		border = int(getattr(board, "boarder", border))

	fixed_positions: dict[str, tuple[int, int]] = {
		"p1_1": (3, 8),
		"p1_2": (8, 3),
		"p1_3": (17, 4),
		"p2_1": (16, 11),
		"p2_2": (11, 16),
		"p2_3": (2, 15),
	}

	def clamp_pos(x: int, y: int) -> tuple[int, int]:
		cx = max(0, min(int(x), max(0, width - 1)))
		cy = max(0, min(int(y), max(0, height - 1)))
		return cx, cy

	for team in (1, 2):
		for idx in (1, 2, 3):
			slot_key = f"p{team}_{idx}"
			x, y = fixed_positions.get(slot_key, (0, 0))
			x, y = clamp_pos(x, y)
			if main_ui._is_profession_mode():
				# 职业模式：天赋必须手动分配，默认空值；血量/派生属性由后端公式决定，不允许手填。
				main_ui.runtime_piece_init_config[slot_key] = {
					"hp": "-",
					"strength": "-",
					"dexterity": "-",
					"intelligence": "-",
					"physical_resist": "-",
					"magic_resist": "-",
					"physical_damage": "-",
					"magic_damage": "-",
					"action_points": "-",
					"max_action_points": "-",
					"spell_slots": "-",
					"max_spell_slots": "-",
					"movement": "-",
					"weapon": "长剑",
					"armor": "轻甲",
					"profession": "战士(长)",
					"pos_x": str(x),
					"pos_y": str(y),
				}
			else:
				# 自定义模式默认数值：显示仍为“自定义/无甲”，但战斗属性默认对齐“长剑+中甲+天赋10”。
				main_ui.runtime_piece_init_config[slot_key] = {
					"hp": "",
					"profession": "自定义",
					"weapon": "自定义",
					"armor": "无甲",
					"strength": "10",
					"dexterity": "10",
					"intelligence": "10",
					"physical_resist": "15",
					"magic_resist": "13",
					"physical_damage": "18",
					"magic_damage": "0",
					"action_points": "2",
					"max_action_points": "2",
					"spell_slots": "2",
					"max_spell_slots": "2",
					"movement": "25",
					"pos_x": str(x),
					"pos_y": str(y),
				}


def set_runtime_board_all_walkable(main_ui: Any) -> None:
	"""后端模式初始化前，将地图默认设置为全盘可走。"""
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	if env is None or getattr(env, "board", None) is None:
		return
	board = env.board
	width = int(getattr(board, "width", 0))
	height = int(getattr(board, "height", 0))
	if width <= 0 or height <= 0:
		return
	for x in range(width):
		for y in range(height):
			cell = board.grid[x][y]
			cell.state = 1
			cell.player_id = -1
			cell.piece_id = -1
	main_ui.right_info_panel.append_content("\n[UI] 后端模式：地图已重置为全盘可走")


def apply_runtime_piece_config_to_environment(main_ui: Any) -> None:
	"""将初始化配置应用到已初始化的后端环境。"""
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	if env is None:
		return

	runtime_map = main_ui._runtime_piece_slot_map()
	board = getattr(env, "board", None)
	if board is not None and getattr(board, "grid", None) is not None:
		for x in range(int(getattr(board, "width", 0))):
			for y in range(int(getattr(board, "height", 0))):
				cell = board.grid[x][y]
				if int(getattr(cell, "state", 0)) == 2:
					cell.state = 1
					cell.player_id = -1
					cell.piece_id = -1

	for slot_key in main_ui._piece_slot_keys():
		cfg = main_ui.runtime_piece_init_config.get(slot_key, {})
		piece = runtime_map.get(slot_key)
		if piece is None:
			continue
		hp_raw = str(cfg.get("hp", "-")).strip()
		hp_value = main_ui._safe_int(hp_raw, -1)
		if hp_raw in ("", "-", "-1") or hp_value <= 0:
			piece.is_alive = False
			piece.health = 0
			continue

		piece.is_alive = True
		piece.health = max(1, hp_value)
		piece.max_health = max(piece.health, main_ui._safe_int(str(cfg.get("hp", piece.health)), piece.health))
		piece.strength = main_ui._safe_int(str(cfg.get("strength", 10)), int(getattr(piece, "strength", 10)))
		piece.dexterity = main_ui._safe_int(str(cfg.get("dexterity", 10)), int(getattr(piece, "dexterity", 10)))
		piece.intelligence = main_ui._safe_int(str(cfg.get("intelligence", 10)), int(getattr(piece, "intelligence", 10)))
		piece.physical_resist = main_ui._safe_int(str(cfg.get("physical_resist", 6)), int(getattr(piece, "physical_resist", 6)))
		piece.magic_resist = main_ui._safe_int(str(cfg.get("magic_resist", 6)), int(getattr(piece, "magic_resist", 6)))
		piece.physical_damage = main_ui._safe_int(str(cfg.get("physical_damage", 6)), int(getattr(piece, "physical_damage", 6)))
		piece.magic_damage = main_ui._safe_int(str(cfg.get("magic_damage", 6)), int(getattr(piece, "magic_damage", 6)))
		piece.max_action_points = main_ui._safe_int(str(cfg.get("max_action_points", 2)), int(getattr(piece, "max_action_points", 2)))
		piece.action_points = min(
			main_ui._safe_int(str(cfg.get("action_points", 2)), int(getattr(piece, "action_points", 2))),
			int(piece.max_action_points),
		)
		piece.max_spell_slots = main_ui._safe_int(str(cfg.get("max_spell_slots", 2)), int(getattr(piece, "max_spell_slots", 2)))
		piece.spell_slots = min(
			main_ui._safe_int(str(cfg.get("spell_slots", 2)), int(getattr(piece, "spell_slots", 2))),
			int(piece.max_spell_slots),
		)
		piece.movement = main_ui._safe_float(str(cfg.get("movement", 10)), float(getattr(piece, "movement", 10.0)))
		piece.max_movement = max(piece.movement, float(getattr(piece, "max_movement", piece.movement)))
		piece.position = Point(
			main_ui._safe_int(str(cfg.get("pos_x", 0)), 0),
			main_ui._safe_int(str(cfg.get("pos_y", 0)), 0),
		)

		weapon_label = main_ui._normalize_weapon_label(str(cfg.get("weapon", "自定义")).strip() or "自定义")
		armor_label = str(cfg.get("armor", "无甲")).strip() or "无甲"
		weapon_id = main_ui._weapon_label_to_weapon_id(weapon_label)
		armor_id = main_ui._armor_label_to_armor_id(armor_label)
		# 兼容“自定义开局默认显示为自定义/无甲”：避免把初始化时的真实装备覆盖成 0/0。
		if not (
			main_ui._normalize_selected_source_value(main_ui.selected_source) == "runtime_custom"
			and weapon_label == "自定义"
			and armor_label == "无甲"
			and int(weapon_id) == 0
			and int(armor_id) == 0
		):
			piece.type = main_ui._weapon_id_to_piece_type(weapon_id)
			setattr(piece, "weapon", int(weapon_id))
			setattr(piece, "armor", int(armor_id))

		if board is not None:
			x = int(piece.position.x)
			y = int(piece.position.y)
			if 0 <= x < int(getattr(board, "width", 0)) and 0 <= y < int(getattr(board, "height", 0)):
				board.grid[x][y].state = 2
				board.grid[x][y].player_id = int(getattr(piece, "team", 0))
				board.grid[x][y].piece_id = int(getattr(piece, "id", -1))


def auto_init_handler(main_ui: Any, init_message: Any):
	if main_ui.runtime_piece_init_config:
		piece_args: list[Any] = []
		team_id = int(getattr(init_message, "id", 1))
		for idx in (1, 2, 3):
			slot_key = f"p{team_id}_{idx}"
			cfg = main_ui.runtime_piece_init_config.get(slot_key, {})
			if main_ui._is_profession_mode():
				strength = main_ui._parse_talent_int(cfg.get("strength"))
				dexterity = main_ui._parse_talent_int(cfg.get("dexterity"))
				intelligence = main_ui._parse_talent_int(cfg.get("intelligence"))
				if strength is None or dexterity is None or intelligence is None:
					continue
				cap = main_ui._get_talent_total_cap()
				if (strength + dexterity + intelligence) > cap:
					continue
			else:
				hp_raw = str(cfg.get("hp", "-")).strip()
				if hp_raw in ("", "-", "-1") or main_ui._safe_int(hp_raw, -1) <= 0:
					continue
			arg = PieceArg()
			if main_ui._is_profession_mode():
				arg.strength = int(strength)
				arg.dexterity = int(dexterity)
				arg.intelligence = int(intelligence)
			else:
				arg.strength = main_ui._safe_int(str(cfg.get("strength", 10)), 10)
				arg.dexterity = main_ui._safe_int(str(cfg.get("dexterity", 10)), 10)
				arg.intelligence = main_ui._safe_int(str(cfg.get("intelligence", 10)), 10)
			weapon_raw = cfg.get("weapon", 1)
			weapon_id = main_ui._safe_int(str(weapon_raw), 0)
			weapon_label = ""
			if weapon_id not in (1, 2, 3, 4):
				weapon_label = main_ui._normalize_weapon_label(str(weapon_raw)) or "自定义"
				weapon_id = main_ui._weapon_label_to_weapon_id(weapon_label)
				# 自定义模式默认：UI 显示“自定义”时，初始化仍按长剑生成（便于保持后端武器相关行为）。
				if int(weapon_id) == 0 and weapon_label == "自定义":
					weapon_id = 1
			armor_raw = cfg.get("armor", 1)
			armor_id = main_ui._safe_int(str(armor_raw), 0)
			armor_label = ""
			if armor_id not in (1, 2, 3):
				armor_label = str(armor_raw or "无甲")
				armor_id = main_ui._armor_label_to_armor_id(armor_label)
				# 自定义模式默认：UI 显示“无甲”时，初始化仍按中甲生成（与默认数值口径一致）。
				if int(armor_id) == 0 and armor_label == "无甲":
					armor_id = 2
			if weapon_id == 4:
				armor_id = 1
			arg.equip = Point(int(weapon_id), int(armor_id))
			arg.pos = Point(
				main_ui._safe_int(str(cfg.get("pos_x", 0)), 0),
				main_ui._safe_int(str(cfg.get("pos_y", 0)), 0),
			)
			piece_args.append(arg)
		if piece_args:
			return piece_args

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


def noop_action_handler(_env: Any) -> ActionSet:
	action = ActionSet()
	action.move = False
	action.attack = False
	action.spell = False
	return action


def get_runtime_current_piece(main_ui: Any, env: Any) -> Any:
	"""优先取 env.current_piece，缺失时回退 action_queue 队首。"""
	current_piece = getattr(env, "current_piece", None)
	if current_piece is not None and bool(getattr(current_piece, "is_alive", True)):
		if main_ui.runtime_card_slots:
			slot_pieces = [s.get("piece") for s in main_ui.runtime_card_slots]
			if current_piece not in slot_pieces:
				match_piece = next(
					(
						p
						for p in slot_pieces
						if int(getattr(p, "id", -1)) == int(getattr(current_piece, "id", -2))
					),
					None,
				)
				if match_piece is not None:
					setattr(env, "current_piece", match_piece)
					return match_piece
		return current_piece
	action_queue = [
		p
		for p in main_ui._coerce_piece_list(getattr(env, "action_queue", []))
		if bool(getattr(p, "is_alive", True))
	]
	if action_queue:
		setattr(env, "current_piece", action_queue[0])
		return action_queue[0]
	return None


def ui_action_handler(main_ui: Any, env: Any) -> ActionSet:
	"""运行时动作输入：严格按当前行动棋子 ID 消费 UI 提交动作。"""
	current_piece = main_ui._get_runtime_current_piece(env)
	if current_piece is None:
		return main_ui._noop_action_handler(env)

	piece_id = int(getattr(current_piece, "id", -1))
	if piece_id < 0:
		return main_ui._noop_action_handler(env)

	action = main_ui.pending_actions_by_piece_id.pop(piece_id, None)
	if action is None:
		return main_ui._noop_action_handler(env)
	return action


def queue_action_for_current_piece(main_ui: Any, action: ActionSet) -> bool:
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	if env is None:
		return False
	current_piece = main_ui._get_runtime_current_piece(env)
	if current_piece is None:
		return False
	piece_id = int(getattr(current_piece, "id", -1))
	if piece_id < 0:
		return False
	main_ui.pending_actions_by_piece_id[piece_id] = action
	return True


def attach_runtime_input(main_ui: Any) -> None:
	main_ui.controller.set_function_input_methods(main_ui._auto_init_handler, main_ui._ui_action_handler)


def initialize_runtime_environment_with_initiative_capture(main_ui: Any, env: Any, board_file: Optional[str]) -> None:
	"""捕获初始化阶段的先攻掷骰明细。"""
	main_ui.runtime_initiative_snapshot = []
	if env is None:
		return

	captured_rolls: list[int] = []
	original_roll = getattr(env, "roll_dice", None)
	wrapped = False

	if callable(original_roll):

		def _roll_proxy(n: int, sides: int):
			value = original_roll(n, sides)
			if int(n) == 1 and int(sides) == 20:
				captured_rolls.append(int(value))
			return value

		setattr(env, "roll_dice", _roll_proxy)
		wrapped = True

	try:
		env.initialize_environment(board_file=board_file)
	finally:
		if wrapped:
			setattr(env, "roll_dice", original_roll)

	roll_idx = 0
	snapshot: list[dict[str, Any]] = []
	for piece in main_ui._coerce_piece_list(getattr(getattr(env, "player1", None), "pieces", [])):
		roll_value = int(captured_rolls[roll_idx]) if roll_idx < len(captured_rolls) else 0
		roll_idx += 1
		attr_value = int(getattr(piece, "dexterity", 0))
		snapshot.append(
			{
				"piece": piece,
				"attr_name": "敏捷",
				"attr_value": attr_value,
				"roll": roll_value,
				"bonus": attr_value,
				"total": int(roll_value + attr_value),
			}
		)

	for piece in main_ui._coerce_piece_list(getattr(getattr(env, "player2", None), "pieces", None)):
		roll_value = int(captured_rolls[roll_idx]) if roll_idx < len(captured_rolls) else 0
		roll_idx += 1
		attr_value = int(getattr(piece, "dexterity", 0))
		snapshot.append(
			{
				"piece": piece,
				"attr_name": "敏捷",
				"attr_value": attr_value,
				"roll": roll_value,
				"bonus": attr_value,
				"total": int(roll_value + attr_value),
			}
		)

	main_ui.runtime_initiative_snapshot = snapshot
