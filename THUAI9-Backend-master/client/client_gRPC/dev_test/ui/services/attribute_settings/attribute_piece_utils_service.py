"""属性设置（piece 页）工具函数下沉。

本文件负责从 `main_ui.py` 下沉的“棋子属性页”相关杂项逻辑，主要包括：
- runtime/mock 槽位映射与槽位绑定（避免非连续槽位被重排）；
- 将 runtime/mock 数据转换为 piece 页每行的展示值；
- 属性输入的归一化与范围约束（含初始化窗口的特殊规则）；
- 坐标 clamp、落点可走性判断、边界线计算；
- 属性应用后的短提示（apply feedback）；
- safe_int/safe_float 等容错解析工具。
- 属性输入错误高亮（Entry 标红、hp placeholder 标红、槽位启用判断）。

约束：
- 不创建/布局 Tk 控件；
- 不 import main_ui（避免循环依赖）；
- 通过 duck-typing 使用 main_ui 的字段/方法，保持 UX/行为不变。
"""

from __future__ import annotations

from typing import Any


def clear_attribute_error_highlight(main_ui: Any) -> None:
	for slot_key, field_widgets in getattr(main_ui, "attribute_piece_entries", {}).items():
		_ = slot_key
		for field, widget in field_widgets.items():
			is_disabled = str(widget.cget("state")) == "disabled"
			try:
				if is_disabled:
					widget.configure(fg="#9ca3af")
				else:
					widget.configure(fg="#111111")
			except Exception:
				pass
			_ = field

	# 同步清理：自定义初始化的 hp placeholder（浮空“-”）颜色。
	for slot_key, widgets in getattr(main_ui, "attribute_piece_hp_hint_widgets", {}).items():
		_ = slot_key
		try:
			if isinstance(widgets, tuple) and len(widgets) == 4:
				_dash_label = widgets[2]
				_dash_label.configure(fg="#111111")
		except Exception:
			pass


def mark_hp_placeholder_error(main_ui: Any, slot_key: str) -> None:
	"""仅用于自定义初始化：将浮空 placeholder 的“-”标红。"""
	widgets = main_ui.attribute_piece_hp_hint_widgets.get(slot_key)
	if not widgets:
		return
	try:
		if isinstance(widgets, tuple) and len(widgets) == 4:
			entry, overlay, dash_label, _hint_label = widgets
			# 确保 placeholder 可见，否则标红看不到。
			try:
				overlay.place(in_=entry, x=4, y=1, relheight=1)
			except Exception:
				pass
			dash_label.configure(fg="#dc2626")
			return
		if isinstance(widgets, tuple) and len(widgets) == 2:
			dash_label, _hint_label = widgets
			dash_label.configure(fg="#dc2626")
	except Exception:
		pass


def mark_attribute_field_error(main_ui: Any, slot_key: str, field: str) -> None:
	entry = getattr(main_ui, "attribute_piece_entries", {}).get(slot_key, {}).get(field)
	if entry is None:
		return
	try:
		entry.configure(fg="#dc2626")
	except Exception:
		pass


def is_attribute_slot_enabled(main_ui: Any, slot_key: str) -> bool:
	field_widgets = getattr(main_ui, "attribute_piece_entries", {}).get(slot_key, {})
	entry = field_widgets.get("pos_x") or field_widgets.get("hp")
	if entry is None:
		return False
	return str(entry.cget("state")) != "disabled"


