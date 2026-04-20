"""属性设置：派生属性计算与联动（Phase 3：MainUI 拆分进行中）。

本文件负责：
- 职业/自定义模式下：武器/护甲/职业展示的联动规则。
- 派生属性的计算（优先调用后端 Environment.apply_init_policy，避免 UI 写死规则）。
- 天赋字段解析、天赋总和上限读取、有效性判断。
- 强制初始化模式下：自定义初始化 HP hint 刷新、一键填入经典 6 棋子配置。

设计约束：
- 保持 UX/行为不变。
- 以 `main_ui` 为首参（duck-typing），直接访问其字段/方法；service 不反向 import main_ui。
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import tkinter as tk

from env import Environment, PieceArg, Player, Point


def weapon_label_to_weapon_id(_main_ui: Any, weapon_label: str) -> int:
	label = str(weapon_label or "").strip()
	if label in ("长剑", "长"):
		return 1
	if label in ("短剑", "短剑🗡", "🗡", "短"):
		return 2
	if label == "弓":
		return 3
	if label == "法杖":
		return 4
	return 0


def armor_label_to_armor_id(_main_ui: Any, armor_label: str) -> int:
	label = str(armor_label or "").strip()
	if label == "轻甲":
		return 1
	if label == "中甲":
		return 2
	if label == "重甲":
		return 3
	return 0


def weapon_id_to_weapon_label(_main_ui: Any, weapon_id: int) -> str:
	wid = int(weapon_id)
	if wid == 1:
		return "长剑"
	if wid == 2:
		return "短剑"
	if wid == 3:
		return "弓"
	if wid == 4:
		return "法杖"
	return "自定义"


def armor_id_to_armor_label(_main_ui: Any, armor_id: int) -> str:
	aid = int(armor_id)
	if aid == 1:
		return "轻甲"
	if aid == 2:
		return "中甲"
	if aid == 3:
		return "重甲"
	return "无甲"


def normalize_weapon_label(_main_ui: Any, weapon_label: str) -> str:
	label = str(weapon_label or "").strip()
	if label in ("0", "自定义", "None"):
		return "自定义"
	if label == "长枪":
		return "长剑"
	if label == "短剑🗡":
		return "短剑"
	if label == "🗡":
		return "短剑"
	return label


def weapon_id_to_profession_display(_main_ui: Any, weapon_id: int) -> str:
	wid = int(weapon_id)
	if wid == 1:
		return "战士(长)"
	if wid == 2:
		return "战士(短)"
	if wid == 3:
		return "射手"
	if wid == 4:
		return "法师"
	return "自定义"


def weapon_id_to_profession_label_simple(_main_ui: Any, weapon_id: int) -> str:
	wid = int(weapon_id)
	if wid == 1:
		return "战士(长)"
	if wid == 2:
		return "战士(短)"
	if wid == 3:
		return "射手"
	if wid == 4:
		return "法师"
	return "自定义"


def get_talent_total_cap(main_ui: Any) -> int:
	"""天赋总和上限（读取后端 env 的变量，避免 UI 写死常数）。"""
	env = getattr(main_ui.controller, "environment", None)
	if env is not None:
		for player_attr in ("player1", "player2"):
			player = getattr(env, player_attr, None)
			cap = getattr(player, "feature_total", None) if player is not None else None
			try:
				cap_int = int(cap)
			except Exception:
				cap_int = 0
			if cap_int > 0:
				return cap_int
	try:
		cap_int = int(getattr(Player(), "feature_total", 0))
		if cap_int > 0:
			return cap_int
	except Exception:
		pass
	# 极端兜底：若后端结构变化导致无法读取，仍给出一个可用值。
	return 30


def parse_talent_int(_main_ui: Any, raw: Any) -> int | None:
	text = str(raw if raw is not None else "").strip()
	if text in ("", "-", "-1", "None"):
		return None
	try:
		value = int(text)
	except Exception:
		return None
	return value if value >= 0 else None


def is_profession_slot_active_from_vars(main_ui: Any, vars_dict: dict[str, tk.StringVar] | None) -> bool:
	if not vars_dict:
		return False
	strength = parse_talent_int(main_ui, vars_dict.get("strength").get() if vars_dict.get("strength") else None)
	dexterity = parse_talent_int(main_ui, vars_dict.get("dexterity").get() if vars_dict.get("dexterity") else None)
	intelligence = parse_talent_int(
		main_ui, vars_dict.get("intelligence").get() if vars_dict.get("intelligence") else None
	)
	if strength is None or dexterity is None or intelligence is None:
		return False
	cap = get_talent_total_cap(main_ui)
	return (strength + dexterity + intelligence) <= cap


def is_profession_slot_active_from_cfg(main_ui: Any, cfg: dict[str, Any] | None) -> bool:
	if not cfg:
		return False
	strength = parse_talent_int(main_ui, cfg.get("strength"))
	dexterity = parse_talent_int(main_ui, cfg.get("dexterity"))
	intelligence = parse_talent_int(main_ui, cfg.get("intelligence"))
	if strength is None or dexterity is None or intelligence is None:
		return False
	cap = get_talent_total_cap(main_ui)
	return (strength + dexterity + intelligence) <= cap


def compute_equipment_only_stats(
	_main_ui: Any,
	*,
	weapon_id: int,
	armor_id: int,
	strength: int | None = None,
	dexterity: int | None = None,
) -> dict[str, str]:
	"""仅按武器/护甲更新对应数值，用于自定义模式。
	- 物伤/法伤/物抗/法抗：完全由装备决定
	- 移动力：若提供 strength/dexterity，则按后端公式 base + 护甲修正计算；否则不返回 movement
	"""
	physical_damage, magic_damage = 6, 6
	if int(weapon_id) == 1:
		physical_damage, magic_damage = 18, 0
	elif int(weapon_id) == 2:
		physical_damage, magic_damage = 24, 0
	elif int(weapon_id) == 3:
		physical_damage, magic_damage = 16, 0
	elif int(weapon_id) == 4:
		physical_damage, magic_damage = 0, 22

	physical_resist, magic_resist = 6, 6
	if int(armor_id) == 1:
		physical_resist, magic_resist = 8, 10
	elif int(armor_id) == 2:
		physical_resist, magic_resist = 15, 13
	elif int(armor_id) == 3:
		physical_resist, magic_resist = 23, 17

	result = {
		"physical_damage": str(int(physical_damage)),
		"magic_damage": str(int(magic_damage)),
		"physical_resist": str(int(physical_resist)),
		"magic_resist": str(int(magic_resist)),
	}
	if strength is not None and dexterity is not None:
		move_delta = 0.0
		if int(armor_id) == 1:
			move_delta = 3.0
		elif int(armor_id) == 3:
			move_delta = -3.0
		base_move = float(dexterity) + 0.5 * float(strength) + 10.0
		movement = max(0.0, base_move + move_delta)
		result["movement"] = f"{float(movement):.1f}".rstrip("0").rstrip(".")
	return result


def update_custom_mode_equipment_presets(main_ui: Any, slot_key: str, *, update_stats: bool) -> None:
	"""自定义模式：职业随武器变化且只读显示。
	- update_stats=True: 覆盖更新装备对应的附带属性值（物伤/法伤/物抗/法抗），但不锁死字段。
	- update_stats=False: 仅刷新职业显示，不改数值（避免打开窗口时覆盖玩家手调值）。
	"""
	if main_ui._is_profession_mode():
		return
	vars_dict = main_ui.attribute_piece_vars.get(slot_key)
	if not vars_dict:
		return
	weapon_label = (
		normalize_weapon_label(main_ui, str(vars_dict.get("weapon").get()).strip())
		if vars_dict.get("weapon")
		else "自定义"
	)
	armor_label = str(vars_dict.get("armor").get()).strip() if vars_dict.get("armor") else "无甲"
	weapon_id = weapon_label_to_weapon_id(main_ui, weapon_label)
	armor_id = armor_label_to_armor_id(main_ui, armor_label)

	profession_var = vars_dict.get("profession")
	if profession_var is not None:
		desired = weapon_id_to_profession_label_simple(main_ui, weapon_id)
		if str(profession_var.get()).strip() != desired:
			main_ui.attribute_internal_update = True
			try:
				profession_var.set(desired)
			finally:
				main_ui.attribute_internal_update = False

	if update_stats:
		strength = main_ui._safe_int(str(vars_dict.get("strength").get()).strip(), 10) if vars_dict.get("strength") else 10
		dexterity = (
			main_ui._safe_int(str(vars_dict.get("dexterity").get()).strip(), 10) if vars_dict.get("dexterity") else 10
		)
		presets = compute_equipment_only_stats(
			main_ui,
			weapon_id=weapon_id,
			armor_id=armor_id,
			strength=strength,
			dexterity=dexterity,
		)
		main_ui.attribute_internal_update = True
		try:
			for key, value in presets.items():
				var = vars_dict.get(key)
				if var is not None:
					var.set(str(value))
		finally:
			main_ui.attribute_internal_update = False


def update_equipment_dependent_fields(main_ui: Any, slot_key: str) -> None:
	if main_ui._is_profession_mode():
		update_profession_display_and_presets(main_ui, slot_key)
	else:
		update_custom_mode_equipment_presets(main_ui, slot_key, update_stats=False)


def compute_custom_mode_stats_via_backend(
	main_ui: Any,
	*,
	strength: int,
	dexterity: int,
	intelligence: int,
	weapon_label: str,
	armor_label: str,
) -> dict[str, str]:
	"""自定义模式：用后端 env.apply_init_policy 计算派生属性，避免 UI 自己写死规则。"""
	weapon_id = weapon_label_to_weapon_id(main_ui, normalize_weapon_label(main_ui, weapon_label))
	armor_id = armor_label_to_armor_id(main_ui, str(armor_label).strip() or "无甲")
	if weapon_id == 4:
		# 后端规则：法杖会强制轻甲（与职业模式保持一致）。
		armor_id = 1
	env = Environment(local_mode=True, if_log=0)
	env.create_default_board()
	arg = PieceArg()
	arg.strength = int(strength)
	arg.dexterity = int(dexterity)
	arg.intelligence = int(intelligence)
	arg.equip = Point(int(weapon_id), int(armor_id))
	arg.pos = Point(0, 0)
	policy = SimpleNamespace(piece_args=[arg])
	env.apply_init_policy(1, policy)
	piece = env.player1.pieces[0]
	movement = float(getattr(piece, "max_movement", getattr(piece, "movement", 0.0)))
	result = {
		"hp": str(int(getattr(piece, "max_health", 0))),
		"physical_resist": str(int(getattr(piece, "physical_resist", 0))),
		"magic_resist": str(int(getattr(piece, "magic_resist", 0))),
		"physical_damage": str(int(getattr(piece, "physical_damage", 0))),
		"magic_damage": str(int(getattr(piece, "magic_damage", 0))),
		"max_action_points": str(int(getattr(piece, "max_action_points", 0))),
		"action_points": str(int(getattr(piece, "action_points", 0))),
		"max_spell_slots": str(int(getattr(piece, "max_spell_slots", 0))),
		"spell_slots": str(int(getattr(piece, "spell_slots", 0))),
		"movement": f"{float(movement):.1f}".rstrip("0").rstrip("."),
	}
	return result


def custom_init_hp_hint_value(main_ui: Any, slot_key: str) -> int:
	vars_dict = main_ui.attribute_piece_vars.get(slot_key)
	if not vars_dict:
		return 50
	strength_raw = str(vars_dict.get("strength").get()).strip() if vars_dict.get("strength") is not None else "10"
	strength = main_ui._safe_int(strength_raw, 10)
	return int(30 + strength * 2)


def refresh_custom_init_hp_hint(main_ui: Any, slot_key: str) -> None:
	widgets = main_ui.attribute_piece_hp_hint_widgets.get(slot_key)
	if not widgets:
		return
	vars_dict = main_ui.attribute_piece_vars.get(slot_key)
	if not vars_dict:
		return
	hp_var = vars_dict.get("hp")
	if hp_var is None:
		return
	hp_raw = str(hp_var.get()).strip()
	should_show = bool(
		hp_raw in ("", "-", "-1")
		and main_ui.attribute_settings_force_init_mode
		and main_ui._normalize_selected_source_value(main_ui.selected_source) == "runtime_custom"
	)

	# 兼容：旧实现是 (dash_label, hint_label)；新实现是 (entry, overlay, dash_label, hint_label)
	if isinstance(widgets, tuple) and len(widgets) == 2:
		dash_label, hint_label = widgets
		if should_show:
			hint_value = custom_init_hp_hint_value(main_ui, slot_key)
			hint_label.configure(text=f" ({hint_value})")
			dash_label.grid()
			hint_label.grid()
		else:
			dash_label.grid_remove()
			hint_label.grid_remove()
		return

	entry, overlay, _dash_label, hint_label = widgets
	if should_show:
		hint_value = custom_init_hp_hint_value(main_ui, slot_key)
		hint_label.configure(text=f" ({hint_value})")
		try:
			# 覆盖在 Entry 内部左侧，不占用 Entry 内容。
			overlay.place(in_=entry, x=4, y=1, relheight=1)
		except Exception:
			pass
	else:
		try:
			overlay.place_forget()
		except Exception:
			pass


def one_click_fill_custom_init(main_ui: Any) -> None:
	"""仅用于“后端模式初始化属性窗口”：一键写入 6 棋子经典配置。"""
	if not (
		main_ui.attribute_settings_force_init_mode
		and main_ui._normalize_selected_source_value(main_ui.selected_source) in ("runtime_custom", "runtime_profession")
	):
		return
	fixed_positions: dict[str, tuple[int, int]] = {
		"p1_1": (3, 8),
		"p1_2": (8, 3),
		"p1_3": (17, 4),
		"p2_1": (16, 11),
		"p2_2": (11, 16),
		"p2_3": (2, 15),
	}
	preset: dict[str, dict[str, Any]] = {
		"p1_1": {"weapon": "长剑", "armor": "重甲", "strength": 20, "dexterity": 8, "intelligence": 2},
		"p1_2": {"weapon": "弓", "armor": "轻甲", "strength": 14, "dexterity": 16, "intelligence": 0},
		"p1_3": {"weapon": "短剑", "armor": "中甲", "strength": 16, "dexterity": 12, "intelligence": 2},
		"p2_1": {"weapon": "法杖", "armor": "轻甲", "strength": 14, "dexterity": 2, "intelligence": 14},
		"p2_2": {"weapon": "短剑", "armor": "轻甲", "strength": 14, "dexterity": 14, "intelligence": 2},
		"p2_3": {"weapon": "弓", "armor": "轻甲", "strength": 14, "dexterity": 16, "intelligence": 0},
	}
	main_ui.attribute_internal_update = True
	try:
		for slot_key in main_ui._piece_slot_keys():
			vars_dict = main_ui.attribute_piece_vars.get(slot_key)
			if not vars_dict:
				continue
			conf = preset.get(slot_key, {})
			px, py = fixed_positions.get(slot_key, (0, 0))
			px, py = main_ui._clamp_piece_position(px, py)
			weapon_label = str(conf.get("weapon", "自定义"))
			armor_label = str(conf.get("armor", "无甲"))
			strength = int(conf.get("strength", 10))
			dexterity = int(conf.get("dexterity", 10))
			intelligence = int(conf.get("intelligence", 10))

			if vars_dict.get("weapon") is not None:
				vars_dict["weapon"].set(weapon_label)
			if vars_dict.get("armor") is not None:
				vars_dict["armor"].set(armor_label)
			if vars_dict.get("strength") is not None:
				vars_dict["strength"].set(str(strength))
			if vars_dict.get("dexterity") is not None:
				vars_dict["dexterity"].set(str(dexterity))
			if vars_dict.get("intelligence") is not None:
				vars_dict["intelligence"].set(str(intelligence))

			weapon_id = weapon_label_to_weapon_id(main_ui, normalize_weapon_label(main_ui, weapon_label))
			if vars_dict.get("profession") is not None:
				vars_dict["profession"].set(weapon_id_to_profession_label_simple(main_ui, weapon_id))

			derived = compute_custom_mode_stats_via_backend(
				main_ui,
				strength=strength,
				dexterity=dexterity,
				intelligence=intelligence,
				weapon_label=weapon_label,
				armor_label=armor_label,
			)
			for key in (
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
			):
				if vars_dict.get(key) is not None and key in derived:
					vars_dict[key].set(str(derived[key]))
			if vars_dict.get("pos_x") is not None:
				vars_dict["pos_x"].set(str(px))
			if vars_dict.get("pos_y") is not None:
				vars_dict["pos_y"].set(str(py))
	finally:
		main_ui.attribute_internal_update = False

	# 自定义初始化：hp 输入必须在 0-200（不自动夹紧），超范围/非法直接阻止开局。
	if (
		main_ui.attribute_settings_force_init_mode
		and main_ui._is_runtime_selected_source()
		and main_ui._normalize_selected_source_value(main_ui.selected_source) == "runtime_custom"
		and (not main_ui._is_profession_mode())
	):
		for slot_key in main_ui._piece_slot_keys():
			vars_dict = main_ui.attribute_piece_vars.get(slot_key)
			if vars_dict is None:
				continue
			hp_raw = str(vars_dict.get("hp").get()).strip() if vars_dict.get("hp") is not None else ""
			if hp_raw in ("", "-", "-1"):
				continue
			try:
				hp_value = int(float(hp_raw))
			except Exception:
				slot_name = f"player{slot_key[1]}-{slot_key[-1]}"
				main_ui._mark_attribute_field_error(slot_key, "hp")
				main_ui._show_attribute_warning_feedback(f"{slot_name} 的血量必须是整数，且范围为 0-200")
				return
			if hp_value < 0 or hp_value > 200:
				slot_name = f"player{slot_key[1]}-{slot_key[-1]}"
				main_ui._mark_attribute_field_error(slot_key, "hp")
				main_ui._show_attribute_warning_feedback(f"{slot_name} 的血量超出范围：0-200")
				return

	for slot_key in main_ui._piece_slot_keys():
		refresh_custom_init_hp_hint(main_ui, slot_key)
	main_ui.right_info_panel.append_content("\n[UI] 已填入经典 6 棋子配置，请点击“应用”开始")


def weapon_id_to_piece_type(_main_ui: Any, weapon_id: int) -> str:
	wid = int(weapon_id)
	if wid in (1, 2):
		return "Warrior"
	if wid == 3:
		return "Archer"
	if wid == 4:
		return "Mage"
	return "Custom"


def compute_profession_mode_stats(
	main_ui: Any,
	*,
	strength: int,
	dexterity: int,
	intelligence: int,
	weapon_id: int,
	armor_id: int,
) -> dict[str, str]:
	"""按后端 env.py 的初始化逻辑计算派生属性（字符串形式用于回填 UI）。"""
	cache_key = (int(strength), int(dexterity), int(intelligence), int(weapon_id), int(armor_id))
	cached = main_ui._profession_derived_cache.get(cache_key)
	if cached is not None:
		return dict(cached)

	env = Environment(local_mode=True, if_log=0)
	env.create_default_board()
	arg = PieceArg()
	arg.strength = int(strength)
	arg.dexterity = int(dexterity)
	arg.intelligence = int(intelligence)
	arg.equip = Point(int(weapon_id), int(armor_id))
	arg.pos = Point(0, 0)
	policy = SimpleNamespace(piece_args=[arg])
	env.apply_init_policy(1, policy)
	piece = env.player1.pieces[0]

	movement = float(getattr(piece, "max_movement", getattr(piece, "movement", 0.0)))
	result = {
		"hp": str(int(getattr(piece, "max_health", 0))),
		"physical_resist": str(int(getattr(piece, "physical_resist", 0))),
		"magic_resist": str(int(getattr(piece, "magic_resist", 0))),
		"physical_damage": str(int(getattr(piece, "physical_damage", 0))),
		"magic_damage": str(int(getattr(piece, "magic_damage", 0))),
		"max_action_points": str(int(getattr(piece, "max_action_points", 0))),
		"action_points": str(int(getattr(piece, "action_points", 0))),
		"max_spell_slots": str(int(getattr(piece, "max_spell_slots", 0))),
		"spell_slots": str(int(getattr(piece, "spell_slots", 0))),
		"movement": f"{float(movement):.1f}".rstrip("0").rstrip("."),
	}
	main_ui._profession_derived_cache[cache_key] = dict(result)
	return result


def update_profession_display_and_presets(main_ui: Any, slot_key: str) -> None:
	vars_dict = main_ui.attribute_piece_vars.get(slot_key)
	if not vars_dict:
		return
	weapon_label = str(vars_dict.get("weapon").get()).strip() if vars_dict.get("weapon") else ""
	armor_label = str(vars_dict.get("armor").get()).strip() if vars_dict.get("armor") else ""
	weapon_id = weapon_label_to_weapon_id(main_ui, weapon_label)
	armor_id = armor_label_to_armor_id(main_ui, armor_label)

	# 仅职业模式：职业由武器决定；自定义模式下职业可自由编辑。
	if main_ui._is_profession_mode():
		profession_var = vars_dict.get("profession")
		if profession_var is not None:
			profession_display = weapon_id_to_profession_display(main_ui, weapon_id)
			if profession_var.get() != profession_display:
				main_ui.attribute_internal_update = True
				try:
					profession_var.set(profession_display)
				finally:
					main_ui.attribute_internal_update = False

	# 仅职业模式：法杖强制轻甲（与 env.py 规则对齐）。
	if main_ui._is_profession_mode() and weapon_id == 4 and vars_dict.get("armor") is not None:
		if str(vars_dict["armor"].get()).strip() != "轻甲":
			main_ui.attribute_internal_update = True
			try:
				vars_dict["armor"].set("轻甲")
			finally:
				main_ui.attribute_internal_update = False
		armor_id = 1

	# 仅职业模式且在初始化配置阶段：自动填充派生属性（未点击“应用”前也生效）。
	if not (main_ui._is_profession_mode() and main_ui.attribute_settings_force_init_mode):
		return
	strength = parse_talent_int(main_ui, vars_dict.get("strength").get() if vars_dict.get("strength") else None)
	dexterity = parse_talent_int(main_ui, vars_dict.get("dexterity").get() if vars_dict.get("dexterity") else None)
	intelligence = parse_talent_int(
		main_ui, vars_dict.get("intelligence").get() if vars_dict.get("intelligence") else None
	)
	if armor_id <= 0 and weapon_id in (1, 2, 3, 4):
		armor_id = 1

	derived_keys = (
		"hp",
		"physical_resist",
		"magic_resist",
		"physical_damage",
		"magic_damage",
		"max_action_points",
		"action_points",
		"max_spell_slots",
		"spell_slots",
		"movement",
	)
	if strength is None or dexterity is None or intelligence is None:
		main_ui.attribute_internal_update = True
		try:
			for key in derived_keys:
				var = vars_dict.get(key)
				if var is not None:
					var.set("-")
		finally:
			main_ui.attribute_internal_update = False
		return

	cap = get_talent_total_cap(main_ui)
	if (int(strength) + int(dexterity) + int(intelligence)) > cap:
		main_ui.attribute_internal_update = True
		try:
			for key in derived_keys:
				var = vars_dict.get(key)
				if var is not None:
					var.set("-")
		finally:
			main_ui.attribute_internal_update = False
		return

	derived = compute_profession_mode_stats(
		main_ui,
		strength=int(strength),
		dexterity=int(dexterity),
		intelligence=int(intelligence),
		weapon_id=weapon_id,
		armor_id=armor_id,
	)
	main_ui.attribute_internal_update = True
	try:
		for key, value in derived.items():
			var = vars_dict.get(key)
			if var is not None:
				var.set(str(value))
	finally:
		main_ui.attribute_internal_update = False


def sync_profession_equipment(main_ui: Any, slot_key: str, changed_field: str) -> None:
	"""将职业展示与属性联动到武器/护甲。职业模式=派生锁定；自定义模式=仅覆盖装备相关数值但不锁死。"""
	if changed_field not in ("weapon", "armor"):
		return
	if main_ui._is_profession_mode():
		update_profession_display_and_presets(main_ui, slot_key)
	else:
		# 自定义模式：只有在武器/护甲变更时才覆盖数值。
		update_custom_mode_equipment_presets(main_ui, slot_key, update_stats=True)
