"""棋盘渲染/覆盖层计算相关的 service。

边界：
- 只负责把 `MainUI` 中与棋盘刷新相关的计算与调用下沉；
- 不改变既有 UI 行为与视觉表现；
- 仍通过 `main_ui` 访问其状态、变量与其它委托方法（duck-typing）。

用法：
- `main_ui._refresh_board_view()` 等薄委托转调到本模块。
"""

from __future__ import annotations

from typing import Any


def refresh_board_view(main_ui: Any) -> None:
	"""刷新棋盘底图和棋子位置。"""
	# 地图属性选点时，棋盘点击由透明覆盖层接管。
	# 为避免行动面板残留的“移动目标/火球 AOE”干扰地图编辑，这里暂时屏蔽行动预览绘制。
	if getattr(main_ui, "attribute_map_pick_waiting", False):
		move_target = None
		spell_overlay = ([], "#f97316")
		target_markers: list[dict[str, Any]] = []
	else:
		move_target = get_move_target_highlight(main_ui)
		spell_overlay = build_spell_aoe_overlay(main_ui)
		target_markers = build_target_markers_for_board(main_ui)
	trap_markers = build_runtime_trap_markers(main_ui)

	controller = getattr(main_ui, "controller", None)
	if getattr(controller, "runtime_source", None) == "runtime_env" and getattr(controller, "environment", None) is not None:
		env = controller.environment
		map_rows = main_ui._extract_runtime_map_rows()
		pieces = main_ui._extract_runtime_pieces()
		main_ui.left_board_panel.set_board_state(map_rows, pieces)
		main_ui.left_board_panel.set_move_target_highlight(move_target)
		main_ui.left_board_panel.set_spell_aoe_overlay(spell_overlay[0], spell_overlay[1])
		main_ui.left_board_panel.set_trap_markers(trap_markers)
		# 🎯 目标标记（只在可执行的锁定行动下展示）
		if hasattr(main_ui.left_board_panel, "set_target_markers"):
			main_ui.left_board_panel.set_target_markers(target_markers)
		# 让 😇 角标能按时消失。
		try:
			main_ui._schedule_runtime_angel_refresh(env)
		except Exception:
			pass
		return

	game_data = getattr(controller, "game_data", None)
	if not isinstance(game_data, dict):
		main_ui.left_board_panel.set_board_state([], [])
		return

	map_rows = main_ui._extract_mock_visual_rows()
	pieces = main_ui._build_mock_pieces_for_current_round()
	main_ui.left_board_panel.set_board_state(map_rows if isinstance(map_rows, list) else [], pieces)
	main_ui.left_board_panel.set_move_target_highlight(move_target)
	main_ui.left_board_panel.set_spell_aoe_overlay([], "#f97316")
	main_ui.left_board_panel.set_trap_markers([])
	if hasattr(main_ui.left_board_panel, "set_target_markers"):
		main_ui.left_board_panel.set_target_markers([])


def build_target_markers_for_board(main_ui: Any) -> list[dict[str, Any]]:
	"""根据当前行动面板状态，判断是否应对目标棋子绘制🎯。"""
	controller = getattr(main_ui, "controller", None)
	if getattr(controller, "runtime_source", None) != "runtime_env":
		return []
	env = getattr(controller, "environment", None)
	if env is None:
		return []
	mode = main_ui.action_ui_mode.get().strip().lower()
	if mode not in ("attack", "spell"):
		return []

	actor = main_ui._get_runtime_current_piece(env)
	if actor is None:
		return []
	# 资源：攻击仅看 AP；法术额外看 SP。
	ap = int(getattr(actor, "action_points", 0))
	if ap <= 0:
		return []

	# 攻击：锁定目标+范围判定。
	if mode == "attack":
		target_label = main_ui.action_attack_target_var.get().strip()
		target_piece = main_ui._resolve_action_target_piece(target_label)
		if target_piece is None:
			return []
		try:
			if not bool(env.is_in_attack_range(actor, target_piece)):
				return []
		except Exception:
			# 若后端环境不支持该判断，则不绘制（避免误导）。
			return []

		pos = getattr(target_piece, "position", None)
		x = int(getattr(pos, "x", -1)) if pos is not None else -1
		y = int(getattr(pos, "y", -1)) if pos is not None else -1
		if x < 0 or y < 0:
			return []
		return [{"x": x, "y": y, "text": "🎯"}]

	# 法术：仅对“锁定法术”显示，且需满足 AP/SP 与射程。
	spell = main_ui._resolve_selected_spell()
	if spell is None:
		return []
	if main_ui._is_teleport_spell(spell) or main_ui._is_trap_spell(spell):
		return []
	is_locking = bool(getattr(spell, "is_locking_spell", False))
	if not is_locking:
		return []
	sp = int(getattr(actor, "spell_slots", 0))
	spell_cost = int(getattr(spell, "spell_cost", 1))
	if sp < spell_cost:
		return []

	target_text = main_ui.action_spell_target_var.get().strip()
	target_piece = main_ui._resolve_spell_target_piece(target_text, spell, actor)
	if target_piece is None:
		return []
	actor_pos = getattr(actor, "position", None)
	target_pos = getattr(target_piece, "position", None)
	ax = int(getattr(actor_pos, "x", -1)) if actor_pos is not None else -1
	ay = int(getattr(actor_pos, "y", -1)) if actor_pos is not None else -1
	tx = int(getattr(target_pos, "x", -1)) if target_pos is not None else -1
	ty = int(getattr(target_pos, "y", -1)) if target_pos is not None else -1
	if ax < 0 or ay < 0 or tx < 0 or ty < 0:
		return []
	spell_range = float(getattr(spell, "range", 0.0))
	distance = ((ax - tx) ** 2 + (ay - ty) ** 2) ** 0.5
	if distance > spell_range:
		return []
	return [{"x": tx, "y": ty, "text": "🎯"}]