def on_attribute_var_changed(main_ui: Any, slot_key: str, field: str) -> None:
	"""属性变量 trace 回调。

	说明：该逻辑原本位于 `MainUI._on_attribute_var_changed`，这里下沉以保持 main_ui 薄委托。
	"""
	if getattr(main_ui, "attribute_internal_update", False):
		return

	if (
		field in ("hp", "strength")
		and bool(getattr(main_ui, "attribute_settings_force_init_mode", False))
		and main_ui._normalize_selected_source_value(getattr(main_ui, "selected_source", "")) == "runtime_custom"
	):
		main_ui._refresh_custom_init_hp_hint(slot_key)
		return

	if field in ("pos_x", "pos_y"):
		main_ui.attribute_edit_tick_counter = int(getattr(main_ui, "attribute_edit_tick_counter", 0)) + 1
		getattr(main_ui, "attribute_piece_last_edit_tick", {})[slot_key] = int(main_ui.attribute_edit_tick_counter)
		return

	if field in ("weapon", "armor"):
		main_ui._sync_profession_equipment(slot_key, field)
		return

	if (
		bool(main_ui._is_profession_mode())
		and bool(getattr(main_ui, "attribute_settings_force_init_mode", False))
		and field in ("strength", "dexterity", "intelligence")
	):
		main_ui._update_profession_display_and_presets(slot_key)
		return


def show_attribute_warning_feedback(main_ui: Any, message: str) -> None:
	"""在属性窗口下方显示 5 秒范围提示。"""
	label = getattr(main_ui, "attribute_piece_warning_label", None)
	if label is None:
		return
	label.configure(text=message, foreground="#b45309")
	job = getattr(main_ui, "attribute_piece_warning_job", None)
	if job is not None:
		try:
			main_ui.root.after_cancel(job)
		except Exception:
			pass
	main_ui.attribute_piece_warning_job = main_ui.root.after(5000, lambda: label.configure(text=""))


def runtime_init_incomplete_message(main_ui: Any) -> str:
	"""返回后端初始化未完成时的具体提示。"""
	team1_count = 0
	team2_count = 0
	for slot_key in main_ui._piece_slot_keys():
		vars_dict = main_ui.attribute_piece_vars.get(slot_key)
		if vars_dict is None:
			continue
		hp_raw = str(vars_dict.get("hp").get()).strip()
		if hp_raw in ("", "-", "-1"):
			continue
		if main_ui._safe_int(hp_raw, -1) <= 0:
			continue
		if int(slot_key[1]) == 1:
			team1_count += 1
		else:
			team2_count += 1

	if team1_count == 0 and team2_count == 0:
		return "当前场上未有有效棋子！"
	if team1_count == 0:
		return "当前场上未有有效棋子！player1阵营未设置棋子"
	if team2_count == 0:
		return "当前场上未有有效棋子！player2阵营未设置棋子"
	return "当前场上未有有效棋子！请先完成属性配置并应用"


def piece_slot_keys(_main_ui: Any) -> list[str]:
	return [f"p{team}_{idx}" for team in (1, 2) for idx in (1, 2, 3)]


def coerce_piece_list(_main_ui: Any, pieces_obj: Any) -> list[Any]:
	if isinstance(pieces_obj, list):
		return pieces_obj
	if isinstance(pieces_obj, tuple):
		return list(pieces_obj)
	if pieces_obj is None or isinstance(pieces_obj, (str, bytes, dict)):
		return []
	try:
		return list(pieces_obj)
	except Exception:
		return []


def runtime_piece_slot_map(main_ui: Any) -> dict[str, Any]:
	result: dict[str, Any] = {}
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	if env is None:
		return result
	if main_ui.runtime_piece_init_config and not main_ui.runtime_piece_slot_binding:
		main_ui._capture_runtime_piece_slot_binding_from_init_config()

	for team_id, player_attr in ((1, "player1"), (2, "player2")):
		player = getattr(env, player_attr, None)
		pieces = main_ui._coerce_piece_list(getattr(player, "pieces", None) if player is not None else None)
		if not pieces:
			continue
		sorted_pieces = sorted(pieces, key=lambda p: int(getattr(p, "id", 0)))
		used_slots: set[str] = set()

		for piece in sorted_pieces:
			slot_key = main_ui.runtime_piece_slot_binding.get(id(piece), "")
			if not slot_key.startswith(f"p{team_id}_"):
				continue
			if slot_key in used_slots:
				continue
			result[slot_key] = piece
			used_slots.add(slot_key)

		fallback_slots = [f"p{team_id}_{idx}" for idx in (1, 2, 3) if f"p{team_id}_{idx}" not in used_slots]
		fallback_idx = 0
		for piece in sorted_pieces:
			bound_slot = main_ui.runtime_piece_slot_binding.get(id(piece), "")
			if bound_slot in used_slots:
				continue
			if fallback_idx >= len(fallback_slots):
				break
			slot_key = fallback_slots[fallback_idx]
			fallback_idx += 1
			result[slot_key] = piece
			used_slots.add(slot_key)
	return result


