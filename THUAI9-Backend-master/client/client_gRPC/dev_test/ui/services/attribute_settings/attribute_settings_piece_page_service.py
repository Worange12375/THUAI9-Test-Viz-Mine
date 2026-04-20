"""属性设置窗口：棋子属性页（piece）。

本文件负责：
- “棋子属性”页 UI 构建（6 槽位矩阵表格 + 纵向滚动）。
- 将页面输入应用到运行时棋子 / mock 数据（本局内存生效）。

阶段说明：
- Phase 3：MainUI 拆分进行中；以“搬家不改逻辑”为原则，接收 `main_ui` 实例并直接访问其字段/方法。
"""

from __future__ import annotations

from typing import Any

import tkinter as tk
from tkinter import ttk

from env import Point


def apply_piece_attribute_changes(main_ui: Any) -> None:
	if not main_ui.loaded:
		main_ui.right_info_panel.append_content("\n[UI] 当前未加载对局，无法应用棋子属性")
		if not (main_ui.attribute_settings_force_init_mode and main_ui._is_runtime_selected_source()):
			return

	runtime_map = main_ui._runtime_piece_slot_map()
	mock_map = main_ui._mock_piece_slot_map()
	applied_count = 0
	warnings: list[str] = []
	active_slots_by_team: dict[int, list[str]] = {1: [], 2: []}
	planned_positions: dict[str, tuple[int, int]] = {}
	allow_unset_hp = bool(main_ui.attribute_settings_force_init_mode and main_ui._is_runtime_selected_source())
	main_ui._clear_attribute_error_highlight()

	# 先做输入规范化（含范围夹紧）并回填到界面。
	main_ui.attribute_internal_update = True
	try:
		for slot_key in main_ui._piece_slot_keys():
			vars_dict = main_ui.attribute_piece_vars.get(slot_key)
			if vars_dict is None:
				continue
			if not main_ui.attribute_settings_force_init_mode and not main_ui._is_attribute_slot_enabled(slot_key):
				continue
			slot_name = f"player{slot_key[1]}-{slot_key[-1]}"
			slot_hp_raw = str(vars_dict["hp"].get()).strip()
			if allow_unset_hp and main_ui._is_profession_mode() and main_ui._is_runtime_selected_source():
				strength = main_ui._parse_talent_int(vars_dict.get("strength").get() if vars_dict.get("strength") else None)
				dexterity = main_ui._parse_talent_int(vars_dict.get("dexterity").get() if vars_dict.get("dexterity") else None)
				intelligence = main_ui._parse_talent_int(
					vars_dict.get("intelligence").get() if vars_dict.get("intelligence") else None
				)
				slot_unset = strength is None and dexterity is None and intelligence is None
			else:
				slot_unset = allow_unset_hp and slot_hp_raw in ("", "-", "-1")
			for field, var in vars_dict.items():
				if slot_unset and field != "hp":
					continue
				# 职业模式初始化：天赋/派生字段允许保持为“-”（未分配/未派生），不做整数夹紧。
				if (
					allow_unset_hp
					and main_ui._is_profession_mode()
					and main_ui._is_runtime_selected_source()
					and field not in ("profession", "weapon", "armor", "pos_x", "pos_y")
				):
					raw_norm = str(var.get()).strip()
					if raw_norm in ("", "-", "-1"):
						if var.get() != "-":
							var.set("-")
						continue
				if field in ("profession", "weapon", "armor"):
					normalized = str(var.get()).strip()
					if not normalized:
						if field == "armor":
							normalized = "无甲"
						else:
							normalized = "自定义"
					if var.get() != normalized:
						var.set(normalized)
					continue
				normalized, warn = main_ui._normalize_piece_value(
					slot_display_name=slot_name,
					field=field,
					raw_value=var.get(),
					allow_unset_hp=allow_unset_hp,
				)
				if var.get() != normalized:
					var.set(normalized)
				if warn is not None:
					warnings.append(warn)

		# 额外约束：当前行动位/法术位不能超过其上限。
		for slot_key in main_ui._piece_slot_keys():
			vars_dict = main_ui.attribute_piece_vars.get(slot_key)
			if vars_dict is None:
				continue
			if not main_ui.attribute_settings_force_init_mode and not main_ui._is_attribute_slot_enabled(slot_key):
				continue
			slot_hp_raw = str(vars_dict["hp"].get()).strip()
			if allow_unset_hp and main_ui._is_profession_mode() and main_ui._is_runtime_selected_source():
				strength = main_ui._parse_talent_int(vars_dict.get("strength").get() if vars_dict.get("strength") else None)
				dexterity = main_ui._parse_talent_int(vars_dict.get("dexterity").get() if vars_dict.get("dexterity") else None)
				intelligence = main_ui._parse_talent_int(
					vars_dict.get("intelligence").get() if vars_dict.get("intelligence") else None
				)
				slot_unset = strength is None and dexterity is None and intelligence is None
			else:
				slot_unset = allow_unset_hp and slot_hp_raw in ("", "-", "-1")
			if slot_unset:
				continue

			slot_name = f"player{slot_key[1]}-{slot_key[-1]}"
			action_max = main_ui._safe_int(vars_dict["max_action_points"].get(), 0)
			action_cur = main_ui._safe_int(vars_dict["action_points"].get(), 0)
			if action_cur > action_max:
				vars_dict["action_points"].set(str(action_max))
				warnings.append(f"{slot_name}的行动位不能超过行动位上限")

			spell_max = main_ui._safe_int(vars_dict["max_spell_slots"].get(), 0)
			spell_cur = main_ui._safe_int(vars_dict["spell_slots"].get(), 0)
			if spell_cur > spell_max:
				vars_dict["spell_slots"].set(str(spell_max))
				warnings.append(f"{slot_name}的法术位不能超过法术位上限")
	finally:
		main_ui.attribute_internal_update = False

	# 构建“有效棋子”集合，并检查坐标合法性（不可重叠、不可走）。
	invalid_coordinate_slots: list[tuple[str, str]] = []
	position_to_slots: dict[str, list[str]] = {}
	use_talent_validity = bool(
		main_ui._is_profession_mode()
		and main_ui.attribute_settings_force_init_mode
		and main_ui._is_runtime_selected_source()
	)
	talent_cap = main_ui._get_talent_total_cap() if use_talent_validity else 0
	for slot_key in main_ui._piece_slot_keys():
		vars_dict = main_ui.attribute_piece_vars.get(slot_key)
		if vars_dict is None:
			continue
		if not main_ui.attribute_settings_force_init_mode and not main_ui._is_attribute_slot_enabled(slot_key):
			continue
		if not main_ui.attribute_settings_force_init_mode:
			if main_ui.controller.runtime_source == "runtime_env" and slot_key not in runtime_map:
				continue
			if main_ui.controller.runtime_source != "runtime_env" and slot_key not in mock_map:
				continue
		team = int(slot_key[1])
		if use_talent_validity:
			strength = main_ui._parse_talent_int(vars_dict.get("strength").get() if vars_dict.get("strength") else None)
			dexterity = main_ui._parse_talent_int(vars_dict.get("dexterity").get() if vars_dict.get("dexterity") else None)
			intelligence = main_ui._parse_talent_int(
				vars_dict.get("intelligence").get() if vars_dict.get("intelligence") else None
			)
			if strength is None or dexterity is None or intelligence is None:
				continue
			if (strength + dexterity + intelligence) > int(talent_cap):
				main_ui._mark_attribute_field_error(slot_key, "strength")
				main_ui._mark_attribute_field_error(slot_key, "dexterity")
				main_ui._mark_attribute_field_error(slot_key, "intelligence")
				main_ui._show_attribute_warning_feedback(f"天赋总和不能超过 {int(talent_cap)}")
				return
		else:
			hp_raw = str(vars_dict["hp"].get()).strip()
			if hp_raw in ("", "-", "-1"):
				continue
			hp_value = main_ui._safe_int(hp_raw, -1)
			if hp_value < 0:
				slot_name = f"player{slot_key[1]}-{slot_key[-1]}"
				main_ui._mark_attribute_field_error(slot_key, "hp")
				main_ui._show_attribute_warning_feedback(f"{slot_name} 的血量不能小于 0")
				return
			if hp_value == 0:
				continue
			if (
				main_ui.attribute_settings_force_init_mode
				and main_ui._is_runtime_selected_source()
				and (not main_ui._is_profession_mode())
				and main_ui._normalize_selected_source_value(main_ui.selected_source) == "runtime_custom"
			):
				strength_raw = (
					str(vars_dict.get("strength").get()).strip() if vars_dict.get("strength") is not None else "10"
				)
				strength = main_ui._safe_int(strength_raw, 10)
				max_hp = int(200)
				if int(hp_value) > int(max_hp):
					slot_name = f"player{slot_key[1]}-{slot_key[-1]}"
					main_ui._mark_attribute_field_error(slot_key, "hp")
					main_ui._show_attribute_warning_feedback(f"{slot_name} 的血量不能超过上限 ({max_hp})")
					return

		x = main_ui._safe_int(vars_dict["pos_x"].get(), -1)
		y = main_ui._safe_int(vars_dict["pos_y"].get(), -1)
		if not main_ui._is_walkable_for_piece(x, y):
			invalid_coordinate_slots.append((slot_key, "walkable"))
			continue

		pos_key = f"{x},{y}"
		position_to_slots.setdefault(pos_key, []).append(slot_key)
		planned_positions[pos_key] = (x, y)
		active_slots_by_team[team].append(slot_key)

	for pos_key, slots in position_to_slots.items():
		if len(slots) <= 1:
			continue
		sorted_slots = sorted(slots, key=lambda s: int(main_ui.attribute_piece_last_edit_tick.get(s, 0)))
		for duplicate_slot in sorted_slots[1:]:
			invalid_coordinate_slots.append((duplicate_slot, "duplicate"))

	if invalid_coordinate_slots:
		for slot_key, _reason in invalid_coordinate_slots:
			main_ui._mark_attribute_field_error(slot_key, "pos_x")
			main_ui._mark_attribute_field_error(slot_key, "pos_y")
		main_ui._show_attribute_warning_feedback("存在非法坐标（重合/越界/不可走），请修改红色坐标")
		return

	team1_count = len(active_slots_by_team[1])
	team2_count = len(active_slots_by_team[2])

	# 后端强制初始化：必须双方至少各有一个有效棋子。
	if main_ui.attribute_settings_force_init_mode and main_ui._is_runtime_selected_source():
		if team1_count == 0 and team2_count == 0:
			if use_talent_validity:
				for field in ("strength", "dexterity", "intelligence"):
					main_ui._mark_attribute_field_error("p1_1", field)
					main_ui._mark_attribute_field_error("p2_1", field)
				main_ui._show_attribute_warning_feedback(
					f"当前场上未有有效棋子！请为双方至少各一个棋子分配天赋（力量/敏捷/智力，且总和≤{int(talent_cap)}）"
				)
				return
			for sk in ("p1_1", "p2_1"):
				vars_dict = main_ui.attribute_piece_vars.get(sk) or {}
				hp_raw = str(vars_dict.get("hp").get()).strip() if vars_dict.get("hp") is not None else ""
				if hp_raw in ("", "-", "-1"):
					main_ui._mark_hp_placeholder_error(sk)
				else:
					main_ui._mark_attribute_field_error(sk, "hp")
			main_ui._show_attribute_warning_feedback("当前场上未有有效棋子！请设置双方至少各一个棋子的血量")
			return

	# 职业模式：有效棋子必须选择非“自定义”职业。
	if main_ui._is_profession_mode():
		invalid_slots: list[str] = []
		for team_id in (1, 2):
			for slot_key in active_slots_by_team[team_id]:
				vars_dict = main_ui.attribute_piece_vars.get(slot_key)
				if vars_dict is None:
					continue
				prof_var = vars_dict.get("profession")
				profession = str(prof_var.get()).strip() if prof_var is not None else ""
				if profession in ("", "自定义"):
					invalid_slots.append(slot_key)
		if invalid_slots:
			for slot_key in invalid_slots:
				main_ui._mark_attribute_field_error(slot_key, "profession")
			main_ui._show_attribute_warning_feedback("职业模式：有效棋子必须选择武器以确定职业，职业不能为自定义")
			return
		if team1_count == 0:
			if use_talent_validity:
				for field in ("strength", "dexterity", "intelligence"):
					main_ui._mark_attribute_field_error("p1_1", field)
				main_ui._show_attribute_warning_feedback("player1阵营未设置有效棋子，请先分配天赋（力量/敏捷/智力）")
				return
			main_ui._mark_attribute_field_error("p1_1", "hp")
			main_ui._show_attribute_warning_feedback("player1阵营未设置有效棋子，请先设置血量")
			return
		if team2_count == 0:
			if use_talent_validity:
				for field in ("strength", "dexterity", "intelligence"):
					main_ui._mark_attribute_field_error("p2_1", field)
				main_ui._show_attribute_warning_feedback("player2阵营未设置有效棋子，请先分配天赋（力量/敏捷/智力）")
				return
			main_ui._mark_attribute_field_error("p2_1", "hp")
			main_ui._show_attribute_warning_feedback("player2阵营未设置有效棋子，请先设置血量")
			return

	for slot_key in main_ui._piece_slot_keys():
		vars_dict = main_ui.attribute_piece_vars.get(slot_key)
		if vars_dict is None:
			continue

		if main_ui.attribute_settings_force_init_mode and main_ui._is_runtime_selected_source():
			cfg = main_ui.runtime_piece_init_config.setdefault(slot_key, {})
			for field, var in vars_dict.items():
				cfg[field] = var.get()
			applied_count += 1
			continue

		if main_ui.controller.runtime_source == "runtime_env":
			piece = runtime_map.get(slot_key)
			if piece is None:
				continue
			px, py = main_ui._clamp_piece_position(
				main_ui._safe_int(vars_dict["pos_x"].get(), 0),
				main_ui._safe_int(vars_dict["pos_y"].get(), 0),
			)
			piece.health = max(0, main_ui._safe_int(vars_dict["hp"].get(), int(getattr(piece, "health", 0))))
			piece.is_alive = bool(int(getattr(piece, "health", 0)) > 0)
			piece.strength = main_ui._safe_int(vars_dict["strength"].get(), int(getattr(piece, "strength", 0)))
			piece.dexterity = main_ui._safe_int(vars_dict["dexterity"].get(), int(getattr(piece, "dexterity", 0)))
			piece.intelligence = main_ui._safe_int(
				vars_dict["intelligence"].get(), int(getattr(piece, "intelligence", 0))
			)
			piece.physical_resist = main_ui._safe_int(
				vars_dict["physical_resist"].get(), int(getattr(piece, "physical_resist", 0))
			)
			piece.magic_resist = main_ui._safe_int(vars_dict["magic_resist"].get(), int(getattr(piece, "magic_resist", 0)))
			piece.physical_damage = main_ui._safe_int(
				vars_dict["physical_damage"].get(), int(getattr(piece, "physical_damage", 0))
			)
			piece.magic_damage = main_ui._safe_int(vars_dict["magic_damage"].get(), int(getattr(piece, "magic_damage", 0)))
			piece.max_action_points = main_ui._safe_int(
				vars_dict["max_action_points"].get(), int(getattr(piece, "max_action_points", 0))
			)
			piece.action_points = min(
				main_ui._safe_int(vars_dict["action_points"].get(), int(getattr(piece, "action_points", 0))),
				int(piece.max_action_points),
			)
			piece.max_spell_slots = main_ui._safe_int(
				vars_dict["max_spell_slots"].get(), int(getattr(piece, "max_spell_slots", 0))
			)
			piece.spell_slots = min(
				main_ui._safe_int(vars_dict["spell_slots"].get(), int(getattr(piece, "spell_slots", 0))),
				int(piece.max_spell_slots),
			)
			piece.movement = main_ui._safe_float(vars_dict["movement"].get(), float(getattr(piece, "movement", 0.0)))
			if main_ui._is_runtime_selected_source():
				weapon_label = (
					main_ui._normalize_weapon_label(str(vars_dict.get("weapon").get()).strip())
					if vars_dict.get("weapon")
					else "自定义"
				)
				armor_label = str(vars_dict.get("armor").get()).strip() if vars_dict.get("armor") else "无甲"
				weapon_id = main_ui._weapon_label_to_weapon_id(weapon_label)
				armor_id = main_ui._armor_label_to_armor_id(armor_label)
				piece.type = main_ui._weapon_id_to_piece_type(weapon_id)
				setattr(piece, "weapon", int(weapon_id))
				setattr(piece, "armor", int(armor_id))
			if getattr(piece, "position", None) is not None:
				piece.position.x = px
				piece.position.y = py
			else:
				piece.position = Point(px, py)
			applied_count += 1
			continue

		soldier_id = mock_map.get(slot_key)
		if soldier_id is None:
			continue
		stats = main_ui.mock_piece_stats_by_id.setdefault(soldier_id, {})
		if main_ui._is_runtime_selected_source():
			stats["profession"] = str(vars_dict.get("profession").get()).strip() if vars_dict.get("profession") else "自定义"
			stats["weapon"] = str(vars_dict.get("weapon").get()).strip() if vars_dict.get("weapon") else "自定义"
			stats["armor"] = str(vars_dict.get("armor").get()).strip() if vars_dict.get("armor") else "无甲"
		px, py = main_ui._clamp_piece_position(
			main_ui._safe_int(
				vars_dict["pos_x"].get(),
				int(main_ui.mock_initial_positions.get(soldier_id, {}).get("x", 0)),
			),
			main_ui._safe_int(
				vars_dict["pos_y"].get(),
				int(main_ui.mock_initial_positions.get(soldier_id, {}).get("y", 0)),
			),
		)
		main_ui.mock_last_health_by_id[soldier_id] = main_ui._safe_int(
			vars_dict["hp"].get(), int(main_ui.mock_last_health_by_id.get(soldier_id, 0))
		)
		stats["strength"] = main_ui._safe_int(vars_dict["strength"].get(), int(stats.get("strength", 0)))
		stats["dexterity"] = main_ui._safe_int(vars_dict["dexterity"].get(), int(stats.get("dexterity", 0)))
		stats["intelligence"] = main_ui._safe_int(vars_dict["intelligence"].get(), int(stats.get("intelligence", 0)))
		stats["physical_resist"] = main_ui._safe_int(
			vars_dict["physical_resist"].get(), int(stats.get("physical_resist", 0))
		)
		stats["magic_resist"] = main_ui._safe_int(vars_dict["magic_resist"].get(), int(stats.get("magic_resist", 0)))
		stats["physical_damage"] = main_ui._safe_int(
			vars_dict["physical_damage"].get(), int(stats.get("physical_damage", 0))
		)
		stats["magic_damage"] = main_ui._safe_int(vars_dict["magic_damage"].get(), int(stats.get("magic_damage", 0)))
		stats["max_action_points"] = main_ui._safe_int(
			vars_dict["max_action_points"].get(), int(stats.get("max_action_points", 0))
		)
		stats["action_points"] = min(
			main_ui._safe_int(vars_dict["action_points"].get(), int(stats.get("action_points", 0))),
			int(stats["max_action_points"]),
		)
		stats["max_spell_slots"] = main_ui._safe_int(
			vars_dict["max_spell_slots"].get(), int(stats.get("max_spell_slots", 0))
		)
		stats["spell_slots"] = min(
			main_ui._safe_int(vars_dict["spell_slots"].get(), int(stats.get("spell_slots", 0))),
			int(stats["max_spell_slots"]),
		)
		stats["movement"] = main_ui._safe_float(vars_dict["movement"].get(), float(stats.get("movement", 0.0)))
		if soldier_id in main_ui.mock_initial_positions:
			main_ui.mock_initial_positions[soldier_id]["x"] = px
			main_ui.mock_initial_positions[soldier_id]["y"] = py
		main_ui.mock_last_positions_by_id[soldier_id] = (px, py)
		applied_count += 1

	if warnings:
		main_ui._show_attribute_warning_feedback(f"{warnings[0]}（自动修正为最近边界值）")

	if main_ui.attribute_settings_force_init_mode and main_ui._is_runtime_selected_source():
		main_ui.runtime_init_config_ready = True
		main_ui.right_info_panel.append_content("\n[UI] 后端模式初始化属性已确认")
		main_ui._show_attribute_apply_feedback("应用成功")
		if main_ui.attribute_settings_window is not None and main_ui.attribute_settings_window.winfo_exists():
			win = main_ui.attribute_settings_window
			main_ui.attribute_settings_window = None
			main_ui.attribute_settings_content_frame = None
			main_ui.attribute_settings_force_init_mode = False
			win.destroy()
		return

	main_ui._refresh_piece_cards()
	main_ui._refresh_board_view()
	# 手动应用属性可能直接导致某一方全灭（例如 0HP vs 50HP），这里主动检查胜负。
	if main_ui.controller.runtime_source == "runtime_env" and main_ui.controller.environment is not None:
		main_ui._check_and_announce_runtime_game_over(main_ui.controller.environment, show_dialog=True)
	main_ui.right_info_panel.append_content(f"\n[UI] 棋子属性已应用（本局临时生效），影响棋子数: {applied_count}")
	main_ui._show_attribute_apply_feedback("应用成功")