def build_runtime_trap_markers(main_ui: Any) -> list[dict[str, Any]]:
	markers: list[dict[str, Any]] = []
	for trap in getattr(main_ui, "runtime_trap_effects", []) or []:
		remaining = int(trap.get("remaining", 0))
		if remaining <= 0:
			continue
		markers.append(
			{
				"x": int(trap.get("x", -1)),
				"y": int(trap.get("y", -1)),
				"remaining": remaining,
			}
		)
	return markers


def spell_preview_color(main_ui: Any, spell: Any) -> str:
	name = str(getattr(spell, "name", "")).strip().lower()
	effect_key = main_ui._spell_effect_key(spell)
	if "fire" in name or "火" in name:
		return "#fb7185"
	if effect_key == "heal":
		return "#34d399"
	if effect_key == "move":
		return "#60a5fa"
	if effect_key in ("debuff", "damage"):
		return "#f97316"
	return "#f59e0b"


def build_spell_aoe_overlay(main_ui: Any) -> tuple[list[tuple[int, int]], str]:
	controller = getattr(main_ui, "controller", None)
	env = getattr(controller, "environment", None)
	if getattr(controller, "runtime_source", None) != "runtime_env" or env is None:
		return [], "#f97316"
	if main_ui.action_ui_mode.get().strip().lower() != "spell":
		return [], "#f97316"
	spell = main_ui._resolve_selected_spell()
	if spell is None:
		return [], "#f97316"
	if main_ui._is_teleport_spell(spell):
		return [], spell_preview_color(main_ui, spell)
	if bool(getattr(spell, "is_locking_spell", False)):
		return [], spell_preview_color(main_ui, spell)
	try:
		center_x = int(main_ui.action_spell_point_x_var.get().strip())
		center_y = int(main_ui.action_spell_point_y_var.get().strip())
	except Exception:
		return [], spell_preview_color(main_ui, spell)
	board = getattr(env, "board", None)
	width = int(getattr(board, "width", 0)) if board is not None else 0
	height = int(getattr(board, "height", 0)) if board is not None else 0
	if width <= 0 or height <= 0:
		return [], spell_preview_color(main_ui, spell)
	radius = max(0, int(getattr(spell, "area_radius", 0)))
	cells: list[tuple[int, int]] = []
	for x in range(width):
		for y in range(height):
			if (x - center_x) ** 2 + (y - center_y) ** 2 <= radius ** 2:
				cells.append((x, y))
	return cells, spell_preview_color(main_ui, spell)


def get_move_target_highlight(main_ui: Any) -> tuple[int, int] | None:
	"""返回需要在棋盘高亮的目标格（移动或法术）。"""
	controller = getattr(main_ui, "controller", None)
	env = getattr(controller, "environment", None)
	if getattr(controller, "runtime_source", None) != "runtime_env" or env is None:
		return None

	mode = main_ui.action_ui_mode.get().strip().lower()
	if mode == "spell":
		selected_spell = main_ui._resolve_selected_spell()
		if selected_spell is None:
			return None
		is_locking_spell = bool(getattr(selected_spell, "is_locking_spell", False)) and not main_ui._is_teleport_spell(selected_spell)
		if is_locking_spell:
			target_text = main_ui.action_spell_target_var.get().strip()
			target_piece = main_ui._resolve_spell_target_piece(target_text, selected_spell, main_ui._get_runtime_current_piece(env))
			if target_piece is None:
				return None
			pos = getattr(target_piece, "position", None)
			tx = int(getattr(pos, "x", -1)) if pos is not None else -1
			ty = int(getattr(pos, "y", -1)) if pos is not None else -1
			return (tx, ty) if tx >= 0 and ty >= 0 else None
		try:
			target_x = int(main_ui.action_spell_point_x_var.get().strip())
			target_y = int(main_ui.action_spell_point_y_var.get().strip())
		except Exception:
			return None
		board = getattr(env, "board", None)
		width = int(getattr(board, "width", 0)) if board is not None else 0
		height = int(getattr(board, "height", 0)) if board is not None else 0
		if 0 <= target_x < width and 0 <= target_y < height:
			return (target_x, target_y)
		return None

	if mode != "move":
		return None
	try:
		target_x = int(main_ui.action_move_x_var.get().strip())
		target_y = int(main_ui.action_move_y_var.get().strip())
	except Exception:
		return None
	board = getattr(env, "board", None)
	width = int(getattr(board, "width", 0)) if board is not None else 0
	height = int(getattr(board, "height", 0)) if board is not None else 0
	if not (0 <= target_x < width and 0 <= target_y < height):
		return None
	piece = main_ui._get_runtime_current_piece(env)
	if piece is None:
		return None
	pos = getattr(piece, "position", None)
	curr_x = int(getattr(pos, "x", -1)) if pos is not None else -1
	curr_y = int(getattr(pos, "y", -1)) if pos is not None else -1
	if (target_x, target_y) == (curr_x, curr_y):
		return None
	return (target_x, target_y)