def capture_runtime_piece_slot_binding_from_init_config(main_ui: Any) -> None:
	"""按初始化配置建立棋子与槽位的一次性绑定，避免非连续槽位被重排。"""
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	if env is None:
		return

	new_binding: dict[int, str] = {}
	for team_id, player_attr in ((1, "player1"), (2, "player2")):
		player = getattr(env, player_attr, None)
		pieces = main_ui._coerce_piece_list(getattr(player, "pieces", None) if player is not None else None)
		if not pieces:
			continue

		expected_slots: list[tuple[str, int, int]] = []
		for idx in (1, 2, 3):
			slot_key = f"p{team_id}_{idx}"
			cfg = main_ui.runtime_piece_init_config.get(slot_key, {})
			if main_ui._is_profession_mode():
				if not main_ui._is_profession_slot_active_from_cfg(cfg):
					continue
			else:
				hp_raw = str(cfg.get("hp", "-")).strip()
				if hp_raw in ("", "-", "-1") or main_ui._safe_int(hp_raw, -1) <= 0:
					continue
			x = main_ui._safe_int(str(cfg.get("pos_x", 0)), 0)
			y = main_ui._safe_int(str(cfg.get("pos_y", 0)), 0)
			expected_slots.append((slot_key, x, y))

		remaining_pieces = list(pieces)
		used_slots: set[str] = set()

		for slot_key, x, y in expected_slots:
			matched_piece = next(
				(
					piece
					for piece in remaining_pieces
					if int(getattr(getattr(piece, "position", None), "x", -9999)) == x
					and int(getattr(getattr(piece, "position", None), "y", -9999)) == y
				),
				None,
			)
			if matched_piece is None:
				continue
			new_binding[id(matched_piece)] = slot_key
			used_slots.add(slot_key)
			remaining_pieces.remove(matched_piece)

		remaining_slots = [slot for slot, _x, _y in expected_slots if slot not in used_slots]
		remaining_pieces.sort(key=lambda p: int(getattr(p, "id", 0)))
		for slot_key, piece in zip(remaining_slots, remaining_pieces):
			new_binding[id(piece)] = slot_key

	main_ui.runtime_piece_slot_binding = new_binding


def mock_piece_slot_map(main_ui: Any) -> dict[str, int]:
	result: dict[str, int] = {}
	for soldier_id, state in main_ui.mock_initial_positions.items():
		team = int(state.get("team", 1))
		piece_no = int(main_ui.mock_piece_number_by_id.get(soldier_id, 0))
		if team not in (1, 2) or piece_no not in (1, 2, 3):
			continue
		result[f"p{team}_{piece_no}"] = int(soldier_id)
	return result