def build_attribute_piece_page(main_ui: Any, content: ttk.LabelFrame) -> None:
	"""构建棋子属性页：固定 6 槽位，矩阵化布局并支持纵向滚动。"""
	wrapper = ttk.Frame(content)
	wrapper.grid(row=0, column=0, sticky="nsew")
	wrapper.columnconfigure(0, weight=1)
	wrapper.rowconfigure(1, weight=1)

	ttk.Label(wrapper, text="棋子属性", font=("Microsoft YaHei UI", 12, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)

	scroll_host = ttk.Frame(wrapper)
	scroll_host.grid(row=1, column=0, sticky="nsew")
	scroll_host.columnconfigure(0, weight=1)
	scroll_host.rowconfigure(0, weight=1)

	canvas = tk.Canvas(scroll_host, highlightthickness=0, borderwidth=0)
	v_scroll = ttk.Scrollbar(scroll_host, orient="vertical", command=canvas.yview)
	canvas.configure(yscrollcommand=v_scroll.set)
	canvas.grid(row=0, column=0, sticky="nsew")
	v_scroll.grid(row=0, column=1, sticky="ns")

	scroll_content = ttk.Frame(canvas)
	canvas_window = canvas.create_window((0, 0), window=scroll_content, anchor="nw")

	def _sync_scroll_region(_event: Any = None) -> None:
		canvas.configure(scrollregion=canvas.bbox("all"))

	def _fit_scroll_content_width(event: Any) -> None:
		canvas.itemconfigure(canvas_window, width=int(event.width))

	scroll_content.bind("<Configure>", _sync_scroll_region)
	canvas.bind("<Configure>", _fit_scroll_content_width)

	def _on_mousewheel(event: Any) -> None:
		if int(event.delta) == 0:
			return
		canvas.yview_scroll(-int(event.delta / 120), "units")

	canvas.bind_all("<MouseWheel>", _on_mousewheel)
	canvas.bind("<Destroy>", lambda _e: canvas.unbind_all("<MouseWheel>"))

	runtime_map = main_ui._runtime_piece_slot_map()
	mock_map = main_ui._mock_piece_slot_map()
	slot_keys = main_ui._piece_slot_keys()

	main_ui.attribute_piece_vars = {}
	main_ui.attribute_piece_entries = {}
	main_ui.attribute_piece_last_edit_tick = {}
	main_ui.attribute_piece_hp_hint_widgets = {}

	enabled_map: dict[str, bool] = {}
	for slot_key in slot_keys:
		if main_ui.attribute_settings_force_init_mode and main_ui._is_runtime_selected_source():
			enabled_map[slot_key] = True
		else:
			enabled_map[slot_key] = (
				slot_key in runtime_map if main_ui.controller.runtime_source == "runtime_env" else slot_key in mock_map
			)
		main_ui.attribute_piece_vars[slot_key] = {}
		main_ui.attribute_piece_entries[slot_key] = {}
		main_ui.attribute_piece_last_edit_tick[slot_key] = 0

	weapon_values = ["自定义", "长剑", "短剑", "弓", "法杖"]
	armor_values = ["无甲", "轻甲", "中甲", "重甲"]
	if main_ui._is_profession_mode():
		weapon_values = ["长剑", "短剑", "弓", "法杖"]
		armor_values = ["轻甲", "中甲", "重甲"]
	combo_values: dict[str, list[str]] = {
		"weapon": weapon_values,
		"armor": armor_values,
	}

	field_groups: list[tuple[str, list[tuple[str, str]]]] = [
		(
			"职业与装备",
			[
				("profession", "职业"),
				("weapon", "武器"),
				("armor", "护甲"),
			],
		),
		(
			"天赋属性",
			[
				("strength", "力量"),
				("dexterity", "敏捷"),
				("intelligence", "智力"),
			],
		),
		(
			"基础与战斗属性",
			[
				("hp", "血量"),
				("physical_resist", "物抗"),
				("magic_resist", "法抗"),
				("physical_damage", "物伤"),
				("magic_damage", "法伤"),
				("action_points", "行动位"),
				("max_action_points", "行动位上限"),
				("spell_slots", "法术位"),
				("max_spell_slots", "法术位上限"),
				("movement", "移动力"),
				("pos_x", "X坐标"),
				("pos_y", "Y坐标"),
			],
		),
	]
	show_profession_section = main_ui._normalize_selected_source_value(main_ui.selected_source) in (
		"runtime_custom",
		"runtime_profession",
	)
	if not show_profession_section:
		field_groups = field_groups[1:]

	derived_fields: set[str] = {
		"hp",
		"physical_resist",
		"magic_resist",
		"physical_damage",
		"magic_damage",
		"action_points",
		"max_action_points",
		"spell_slots",
		"max_spell_slots",
		"movement",
	}
	lock_all_stats = main_ui._is_profession_mode() and not main_ui.attribute_settings_force_init_mode

	def render_matrix(
		parent: ttk.Frame,
		fields: list[tuple[str, str]],
		*,
		start_row: int,
		title: str | None = None,
		highlight: str | None = None,
	) -> int:
		row_idx = start_row
		if title is not None:
			title_fg = highlight if highlight is not None else "#111827"
			ttk.Label(parent, text=title, font=("Microsoft YaHei UI", 10, "bold"), foreground=title_fg).grid(
				row=row_idx, column=0, columnspan=len(slot_keys) + 1, sticky="w", pady=(0, 6)
			)
			row_idx += 1

		table = ttk.Frame(parent)
		table.grid(row=row_idx, column=0, sticky="ew")
		table.columnconfigure(0, weight=0)
		for col_idx in range(1, len(slot_keys) + 1):
			table.columnconfigure(col_idx, weight=1)

		ttk.Label(table, text="属性\\棋子", font=("Microsoft YaHei UI", 9, "bold")).grid(
			row=0, column=0, sticky="w", padx=(0, 8), pady=(0, 6)
		)
		for col_idx, slot_key in enumerate(slot_keys, start=1):
			team = int(slot_key[1])
			num = int(slot_key[-1])
			ttk.Label(table, text=f"P{team}-{num}", font=("Microsoft YaHei UI", 9, "bold")).grid(
				row=0, column=col_idx, sticky="w", padx=(0, 6), pady=(0, 6)
			)

		for field_row, (field, field_label) in enumerate(fields, start=1):
			ttk.Label(table, text=field_label).grid(row=field_row, column=0, sticky="w", padx=(0, 8), pady=3)
			for col_idx, slot_key in enumerate(slot_keys, start=1):
				values = main_ui._get_piece_row_values(slot_key, runtime_map, mock_map)
				var = tk.StringVar(value=values[field])
				var.trace_add("write", lambda *_args, sk=slot_key, fd=field: main_ui._on_attribute_var_changed(sk, fd))
				state = "normal" if enabled_map.get(slot_key, False) else "disabled"
				if lock_all_stats and field not in ("pos_x", "pos_y"):
					state = "disabled"
				widget: Any
				if field == "profession":
					entry_state = "readonly" if state == "normal" else "disabled"
					entry = tk.Entry(
						table,
						textvariable=var,
						width=9,
						state=entry_state,
						fg="#111111",
						disabledforeground="#9ca3af",
						readonlybackground="#f3f4f6",
					)
					entry.grid(row=field_row, column=col_idx, sticky="ew", padx=(0, 6), pady=3)
					widget = entry
				elif field in ("weapon", "armor"):
					combo_state = "readonly" if state == "normal" else "disabled"
					combo = ttk.Combobox(
						table,
						textvariable=var,
						values=combo_values.get(field, []),
						state=combo_state,
						width=9,
					)
					combo.grid(row=field_row, column=col_idx, sticky="ew", padx=(0, 6), pady=3)
					widget = combo
				else:
					if main_ui._is_profession_mode() and field in derived_fields:
						state = "disabled"
					if (
						field == "hp"
						and main_ui.attribute_settings_force_init_mode
						and main_ui._normalize_selected_source_value(main_ui.selected_source) == "runtime_custom"
						and not main_ui._is_profession_mode()
					):
						cell = ttk.Frame(table)
						cell.grid(row=field_row, column=col_idx, sticky="ew", padx=(0, 6), pady=3)
						cell.columnconfigure(0, weight=1)
						entry = tk.Entry(
							cell,
							textvariable=var,
							width=6,
							state=state,
							fg="#111111",
							disabledforeground="#9ca3af",
						)
						entry.grid(row=0, column=0, sticky="ew")

						# placeholder：覆盖在 Entry 内部，但不写入 Entry 内容。
						try:
							entry_bg = str(entry.cget("background"))
						except Exception:
							entry_bg = "#ffffff"
						overlay = tk.Frame(cell, bg=entry_bg, highlightthickness=0, bd=0)
						dash_label = tk.Label(overlay, text="-", fg="#111111", bg=entry_bg)
						hint_label = tk.Label(overlay, text="", fg="#9ca3af", bg=entry_bg)
						dash_label.pack(side="left")
						hint_label.pack(side="left")
						# 默认先隐藏，交给 _refresh_custom_init_hp_hint 控制显示。
						overlay.place_forget()
						# 点击 placeholder 时也能聚焦输入框。
						overlay.bind("<Button-1>", lambda _e, ent=entry: ent.focus_set())
						dash_label.bind("<Button-1>", lambda _e, ent=entry: ent.focus_set())
						hint_label.bind("<Button-1>", lambda _e, ent=entry: ent.focus_set())
						main_ui.attribute_piece_hp_hint_widgets[slot_key] = (entry, overlay, dash_label, hint_label)
						widget = entry
					else:
						entry = tk.Entry(
							table,
							textvariable=var,
							width=9,
							state=state,
							fg="#111111",
							disabledforeground="#9ca3af",
						)
						entry.grid(row=field_row, column=col_idx, sticky="ew", padx=(0, 6), pady=3)
						widget = entry
				main_ui.attribute_piece_vars[slot_key][field] = var
				main_ui.attribute_piece_entries[slot_key][field] = widget

		return row_idx + 1

	row_cursor = 0
	for group_title, group_fields in field_groups:
		display_title = group_title
		highlight = None
		row_cursor = render_matrix(
			scroll_content,
			group_fields,
			start_row=row_cursor,
			title=display_title,
			highlight=highlight,
		)
		row_cursor += 1
	for slot_key in slot_keys:
		if main_ui._is_profession_mode():
			main_ui._update_profession_display_and_presets(slot_key)
		else:
			# 注意：初始化窗口的 custom 默认战斗数值是硬编码写入 cfg 的，不应再被装备预设覆盖。
			main_ui._update_custom_mode_equipment_presets(slot_key, update_stats=False)
		if (
			main_ui.attribute_settings_force_init_mode
			and main_ui._normalize_selected_source_value(main_ui.selected_source) == "runtime_custom"
			and not main_ui._is_profession_mode()
		):
			main_ui._refresh_custom_init_hp_hint(slot_key)

	if main_ui.attribute_settings_force_init_mode and main_ui._is_runtime_selected_source():
		cap = main_ui._get_talent_total_cap() if main_ui._is_profession_mode() else None
		ttk.Label(
			scroll_content,
			text=(
				f"后端模式初始化：请至少为双方各配置一个有效棋子（力量/敏捷/智力均填写且总和≤{cap}）。"
				if main_ui._is_profession_mode()
				else "后端模式初始化：请至少为双方各配置一个有效棋子（血量非“-”且 > 0）。"
			),
			foreground="#7c3aed",
		).grid(row=row_cursor + 1, column=0, sticky="w", pady=(10, 0))
	elif not main_ui.loaded:
		ttk.Label(
			scroll_content,
			text="当前未加载对局，6个棋子槽位均不可编辑。",
			foreground="#6b7280",
		).grid(row=row_cursor + 1, column=0, sticky="w", pady=(10, 0))
	else:
		ttk.Label(
			scroll_content,
			text="注：仅当前开局存在的棋子可编辑，未上场棋子槽位会禁用。",
			foreground="#6b7280",
		).grid(row=row_cursor + 1, column=0, sticky="w", pady=(10, 0))

	button_row = ttk.Frame(wrapper)
	button_row.grid(row=2, column=0, sticky="e", pady=(10, 0))
	main_ui.attribute_piece_apply_status_label = ttk.Label(button_row, text="", foreground="#059669")
	main_ui.attribute_piece_apply_status_label.pack(side="right", padx=(0, 8))
	if main_ui.attribute_settings_force_init_mode and main_ui._normalize_selected_source_value(main_ui.selected_source) in (
		"runtime_custom",
		"runtime_profession",
	):
		ttk.Button(button_row, text="一键开始", command=main_ui._one_click_fill_custom_init).pack(
			side="right", padx=(0, 8)
		)
	ttk.Button(button_row, text="应用", command=lambda: apply_piece_attribute_changes(main_ui)).pack(side="right")

	main_ui.attribute_piece_warning_label = ttk.Label(wrapper, text="", foreground="#b45309")
	main_ui.attribute_piece_warning_label.grid(row=3, column=0, sticky="w", pady=(8, 0))