def get_piece_row_values(main_ui: Any, slot_key: str, runtime_map: dict[str, Any], mock_map: dict[str, int]) -> dict[str, str]:
	if main_ui.attribute_settings_force_init_mode and main_ui._is_runtime_selected_source():
		fixed_positions: dict[str, tuple[int, int]] = {
			"p1_1": (3, 8),
			"p1_2": (8, 3),
			"p1_3": (17, 4),
			"p2_1": (16, 11),
			"p2_2": (11, 16),
			"p2_3": (2, 15),
		}
		px, py = fixed_positions.get(slot_key, (0, 0))
		px, py = main_ui._clamp_piece_position(px, py)
		if main_ui._is_profession_mode():
			default_cfg = {
				"hp": "-",
				"profession": "战士(长)",
				"weapon": "长剑",
				"armor": "轻甲",
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
				"pos_x": str(px),
				"pos_y": str(py),
			}
		else:
			default_cfg = {
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
				"pos_x": str(px),
				"pos_y": str(py),
			}
		cfg = main_ui.runtime_piece_init_config.get(slot_key, {})
		for key, val in cfg.items():
			default_cfg[key] = str(val)
		return default_cfg

	default_values = {
		"hp": "0",
		"profession": "自定义",
		"weapon": "自定义",
		"armor": "无甲",
		"strength": "0",
		"dexterity": "0",
		"intelligence": "0",
		"physical_resist": "0",
		"magic_resist": "0",
		"physical_damage": "0",
		"magic_damage": "0",
		"action_points": "0",
		"max_action_points": "0",
		"spell_slots": "0",
		"max_spell_slots": "0",
		"movement": "0",
		"pos_x": "0",
		"pos_y": "0",
	}
	if main_ui.controller.runtime_source == "runtime_env":
		piece = runtime_map.get(slot_key)
		if piece is None:
			return default_values
		pos = getattr(piece, "position", None)
		px = int(getattr(pos, "x", 0)) if pos is not None else 0
		py = int(getattr(pos, "y", 0)) if pos is not None else 0
		weapon_raw = getattr(piece, "weapon", "自定义")
		weapon_id = main_ui._safe_int(str(weapon_raw), 0)
		if weapon_id in (1, 2, 3, 4):
			weapon_label = main_ui._weapon_id_to_weapon_label(weapon_id)
		else:
			weapon_label = main_ui._normalize_weapon_label(str(weapon_raw)) or "自定义"
			weapon_id = main_ui._weapon_label_to_weapon_id(weapon_label)

		armor_raw = getattr(piece, "armor", "无甲")
		armor_id = main_ui._safe_int(str(armor_raw), 0)
		if armor_id in (1, 2, 3):
			armor_label = main_ui._armor_id_to_armor_label(armor_id)
		else:
			armor_label = str(armor_raw or "无甲")
			armor_id = main_ui._armor_label_to_armor_id(armor_label)

		profession_label = main_ui._weapon_id_to_profession_display(weapon_id)
		return {
			"hp": str(int(getattr(piece, "health", 0))),
			"profession": profession_label,
			"weapon": weapon_label,
			"armor": armor_label,
			"strength": str(int(getattr(piece, "strength", 0))),
			"dexterity": str(int(getattr(piece, "dexterity", 0))),
			"intelligence": str(int(getattr(piece, "intelligence", 0))),
			"physical_resist": str(int(getattr(piece, "physical_resist", 0))),
			"magic_resist": str(int(getattr(piece, "magic_resist", 0))),
			"physical_damage": str(int(getattr(piece, "physical_damage", 0))),
			"magic_damage": str(int(getattr(piece, "magic_damage", 0))),
			"action_points": str(int(getattr(piece, "action_points", 0))),
			"max_action_points": str(int(getattr(piece, "max_action_points", 0))),
			"spell_slots": str(int(getattr(piece, "spell_slots", 0))),
			"max_spell_slots": str(int(getattr(piece, "max_spell_slots", 0))),
			"movement": str(float(getattr(piece, "movement", 0.0))),
			"pos_x": str(px),
			"pos_y": str(py),
		}

	soldier_id = mock_map.get(slot_key)
	if soldier_id is None:
		return default_values
	stats = main_ui.mock_piece_stats_by_id.get(soldier_id, {})
	weapon_label = main_ui._normalize_weapon_label(str(stats.get("weapon", "自定义"))) or "自定义"
	weapon_id = main_ui._weapon_label_to_weapon_id(weapon_label)
	armor_label = str(stats.get("armor", "无甲")) or "无甲"
	profession_label = main_ui._weapon_id_to_profession_display(weapon_id)
	return {
		"hp": str(int(main_ui.mock_last_health_by_id.get(soldier_id, stats.get("health", 0)))),
		"profession": profession_label,
		"weapon": weapon_label,
		"armor": armor_label,
		"strength": str(int(stats.get("strength", 0))),
		"dexterity": str(int(stats.get("dexterity", 0))),
		"intelligence": str(int(stats.get("intelligence", 0))),
		"physical_resist": str(int(stats.get("physical_resist", 0))),
		"magic_resist": str(int(stats.get("magic_resist", 0))),
		"physical_damage": str(int(stats.get("physical_damage", 0))),
		"magic_damage": str(int(stats.get("magic_damage", 0))),
		"action_points": str(int(stats.get("action_points", 0))),
		"max_action_points": str(int(stats.get("max_action_points", 0))),
		"spell_slots": str(int(stats.get("spell_slots", 0))),
		"max_spell_slots": str(int(stats.get("max_spell_slots", 0))),
		"movement": str(float(stats.get("movement", 0.0))),
		"pos_x": str(int(main_ui.mock_initial_positions.get(soldier_id, {}).get("x", 0))),
		"pos_y": str(int(main_ui.mock_initial_positions.get(soldier_id, {}).get("y", 0))),
	}


def piece_attr_range(_main_ui: Any, field: str) -> tuple[float, float]:
	ranges: dict[str, tuple[float, float]] = {
		"hp": (0, 200),
		"strength": (0, 30),
		"dexterity": (0, 30),
		"intelligence": (0, 30),
		"physical_resist": (0, 50),
		"magic_resist": (0, 50),
		"physical_damage": (0, 100),
		"magic_damage": (0, 100),
		"action_points": (0, 10),
		"max_action_points": (0, 10),
		"spell_slots": (0, 20),
		"max_spell_slots": (0, 20),
		"movement": (0, 40),
	}
	return ranges.get(field, (0, 9999))


def normalize_piece_value(
	main_ui: Any,
	*,
	slot_display_name: str,
	field: str,
	raw_value: str,
	allow_unset_hp: bool,
) -> tuple[str, str | None]:
	value = str(raw_value).strip()
	field_labels = {
		"hp": "血量",
		"strength": "力量",
		"dexterity": "敏捷",
		"intelligence": "智力",
		"physical_resist": "物抗",
		"magic_resist": "法抗",
		"physical_damage": "物伤",
		"magic_damage": "法伤",
		"action_points": "行动位",
		"max_action_points": "行动位上限",
		"spell_slots": "法术位",
		"max_spell_slots": "法术位上限",
		"movement": "移动力",
		"pos_x": "X坐标",
		"pos_y": "Y坐标",
	}
	if field == "hp" and allow_unset_hp and value in ("", "-", "-1"):
		return "", None
	if field == "hp" and allow_unset_hp:
		# 初始化窗口：不自动修正到边界值，保留原始输入，让应用时可以标红并给出简要提示。
		_ = value
		return value, None

	if field in ("movement",):
		parsed = main_ui._safe_float(value, -99999.0)
		lo, hi = main_ui._piece_attr_range(field)
		clamped = max(lo, min(parsed, hi))
		out_str = f"{clamped:.1f}".rstrip("0").rstrip(".")
		if parsed != clamped:
			return out_str, f"{slot_display_name}的{field_labels.get(field, field)}合理范围是{int(lo)}-{int(hi)}"
		return out_str, None

	if field in ("pos_x", "pos_y"):
		parsed_i = main_ui._safe_int(value, -99999)
		if main_ui.controller.runtime_source == "runtime_env" and main_ui.controller.environment is not None:
			board = getattr(main_ui.controller.environment, "board", None)
			if board is not None:
				max_x = max(0, int(getattr(board, "width", 1)) - 1)
				max_y = max(0, int(getattr(board, "height", 1)) - 1)
			else:
				max_x, max_y = 19, 19
		else:
			max_x, max_y = 19, 19
		max_v = max_x if field == "pos_x" else max_y
		clamped_i = max(0, min(parsed_i, max_v))
		if parsed_i != clamped_i:
			return str(clamped_i), f"{slot_display_name}的{field_labels.get(field, field)}合理范围是0-{max_v}"
		return str(clamped_i), None

	parsed_i = main_ui._safe_int(value, -99999)
	lo, hi = main_ui._piece_attr_range(field)
	clamped_i = int(max(lo, min(parsed_i, hi)))
	if parsed_i != clamped_i:
		return str(clamped_i), f"{slot_display_name}的{field_labels.get(field, field)}合理范围是{int(lo)}-{int(hi)}"
	return str(clamped_i), None


def is_walkable_for_piece(main_ui: Any, x: int, y: int) -> bool:
	if main_ui.controller.runtime_source == "runtime_env" and main_ui.controller.environment is not None:
		board = getattr(main_ui.controller.environment, "board", None)
		if board is None:
			return False
		width = int(getattr(board, "width", 0))
		height = int(getattr(board, "height", 0))
		if not (0 <= x < width and 0 <= y < height):
			return False
		height_map = getattr(board, "height_map", None)
		if height_map is None:
			return False
		try:
			if int(height_map[x][y]) == -1:
				return False
		except Exception:
			return False
		# 注：部分地图/实现可能会使用 state=0 表示“空地”，但仍可作为落点。
		# 这里对属性编辑放宽：只要不是禁止格(state=-1)且高度不为-1即可。
		cell = board.grid[x][y]
		return int(getattr(cell, "state", 0)) != -1

	game_data = main_ui.controller.game_data
	if not isinstance(game_data, dict):
		return False
	board = game_data.get("map", {})
	rows = board.get("rows", []) if isinstance(board, dict) else []
	if not isinstance(rows, list) or not rows:
		return False
	if y < 0 or y >= len(rows):
		return False
	row = rows[y]
	if not isinstance(row, list) or x < 0 or x >= len(row):
		return False
	visual_rows = main_ui._extract_mock_visual_rows()
	if y < 0 or y >= len(visual_rows):
		return False
	visual_row = visual_rows[y]
	if not isinstance(visual_row, list) or x < 0 or x >= len(visual_row):
		return False
	return int(visual_row[x]) != -1


def runtime_border_line(main_ui: Any) -> int:
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	if env is not None and getattr(env, "board", None) is not None:
		return int(getattr(env.board, "boarder", 0))
	return 10


def clamp_piece_position(main_ui: Any, x: int, y: int) -> tuple[int, int]:
	"""将坐标限制在当前地图范围内。"""
	width = 20
	height = 20
	if main_ui.controller.runtime_source == "runtime_env" and main_ui.controller.environment is not None:
		board = getattr(main_ui.controller.environment, "board", None)
		if board is not None:
			width = int(getattr(board, "width", width))
			height = int(getattr(board, "height", height))
	else:
		game_data = main_ui.controller.game_data
		if isinstance(game_data, dict):
			board = game_data.get("map", {})
			rows = board.get("rows", []) if isinstance(board, dict) else []
			if isinstance(rows, list) and rows:
				height = len(rows)
				first_row = rows[0]
				if isinstance(first_row, list) and first_row:
					width = len(first_row)

	cx = max(0, min(int(x), max(0, width - 1)))
	cy = max(0, min(int(y), max(0, height - 1)))
	return cx, cy


def show_attribute_apply_feedback(main_ui: Any, message: str) -> None:
	label = getattr(main_ui, "attribute_piece_apply_status_label", None)
	if label is None:
		return
	label.configure(text=message, foreground="#059669")
	job = getattr(main_ui, "attribute_piece_apply_status_job", None)
	if job is not None:
		try:
			main_ui.root.after_cancel(job)
		except Exception:
			pass

	def _clear_if_exists() -> None:
		try:
			if label is not None and bool(label.winfo_exists()):
				label.configure(text="")
		except Exception:
			pass

	main_ui.attribute_piece_apply_status_job = main_ui.root.after(2000, _clear_if_exists)


def safe_int(_main_ui: Any, value: str, default: int = 0) -> int:
	try:
		return int(float(value))
	except Exception:
		return default


def safe_float(_main_ui: Any, value: str, default: float = 0.0) -> float:
	try:
		return float(value)
	except Exception:
		return default
