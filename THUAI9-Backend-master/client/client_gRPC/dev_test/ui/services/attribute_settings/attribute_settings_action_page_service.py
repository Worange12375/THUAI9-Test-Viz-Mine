"""属性设置窗口：行动属性页（action）。

本文件负责：
- “行动属性”页 UI 构建（攻击模型参数、法术模板覆盖）。
- 将 UI 变量与 `action_settings_snapshot` 双向同步。
- 点击“应用（本局）/恢复默认”的回调，以及把配置注入 runtime env（仅内存生效）。

阶段说明：
- Phase 3：MainUI 拆分进行中；以“搬家不改逻辑”为原则，接收 `main_ui` 实例并直接访问其字段/方法。
"""

from __future__ import annotations

import copy
from typing import Any

import tkinter as tk
from tkinter import ttk


def default_action_settings_snapshot(_main_ui: Any) -> dict[str, Any]:
	return {
		"attack_model": {
			"enable_d20": True,
			"hit": {
				"bonus_flat": 0.0,
				"coeff_strength": 1.0,
				"coeff_dexterity": 1.0,
				"defense_modifier_attr": "dexterity",
				"defense_base_coeff": 1.0,
				"defense_attr_coeff": 1.0,
				"defense_flat_bonus": 0.0,
				"crit_on_20": True,
				"fail_on_1": True,
			},
			"magic_hit": {
				"bonus_flat": 0.0,
				"coeff_intelligence": 1.0,
				"coeff_advantage": 1.0,
				"defense_modifier_attr": None,
				"defense_base_coeff": 1.0,
				"defense_attr_coeff": 1.0,
				"defense_flat_bonus": 0.0,
			},
			"physical_damage": {
				"base_from_piece": True,
				"base_override": None,
				"flat_bonus": 0.0,
				"resist_mode": "subtract",
			},
			"magic_damage": {
				"base_from_piece": True,
				"base_override": None,
				"flat_bonus": 0.0,
				"resist_mode": "subtract",
			},
		},
		"spell_overrides": {},
	}


def ensure_action_settings_initialized(main_ui: Any) -> None:
	if not isinstance(main_ui.action_settings_snapshot, dict) or not main_ui.action_settings_snapshot:
		main_ui.action_settings_snapshot = default_action_settings_snapshot(main_ui)
	if "attack_model" not in main_ui.action_settings_snapshot:
		main_ui.action_settings_snapshot["attack_model"] = default_action_settings_snapshot(main_ui)["attack_model"]
	if "spell_overrides" not in main_ui.action_settings_snapshot:
		main_ui.action_settings_snapshot["spell_overrides"] = {}
	attack_model = main_ui.action_settings_snapshot.get("attack_model")
	if not isinstance(attack_model, dict):
		main_ui.action_settings_snapshot["attack_model"] = default_action_settings_snapshot(main_ui)["attack_model"]
		return
	if "hit" not in attack_model or not isinstance(attack_model.get("hit"), dict):
		attack_model["hit"] = default_action_settings_snapshot(main_ui)["attack_model"]["hit"]
	if "magic_hit" not in attack_model or not isinstance(attack_model.get("magic_hit"), dict):
		attack_model["magic_hit"] = default_action_settings_snapshot(main_ui)["attack_model"]["magic_hit"]
	if "physical_damage" not in attack_model or not isinstance(attack_model.get("physical_damage"), dict):
		attack_model["physical_damage"] = default_action_settings_snapshot(main_ui)["attack_model"]["physical_damage"]
	if "magic_damage" not in attack_model or not isinstance(attack_model.get("magic_damage"), dict):
		attack_model["magic_damage"] = default_action_settings_snapshot(main_ui)["attack_model"]["magic_damage"]

	hit = attack_model.get("hit")
	if isinstance(hit, dict):
		for k, v in (
			("defense_base_coeff", 1.0),
			("defense_attr_coeff", 1.0),
			("defense_flat_bonus", 0.0),
		):
			if k not in hit:
				hit[k] = v
	magic_hit = attack_model.get("magic_hit")
	if isinstance(magic_hit, dict):
		for k, v in (
			("defense_base_coeff", 1.0),
			("defense_attr_coeff", 1.0),
			("defense_flat_bonus", 0.0),
		):
			if k not in magic_hit:
				magic_hit[k] = v


def sync_action_settings_vars_from_snapshot(main_ui: Any) -> None:
	"""将 snapshot 同步到界面变量（仅用于属性设置-行动页）。"""
	from env import SpellFactory

	ensure_action_settings_initialized(main_ui)
	main_ui.action_attribute_internal_update = True
	try:
		attack_model = main_ui.action_settings_snapshot.get("attack_model", {})
		hit = attack_model.get("hit", {}) if isinstance(attack_model, dict) else {}
		magic_hit = attack_model.get("magic_hit", {}) if isinstance(attack_model, dict) else {}
		physical_damage = attack_model.get("physical_damage", {}) if isinstance(attack_model, dict) else {}
		magic_damage = attack_model.get("magic_damage", {}) if isinstance(attack_model, dict) else {}

		def _get_bool(d: dict[str, Any], key: str, default: bool) -> bool:
			val = d.get(key, default)
			return bool(val) if isinstance(val, (bool, int)) else default

		def _get_float(d: dict[str, Any], key: str, default: float) -> float:
			val = d.get(key, default)
			try:
				return float(val)
			except Exception:
				return float(default)

		main_ui.attribute_action_attack_vars.setdefault("enable_d20", tk.BooleanVar())
		main_ui.attribute_action_attack_vars.setdefault("hit_bonus_flat", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("hit_coeff_strength", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("hit_coeff_dexterity", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("magic_hit_bonus_flat", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("magic_hit_coeff_intelligence", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("magic_hit_coeff_advantage", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("phy_defense_modifier", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("phy_def_base_coeff", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("phy_def_attr_coeff", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("phy_def_flat_bonus", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("mag_defense_modifier", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("mag_def_base_coeff", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("mag_def_attr_coeff", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("mag_def_flat_bonus", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("hit_crit_on_20", tk.BooleanVar())
		main_ui.attribute_action_attack_vars.setdefault("hit_fail_on_1", tk.BooleanVar())
		main_ui.attribute_action_attack_vars.setdefault("phy_base_from_piece", tk.BooleanVar())
		main_ui.attribute_action_attack_vars.setdefault("phy_base_override", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("phy_flat_bonus", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("mag_base_from_piece", tk.BooleanVar())
		main_ui.attribute_action_attack_vars.setdefault("mag_base_override", tk.StringVar())
		main_ui.attribute_action_attack_vars.setdefault("mag_flat_bonus", tk.StringVar())

		attack_dict = attack_model if isinstance(attack_model, dict) else {}
		hit_dict = hit if isinstance(hit, dict) else {}
		magic_hit_dict = magic_hit if isinstance(magic_hit, dict) else {}
		phy_dict = physical_damage if isinstance(physical_damage, dict) else {}
		mag_dict = magic_damage if isinstance(magic_damage, dict) else {}

		# 顶层
		main_ui.attribute_action_attack_vars["enable_d20"].set(_get_bool(attack_dict, "enable_d20", True))

		# 命中
		main_ui.attribute_action_attack_vars["hit_bonus_flat"].set(str(_get_float(hit_dict, "bonus_flat", 0.0)))
		# 系数输入框允许留空=默认，因此这里不直接回填数值，只缓存默认值供公式显示与 apply 使用。
		main_ui.attribute_action_attack_defaults["hit_coeff_strength"] = _get_float(hit_dict, "coeff_strength", 1.0)
		# 这里的 coeff_dexterity 作为“优势值系数”使用（历史遗留字段名），默认取 1。
		main_ui.attribute_action_attack_defaults["hit_coeff_dexterity"] = _get_float(hit_dict, "coeff_dexterity", 1.0)
		main_ui.attribute_action_attack_vars["hit_coeff_strength"].set("")
		main_ui.attribute_action_attack_vars["hit_coeff_dexterity"].set("")
		main_ui.attribute_action_attack_vars["hit_crit_on_20"].set(_get_bool(hit_dict, "crit_on_20", True))
		main_ui.attribute_action_attack_vars["hit_fail_on_1"].set(_get_bool(hit_dict, "fail_on_1", True))
		phy_def_attr = hit_dict.get("defense_modifier_attr", "dexterity")
		phy_def_label = {
			None: "无",
			"": "无",
			"none": "无",
			"strength": "力量修正",
			"dexterity": "敏捷修正",
			"intelligence": "智力修正",
		}.get(
			phy_def_attr,
			"敏捷修正",
		)
		main_ui.attribute_action_attack_vars["phy_defense_modifier"].set(phy_def_label)
		main_ui.attribute_action_attack_defaults["phy_def_base_coeff"] = _get_float(hit_dict, "defense_base_coeff", 1.0)
		main_ui.attribute_action_attack_defaults["phy_def_attr_coeff"] = _get_float(hit_dict, "defense_attr_coeff", 1.0)
		main_ui.attribute_action_attack_defaults["phy_def_flat_bonus"] = _get_float(hit_dict, "defense_flat_bonus", 0.0)
		main_ui.attribute_action_attack_vars["phy_def_base_coeff"].set("")
		main_ui.attribute_action_attack_vars["phy_def_attr_coeff"].set("")
		main_ui.attribute_action_attack_vars["phy_def_flat_bonus"].set("")

		# 普通法术攻击命中
		main_ui.attribute_action_attack_vars["magic_hit_bonus_flat"].set(str(_get_float(magic_hit_dict, "bonus_flat", 0.0)))
		main_ui.attribute_action_attack_defaults["magic_hit_coeff_intelligence"] = _get_float(
			magic_hit_dict, "coeff_intelligence", 1.0
		)
		main_ui.attribute_action_attack_defaults["magic_hit_coeff_advantage"] = _get_float(
			magic_hit_dict, "coeff_advantage", 1.0
		)
		main_ui.attribute_action_attack_vars["magic_hit_coeff_intelligence"].set("")
		main_ui.attribute_action_attack_vars["magic_hit_coeff_advantage"].set("")
		mag_def_attr = magic_hit_dict.get("defense_modifier_attr", None)
		mag_def_label = {
			None: "无",
			"": "无",
			"none": "无",
			"strength": "力量修正",
			"dexterity": "敏捷修正",
			"intelligence": "智力修正",
		}.get(
			mag_def_attr,
			"无",
		)
		main_ui.attribute_action_attack_vars["mag_defense_modifier"].set(mag_def_label)
		main_ui.attribute_action_attack_defaults["mag_def_base_coeff"] = _get_float(
			magic_hit_dict, "defense_base_coeff", 1.0
		)
		main_ui.attribute_action_attack_defaults["mag_def_attr_coeff"] = _get_float(
			magic_hit_dict, "defense_attr_coeff", 1.0
		)
		main_ui.attribute_action_attack_defaults["mag_def_flat_bonus"] = _get_float(
			magic_hit_dict, "defense_flat_bonus", 0.0
		)
		main_ui.attribute_action_attack_vars["mag_def_base_coeff"].set("")
		main_ui.attribute_action_attack_vars["mag_def_attr_coeff"].set("")
		main_ui.attribute_action_attack_vars["mag_def_flat_bonus"].set("")

		# 物理伤害
		main_ui.attribute_action_attack_vars["phy_base_from_piece"].set(_get_bool(phy_dict, "base_from_piece", True))
		phy_base_override = phy_dict.get("base_override") if isinstance(phy_dict, dict) else None
		main_ui.attribute_action_attack_vars["phy_base_override"].set("" if phy_base_override is None else str(phy_base_override))
		main_ui.attribute_action_attack_vars["phy_flat_bonus"].set(str(_get_float(phy_dict, "flat_bonus", 0.0)))
		# 伤害系数（力量/敏捷）不参与后端真实伤害结算，已从 UI 收敛移除。

		# 普通法术攻击伤害
		main_ui.attribute_action_attack_vars["mag_base_from_piece"].set(_get_bool(mag_dict, "base_from_piece", True))
		mag_base_override = mag_dict.get("base_override") if isinstance(mag_dict, dict) else None
		main_ui.attribute_action_attack_vars["mag_base_override"].set("" if mag_base_override is None else str(mag_base_override))
		main_ui.attribute_action_attack_vars["mag_flat_bonus"].set(str(_get_float(mag_dict, "flat_bonus", 0.0)))
		# 伤害系数（智力）不参与后端真实伤害结算，已从 UI 收敛移除。

		# 法术覆盖
		overrides = main_ui.action_settings_snapshot.get("spell_overrides", {})
		if not isinstance(overrides, dict):
			overrides = {}
		for spell in SpellFactory.get_all_spells():
			sid = int(getattr(spell, "id", 0))
			if sid <= 0:
				continue
			override = overrides.get(str(sid)) or overrides.get(sid)
			enabled = isinstance(override, dict)
			main_ui.attribute_action_spell_enable_vars.setdefault(sid, tk.BooleanVar(value=enabled))
			vars_map = main_ui.attribute_action_spell_vars.setdefault(
				sid,
				{
					"base_value": tk.StringVar(),
					"range": tk.StringVar(),
					"area_radius": tk.StringVar(),
					"spell_cost": tk.StringVar(),
					"base_lifespan": tk.StringVar(),
				},
			)
			def_val = {
				"base_value": int(getattr(spell, "base_value", 0)),
				"range": int(getattr(spell, "range", 0)),
				"area_radius": int(getattr(spell, "area_radius", 0)),
				"spell_cost": int(getattr(spell, "spell_cost", 0)),
				"base_lifespan": int(getattr(spell, "base_lifespan", 0)),
			}
			if isinstance(override, dict):
				for k in list(def_val.keys()):
					if k in override:
						try:
							def_val[k] = int(float(override.get(k)))
						except Exception:
							pass
			for k, v in def_val.items():
				vars_map[k].set(str(v))
	finally:
		main_ui.action_attribute_internal_update = False


def collect_action_settings_snapshot_from_vars(main_ui: Any) -> dict[str, Any]:
	"""从界面变量读取配置，生成 snapshot（不接入后端，仅测试端内存保存）。"""
	from env import SpellFactory

	ensure_action_settings_initialized(main_ui)

	def _bool(key: str, default: bool = False) -> bool:
		var = main_ui.attribute_action_attack_vars.get(key)
		if var is None:
			return default
		try:
			return bool(var.get())
		except Exception:
			return default

	def _float(key: str, default: float = 0.0) -> float:
		var = main_ui.attribute_action_attack_vars.get(key)
		if var is None:
			return default
		return main_ui._safe_float(str(var.get()), default)

	def _float_or_default_from_blank(key: str, default: float) -> float:
		var = main_ui.attribute_action_attack_vars.get(key)
		if var is None:
			return default
		raw = str(var.get()).strip()
		if raw == "":
			return default
		return main_ui._safe_float(raw, default)

	phy_base_from_piece = _bool("phy_base_from_piece", True)
	phy_base_override_raw = (
		str(main_ui.attribute_action_attack_vars.get("phy_base_override").get()).strip()
		if main_ui.attribute_action_attack_vars.get("phy_base_override")
		else ""
	)
	phy_base_override: float | None
	if (not phy_base_from_piece) and phy_base_override_raw == "":
		raise ValueError("物理攻击伤害：请填写“覆盖基础值”，或勾选“以棋子物伤作为原伤害基础值”。")
	if phy_base_override_raw == "":
		phy_base_override = None
	else:
		phy_base_override = main_ui._safe_float(phy_base_override_raw, 0.0)
	if phy_base_from_piece:
		phy_base_override = None

	mag_base_from_piece = _bool("mag_base_from_piece", True)
	mag_base_override_raw = (
		str(main_ui.attribute_action_attack_vars.get("mag_base_override").get()).strip()
		if main_ui.attribute_action_attack_vars.get("mag_base_override")
		else ""
	)
	mag_base_override: float | None
	if (not mag_base_from_piece) and mag_base_override_raw == "":
		raise ValueError("普通法术攻击伤害：请填写“覆盖基础值”，或勾选“以棋子法伤作为原伤害基础值”。")
	if mag_base_override_raw == "":
		mag_base_override = None
	else:
		mag_base_override = main_ui._safe_float(mag_base_override_raw, 0.0)
	if mag_base_from_piece:
		mag_base_override = None

	snapshot: dict[str, Any] = {
		"attack_model": {
			"enable_d20": _bool("enable_d20", True),
			"hit": {
				"bonus_flat": _float("hit_bonus_flat", 0.0),
				"coeff_strength": _float_or_default_from_blank(
					"hit_coeff_strength",
					float(main_ui.attribute_action_attack_defaults.get("hit_coeff_strength", 1.0)),
				),
				"coeff_dexterity": _float_or_default_from_blank(
					"hit_coeff_dexterity",
					float(main_ui.attribute_action_attack_defaults.get("hit_coeff_dexterity", 1.0)),
				),
				"defense_modifier_attr": None,
				"defense_base_coeff": _float_or_default_from_blank(
					"phy_def_base_coeff",
					float(main_ui.attribute_action_attack_defaults.get("phy_def_base_coeff", 1.0)),
				),
				"defense_attr_coeff": _float_or_default_from_blank(
					"phy_def_attr_coeff",
					float(main_ui.attribute_action_attack_defaults.get("phy_def_attr_coeff", 1.0)),
				),
				"defense_flat_bonus": _float_or_default_from_blank(
					"phy_def_flat_bonus",
					float(main_ui.attribute_action_attack_defaults.get("phy_def_flat_bonus", 0.0)),
				),
				"crit_on_20": _bool("hit_crit_on_20", True),
				"fail_on_1": _bool("hit_fail_on_1", True),
			},
			"magic_hit": {
				"bonus_flat": _float("magic_hit_bonus_flat", 0.0),
				"coeff_intelligence": _float_or_default_from_blank(
					"magic_hit_coeff_intelligence",
					float(main_ui.attribute_action_attack_defaults.get("magic_hit_coeff_intelligence", 1.0)),
				),
				"coeff_advantage": _float_or_default_from_blank(
					"magic_hit_coeff_advantage",
					float(main_ui.attribute_action_attack_defaults.get("magic_hit_coeff_advantage", 1.0)),
				),
				"defense_modifier_attr": None,
				"defense_base_coeff": _float_or_default_from_blank(
					"mag_def_base_coeff",
					float(main_ui.attribute_action_attack_defaults.get("mag_def_base_coeff", 1.0)),
				),
				"defense_attr_coeff": _float_or_default_from_blank(
					"mag_def_attr_coeff",
					float(main_ui.attribute_action_attack_defaults.get("mag_def_attr_coeff", 1.0)),
				),
				"defense_flat_bonus": _float_or_default_from_blank(
					"mag_def_flat_bonus",
					float(main_ui.attribute_action_attack_defaults.get("mag_def_flat_bonus", 0.0)),
				),
			},
			"physical_damage": {
				"base_from_piece": phy_base_from_piece,
				"base_override": phy_base_override,
				"flat_bonus": _float("phy_flat_bonus", 0.0),
				"resist_mode": "subtract",
			},
			"magic_damage": {
				"base_from_piece": mag_base_from_piece,
				"base_override": mag_base_override,
				"flat_bonus": _float("mag_flat_bonus", 0.0),
				"resist_mode": "subtract",
			},
		},
		"spell_overrides": {},
	}

	def _def_mod_to_key(label: str, default_key: str | None) -> str | None:
		label = str(label or "").strip()
		mapping = {
			"无": None,
			"力量修正": "strength",
			"敏捷修正": "dexterity",
			"智力修正": "intelligence",
		}
		return mapping.get(label, default_key)

	phy_def_label = ""
	mag_def_label = ""
	try:
		phy_def_label = str(main_ui.attribute_action_attack_vars.get("phy_defense_modifier").get()).strip()
	except Exception:
		phy_def_label = ""
	try:
		mag_def_label = str(main_ui.attribute_action_attack_vars.get("mag_defense_modifier").get()).strip()
	except Exception:
		mag_def_label = ""

	snapshot["attack_model"]["hit"]["defense_modifier_attr"] = _def_mod_to_key(phy_def_label, "dexterity")
	snapshot["attack_model"]["magic_hit"]["defense_modifier_attr"] = _def_mod_to_key(mag_def_label, None)

	spell_overrides: dict[str, dict[str, int]] = {}
	for spell in SpellFactory.get_all_spells():
		sid = int(getattr(spell, "id", 0))
		if sid <= 0:
			continue
		enable_var = main_ui.attribute_action_spell_enable_vars.get(sid)
		if enable_var is None:
			continue
		try:
			enabled = bool(enable_var.get())
		except Exception:
			enabled = False
		if not enabled:
			continue
		vars_map = main_ui.attribute_action_spell_vars.get(sid, {})
		override: dict[str, int] = {}
		for key in ("base_value", "range", "area_radius", "spell_cost", "base_lifespan"):
			var = vars_map.get(key)
			if var is None:
				continue
			override[key] = main_ui._safe_int(str(var.get()), 0)
		spell_overrides[str(sid)] = override
	snapshot["spell_overrides"] = spell_overrides
	return snapshot


def show_action_apply_feedback(main_ui: Any, message: str) -> None:
	label = main_ui.attribute_action_apply_status_label
	if label is None or not label.winfo_exists():
		return
	label.configure(text=message, foreground="#059669")

	def _clear() -> None:
		try:
			if label.winfo_exists():
				label.configure(text="")
		except Exception:
			pass

	main_ui.root.after(2000, _clear)


def show_action_warning_feedback(main_ui: Any, message: str) -> None:
	label = main_ui.attribute_action_warning_label
	if label is None or not label.winfo_exists():
		return
	label.configure(text=message, foreground="#b45309")

	def _clear() -> None:
		try:
			if label.winfo_exists():
				label.configure(text="")
		except Exception:
			pass

	main_ui.root.after(5000, _clear)


def apply_action_attribute_changes(main_ui: Any) -> None:
	"""应用行动属性（本局临时生效）：运行时猴子补丁覆写 env 公式，不改后端文件。"""
	try:
		snapshot = collect_action_settings_snapshot_from_vars(main_ui)
		main_ui.action_settings_snapshot = snapshot
		# 先放入 controller 的 custom_config，便于后续在逻辑层统一取配置。
		try:
			main_ui.controller.apply_environment_config({"action_settings": snapshot})
		except Exception:
			pass
		apply_action_settings_to_runtime_environment(main_ui, snapshot)
		main_ui.right_info_panel.append_content("\n[UI] 行动属性已应用（本局临时生效）：攻击模型 + 法术数值覆盖")
		show_action_apply_feedback(main_ui, "应用成功")
	except Exception as e:
		show_action_warning_feedback(main_ui, f"应用失败：{e}")
		main_ui.right_info_panel.append_content(f"\n[UI] 行动属性应用失败: {e}")


def reset_action_attribute_to_defaults(main_ui: Any) -> None:
	main_ui.action_settings_snapshot = default_action_settings_snapshot(main_ui)
	sync_action_settings_vars_from_snapshot(main_ui)
	for _sid, var in main_ui.attribute_action_spell_enable_vars.items():
		try:
			var.set(False)
		except Exception:
			pass
	apply_action_settings_to_runtime_environment(main_ui, main_ui.action_settings_snapshot)
	show_action_apply_feedback(main_ui, "已恢复默认")


def apply_action_settings_to_runtime_environment(main_ui: Any, snapshot: dict[str, Any]) -> None:
	"""将行动属性设置注入到 runtime env（仅本局内存生效）。"""
	if main_ui.controller.runtime_source != "runtime_env":
		return
	env = getattr(main_ui.controller, "environment", None)
	if env is None:
		return
	# 存到 env 上，供钩子读取。
	setattr(env, "_ui_action_settings_snapshot", snapshot if isinstance(snapshot, dict) else {})
	if bool(getattr(env, "_ui_action_settings_hook_installed", False)):
		return
	setattr(env, "_ui_action_settings_hook_installed", True)
	default_snapshot = default_action_settings_snapshot(main_ui)

	orig_execute_attack = getattr(env, "execute_attack", None)
	orig_get_available_spells = getattr(env, "get_available_spells", None)
	if callable(orig_execute_attack):
		setattr(env, "_ui_orig_execute_attack", orig_execute_attack)
	if callable(orig_get_available_spells):
		setattr(env, "_ui_orig_get_available_spells", orig_get_available_spells)

	def _get_snapshot() -> dict[str, Any]:
		snap = getattr(env, "_ui_action_settings_snapshot", None)
		return snap if isinstance(snap, dict) else default_snapshot

	def _step_mod(_stat_name: str | None, value: Any) -> int:
		"""读取阶梯值：保持与后端一致，直接使用 env.step_modified_func。"""
		try:
			num = int(value)
		except Exception:
			num = 0

		step_func = getattr(env, "step_modified_func", None)
		if callable(step_func):
			try:
				return int(step_func(int(num)))
			except Exception:
				return 0
		return 0

	def _adv_value(attacker: Any, target: Any) -> float:
		adv_func = getattr(env, "calculate_advantage_value", None)
		if callable(adv_func):
			try:
				return float(adv_func(attacker, target))
			except Exception:
				return 0.0
		return 0.0

	def execute_attack_hook(attack_context: Any):
		# 仅覆盖“物理攻击”的命中与伤害；其余逻辑保持与原 env 一致（AP、范围等）。
		try:
			attacker = getattr(attack_context, "attacker", None)
			target = getattr(attack_context, "target", None)
			if attacker is None or target is None:
				return
			if int(getattr(attacker, "action_points", 0)) <= 0:
				return
			if not bool(getattr(attacker, "is_alive", True)) or int(getattr(attacker, "health", 0)) <= 0:
				return
			# 濒死系统：濒死（HP=0）目标允许被攻击（“再受伤直接判死”由 test_mock_gameplay 处理）。
			near_cfg = getattr(env, "_ui_near_death_config", None)
			near_enabled = bool(near_cfg.get("enabled")) if isinstance(near_cfg, dict) else False
			attacker_dying = bool(getattr(attacker, "is_dying", False))
			if attacker_dying and int(getattr(attacker, "health", 0)) <= 0:
				return
			target_alive = bool(getattr(target, "is_alive", True))
			target_hp = int(getattr(target, "health", 0))
			target_dying = bool(getattr(target, "is_dying", False))
			if (not target_alive) or (target_hp <= 0 and not (near_enabled and target_dying and target_hp == 0)):
				return
			if not bool(getattr(env, "is_in_attack_range", lambda a, t: True)(attacker, target)):
				return

			snap = _get_snapshot()
			attack_model = snap.get("attack_model", {}) if isinstance(snap, dict) else {}
			enable_d20 = bool(attack_model.get("enable_d20", True))
			hit_cfg = attack_model.get("hit", {}) if isinstance(attack_model.get("hit"), dict) else {}
			dmg_cfg = attack_model.get("physical_damage", {}) if isinstance(attack_model.get("physical_damage"), dict) else {}

			roll_value = 0
			if enable_d20 and callable(getattr(env, "roll_dice", None)):
				try:
					roll_value = int(getattr(env, "roll_dice")(1, 20))
				except Exception:
					roll_value = 0

			fail_on_1 = bool(hit_cfg.get("fail_on_1", True))
			crit_on_20 = bool(hit_cfg.get("crit_on_20", True))
			bonus_flat = float(hit_cfg.get("bonus_flat", 0.0) or 0.0)
			coeff_strength = float(hit_cfg.get("coeff_strength", 1.0) or 1.0)
			adv_coeff = float(hit_cfg.get("coeff_dexterity", 1.0) or 1.0)

			def_attr = hit_cfg.get("defense_modifier_attr", "dexterity")
			def_base_coeff = float(hit_cfg.get("defense_base_coeff", 1.0) or 1.0)
			def_attr_coeff = float(hit_cfg.get("defense_attr_coeff", 1.0) or 1.0)
			def_flat_bonus = float(hit_cfg.get("defense_flat_bonus", 0.0) or 0.0)

			is_critical = False
			if enable_d20 and roll_value == 1 and fail_on_1:
				is_hit = False
			elif enable_d20 and roll_value == 20 and crit_on_20:
				is_hit = True
				is_critical = True
			else:
				adv = _adv_value(attacker, target)
				attack_score = (
					float(roll_value)
					+ bonus_flat
					+ coeff_strength * float(_step_mod("strength", getattr(attacker, "strength", 0)))
					+ adv_coeff * float(adv)
				)
				base_def = float(getattr(target, "physical_resist", 0))
				attr_def = 0.0
				if def_attr not in (None, "", "none"):
					attr_def = float(_step_mod(str(def_attr), getattr(target, str(def_attr), 0)))
				defense_score = def_base_coeff * base_def + def_attr_coeff * attr_def + def_flat_bonus
				is_hit = bool(attack_score > defense_score)

			# 命中才结算伤害
			setattr(attack_context, "damage_dealt", 0)
			if is_hit:
				base_from_piece = bool(dmg_cfg.get("base_from_piece", True))
				base_override = dmg_cfg.get("base_override", None)
				flat_bonus = float(dmg_cfg.get("flat_bonus", 0.0) or 0.0)
				if base_from_piece:
					base = float(getattr(attacker, "physical_damage", 0))
				else:
					try:
						base = float(base_override) if base_override is not None else 0.0
					except Exception:
						base = 0.0
				damage = max(0, base + flat_bonus)
				if is_critical:
					damage *= 2
				int_damage = int(round(damage))
				try:
					target.receive_damage(int_damage, "physical")
				except Exception:
					try:
						old_hp = int(getattr(target, "health", 0))
						setattr(target, "health", old_hp - int_damage)
					except Exception:
						pass
				# 夹到 0，避免出现负血。
				try:
					cur_hp = int(getattr(target, "health", 0))
				except Exception:
					cur_hp = 0
				if cur_hp < 0:
					try:
						target.get_accessor().set_health_to(0)
					except Exception:
						setattr(target, "health", 0)
					cur_hp = 0
				setattr(attack_context, "damage_dealt", int_damage)
				if cur_hp == 0 and callable(getattr(env, "handle_death_check", None)):
					env.handle_death_check(target)

			# 消耗 AP
			try:
				attacker.get_accessor().change_action_points_by(-1)
			except Exception:
				setattr(attacker, "action_points", int(getattr(attacker, "action_points", 0)) - 1)
		except Exception:
			# 回退：若 hook 出错，尽量调用原实现。
			orig = getattr(env, "_ui_orig_execute_attack", None)
			if callable(orig):
				return orig(attack_context)
			return

	def get_available_spells_hook(piece: Any = None):
		orig = getattr(env, "_ui_orig_get_available_spells", None)
		if not callable(orig):
			return []
		spells = [s for s in main_ui._coerce_piece_list(orig(piece)) if s is not None]
		snap = _get_snapshot()
		overrides = snap.get("spell_overrides", {}) if isinstance(snap, dict) else {}
		if not isinstance(overrides, dict) or not overrides:
			return spells
		out: list[Any] = []
		for spell in spells:
			sid = getattr(spell, "id", None)
			key1 = str(sid) if sid is not None else ""
			override = overrides.get(key1) or overrides.get(sid)
			if not isinstance(override, dict):
				out.append(spell)
				continue
			try:
				new_spell = copy.copy(spell)
			except Exception:
				new_spell = spell
			for k, attr_name in (
				("base_value", "base_value"),
				("range", "range"),
				("area_radius", "area_radius"),
				("spell_cost", "spell_cost"),
				("base_lifespan", "base_lifespan"),
			):
				if k not in override:
					continue
				try:
					setattr(new_spell, attr_name, int(float(override.get(k))))
				except Exception:
					pass
			out.append(new_spell)
		return out

	# 安装 hook
	setattr(env, "execute_attack", execute_attack_hook)
	setattr(env, "get_available_spells", get_available_spells_hook)


def build_attribute_action_page(main_ui: Any, content: ttk.LabelFrame) -> None:
	"""构建行动属性页：仅用于调参（已实现、非自定义行动）。"""
	from env import SpellFactory

	sync_action_settings_vars_from_snapshot(main_ui)

	wrapper = ttk.Frame(content)
	wrapper.grid(row=0, column=0, sticky="nsew")
	wrapper.columnconfigure(0, weight=1)
	wrapper.rowconfigure(2, weight=1)

	ttk.Label(wrapper, text="行动属性", font=("Microsoft YaHei UI", 12, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 6)
	)
	note = (
		"用于修改已实现（非自定义）行动的数值：攻击模型、法术模板参数。\n"
		"点击“应用（本局）”即生效（仅本局内存）；关闭程序即清空。"
	)
	ttk.Label(wrapper, text=note, foreground="#4b5563", justify="left", wraplength=640).grid(
		row=1, column=0, sticky="w", pady=(0, 8)
	)

	# Notebook（攻击/法术）冻结：tab 选择条不随内容滚动。
	nb = ttk.Notebook(wrapper)
	nb.grid(row=2, column=0, sticky="nsew")

	active_scroll_canvas: dict[str, Any] = {"canvas": None}

	def _on_mousewheel(event: Any) -> None:
		canvas = active_scroll_canvas.get("canvas")
		if canvas is None or (hasattr(canvas, "winfo_exists") and not canvas.winfo_exists()):
			return
		try:
			delta = int(getattr(event, "delta", 0))
			if delta == 0:
				return
		except Exception:
			return
		# 内容不足一屏时，不滚动，避免出现“空白滚动”。
		try:
			sr = str(canvas.cget("scrollregion") or "").strip()
			parts = [float(x) for x in sr.split()] if sr else []
			content_h = float(parts[3] - parts[1]) if len(parts) == 4 else 0.0
			view_h = float(canvas.winfo_height())
			if content_h <= view_h + 2:
				return
		except Exception:
			pass
		try:
			canvas.yview_scroll(-int(delta / 120), "units")
			# 夹紧到顶/底，避免能滚到无内容区域。
			first, last = canvas.yview()
			if first < 0:
				canvas.yview_moveto(0)
			elif last > 1:
				span = max(1e-9, last - first)
				canvas.yview_moveto(max(0.0, 1.0 - span))
		except Exception:
			return

	wrapper.bind_all("<MouseWheel>", _on_mousewheel)
	wrapper.bind("<Destroy>", lambda _e: wrapper.unbind_all("<MouseWheel>"))

	attack_tab = ttk.Frame(nb)
	spell_tab = ttk.Frame(nb)
	nb.add(attack_tab, text="攻击")
	nb.add(spell_tab, text="法术")

	# --- 攻击 TAB ---
	attack_tab.columnconfigure(0, weight=1)
	attack_tab.rowconfigure(0, weight=1)

	attack_scroll_host = ttk.Frame(attack_tab)
	attack_scroll_host.grid(row=0, column=0, sticky="nsew")
	attack_scroll_host.columnconfigure(0, weight=1)
	attack_scroll_host.rowconfigure(0, weight=1)

	attack_canvas = tk.Canvas(attack_scroll_host, highlightthickness=0, borderwidth=0)
	attack_v_scroll = ttk.Scrollbar(attack_scroll_host, orient="vertical", command=attack_canvas.yview)
	attack_canvas.configure(yscrollcommand=attack_v_scroll.set)
	attack_canvas.grid(row=0, column=0, sticky="nsew")
	attack_v_scroll.grid(row=0, column=1, sticky="ns")

	attack_content = ttk.Frame(attack_canvas, padding=10)
	attack_canvas_window = attack_canvas.create_window((0, 0), window=attack_content, anchor="nw")
	attack_content.columnconfigure(0, weight=1)

	def _sync_attack_scroll_region(_event: Any = None) -> None:
		try:
			attack_content.update_idletasks()
			req_w = int(attack_content.winfo_reqwidth())
			req_h = int(attack_content.winfo_reqheight())
			attack_canvas.configure(scrollregion=(0, 0, max(req_w, 1), max(req_h, 1)))
		except Exception:
			attack_canvas.configure(scrollregion=attack_canvas.bbox("all"))

	def _fit_attack_content_width(event: Any) -> None:
		attack_canvas.itemconfigure(attack_canvas_window, width=int(event.width))

	attack_content.bind("<Configure>", _sync_attack_scroll_region)
	attack_canvas.bind("<Configure>", _fit_attack_content_width)
	attack_canvas.bind("<Enter>", lambda _e: active_scroll_canvas.__setitem__("canvas", attack_canvas))
	attack_content.bind("<Enter>", lambda _e: active_scroll_canvas.__setitem__("canvas", attack_canvas))
	active_scroll_canvas["canvas"] = attack_canvas

	# 公式显示帮助：系数输入框可留空，表示使用默认系数。
	helper = "说明：公式中的【系数】输入框可以留空，表示使用默认系数值。"
	ttk.Label(attack_content, text=helper, foreground="#4b5563").grid(row=0, column=0, sticky="w", pady=(0, 8))

	# ---- 命中判定 ----
	hit_box = ttk.LabelFrame(attack_content, text="命中判定", padding=10)
	hit_box.grid(row=1, column=0, sticky="ew")
	hit_box.columnconfigure(0, weight=1)

	rule_note = "说明：\n- 优势值 = 2×(攻击者高度-受击者高度) + 3×(攻击者环境值-受击者环境值)\n- 环境值：不在任何延时法术/BUFF 中为 0；处在伤害法术范围为 -1；处在 BUFF 范围为 +1（可叠加）"
	ttk.Label(hit_box, text=rule_note, foreground="#4b5563", justify="left", wraplength=640).grid(
		row=0, column=0, sticky="w"
	)

	phy_hit_formula_var = tk.StringVar(value="")
	mag_hit_formula_var = tk.StringVar(value="")
	ttk.Label(hit_box, text="物理攻击：", font=("Microsoft YaHei UI", 10, "bold")).grid(
		row=1, column=0, sticky="w", pady=(8, 0)
	)
	ttk.Label(hit_box, textvariable=phy_hit_formula_var, justify="left", wraplength=640).grid(
		row=2, column=0, sticky="w"
	)

	hit_edit = ttk.Frame(hit_box)
	hit_edit.grid(row=3, column=0, sticky="w", pady=(8, 0))
	ttk.Checkbutton(hit_edit, text="启用 d20", variable=main_ui.attribute_action_attack_vars["enable_d20"]).grid(
		row=0, column=0, sticky="w", padx=(0, 14)
	)
	ttk.Checkbutton(hit_edit, text="d20=20 大成功", variable=main_ui.attribute_action_attack_vars["hit_crit_on_20"]).grid(
		row=0, column=1, sticky="w", padx=(0, 14)
	)
	ttk.Checkbutton(hit_edit, text="d20=1 大失败", variable=main_ui.attribute_action_attack_vars["hit_fail_on_1"]).grid(
		row=0, column=2, sticky="w"
	)

	hit_line = ttk.Frame(hit_box)
	hit_line.grid(row=4, column=0, sticky="w", pady=(8, 0))
	ttk.Label(hit_line, text="攻击投掷 = ").grid(row=0, column=0, sticky="w")
	ttk.Label(hit_line, text="d20 +").grid(row=0, column=1, sticky="w")
	tk.Entry(hit_line, textvariable=main_ui.attribute_action_attack_vars["hit_coeff_strength"], width=7).grid(
		row=0, column=2, sticky="w", padx=(6, 4)
	)
	ttk.Label(hit_line, text="×力量修正 +").grid(row=0, column=3, sticky="w")
	tk.Entry(hit_line, textvariable=main_ui.attribute_action_attack_vars["hit_coeff_dexterity"], width=7).grid(
		row=0, column=4, sticky="w", padx=(6, 4)
	)
	ttk.Label(hit_line, text="×优势值 + 固定加值").grid(row=0, column=5, sticky="w")
	tk.Entry(hit_line, textvariable=main_ui.attribute_action_attack_vars["hit_bonus_flat"], width=8).grid(
		row=0, column=6, sticky="w", padx=(6, 0)
	)

	phy_def_line = ttk.Frame(hit_box)
	phy_def_line.grid(row=5, column=0, sticky="w", pady=(8, 0))
	ttk.Label(phy_def_line, text="豁免值 = ").grid(row=0, column=0, sticky="w")
	tk.Entry(phy_def_line, textvariable=main_ui.attribute_action_attack_vars["phy_def_base_coeff"], width=7).grid(
		row=0, column=1, sticky="w", padx=(6, 4)
	)
	ttk.Label(phy_def_line, text="×目标物理豁免值(物抗) +").grid(row=0, column=2, sticky="w")
	tk.Entry(phy_def_line, textvariable=main_ui.attribute_action_attack_vars["phy_def_attr_coeff"], width=7).grid(
		row=0, column=3, sticky="w", padx=(6, 4)
	)
	ttk.Label(phy_def_line, text="×").grid(row=0, column=4, sticky="w")
	def_mod_values = ["无", "力量修正", "敏捷修正", "智力修正"]
	phy_def_combo = ttk.Combobox(
		phy_def_line,
		textvariable=main_ui.attribute_action_attack_vars["phy_defense_modifier"],
		values=def_mod_values,
		state="readonly",
		width=10,
	)
	phy_def_combo.grid(row=0, column=5, sticky="w", padx=(6, 18))
	ttk.Label(phy_def_line, text="+ 固定加值").grid(row=0, column=6, sticky="w")
	tk.Entry(phy_def_line, textvariable=main_ui.attribute_action_attack_vars["phy_def_flat_bonus"], width=8).grid(
		row=0, column=7, sticky="w", padx=(6, 0)
	)

	ttk.Label(hit_box, text="普通法术攻击：", font=("Microsoft YaHei UI", 10, "bold")).grid(
		row=6, column=0, sticky="w", pady=(10, 0)
	)
	ttk.Label(hit_box, textvariable=mag_hit_formula_var, justify="left", wraplength=640).grid(
		row=7, column=0, sticky="w"
	)

	mag_hit_line = ttk.Frame(hit_box)
	mag_hit_line.grid(row=8, column=0, sticky="w", pady=(8, 0))
	ttk.Label(mag_hit_line, text="攻击投掷 = ").grid(row=0, column=0, sticky="w")
	ttk.Label(mag_hit_line, text="d20 +").grid(row=0, column=1, sticky="w")
	tk.Entry(mag_hit_line, textvariable=main_ui.attribute_action_attack_vars["magic_hit_coeff_intelligence"], width=7).grid(
		row=0, column=2, sticky="w", padx=(6, 4)
	)
	ttk.Label(mag_hit_line, text="×智力修正 +").grid(row=0, column=3, sticky="w")
	tk.Entry(mag_hit_line, textvariable=main_ui.attribute_action_attack_vars["magic_hit_coeff_advantage"], width=7).grid(
		row=0, column=4, sticky="w", padx=(6, 4)
	)
	ttk.Label(mag_hit_line, text="×优势值 + 固定加值").grid(row=0, column=5, sticky="w")
	tk.Entry(mag_hit_line, textvariable=main_ui.attribute_action_attack_vars["magic_hit_bonus_flat"], width=8).grid(
		row=0, column=6, sticky="w", padx=(6, 0)
	)

	mag_def_line = ttk.Frame(hit_box)
	mag_def_line.grid(row=9, column=0, sticky="w", pady=(8, 0))
	ttk.Label(mag_def_line, text="豁免值 = ").grid(row=0, column=0, sticky="w")
	tk.Entry(mag_def_line, textvariable=main_ui.attribute_action_attack_vars["mag_def_base_coeff"], width=7).grid(
		row=0, column=1, sticky="w", padx=(6, 4)
	)
	ttk.Label(mag_def_line, text="×目标法术豁免值(法抗) +").grid(row=0, column=2, sticky="w")
	tk.Entry(mag_def_line, textvariable=main_ui.attribute_action_attack_vars["mag_def_attr_coeff"], width=7).grid(
		row=0, column=3, sticky="w", padx=(6, 4)
	)
	ttk.Label(mag_def_line, text="×").grid(row=0, column=4, sticky="w")
	mag_def_combo = ttk.Combobox(
		mag_def_line,
		textvariable=main_ui.attribute_action_attack_vars["mag_defense_modifier"],
		values=def_mod_values,
		state="readonly",
		width=10,
	)
	mag_def_combo.grid(row=0, column=5, sticky="w", padx=(6, 18))
	ttk.Label(mag_def_line, text="+ 固定加值").grid(row=0, column=6, sticky="w")
	tk.Entry(mag_def_line, textvariable=main_ui.attribute_action_attack_vars["mag_def_flat_bonus"], width=8).grid(
		row=0, column=7, sticky="w", padx=(6, 0)
	)

	# ---- 物理攻击伤害 ----
	phy_box = ttk.LabelFrame(attack_content, text="物理攻击伤害", padding=10)
	phy_box.grid(row=2, column=0, sticky="ew", pady=(10, 0))
	phy_box.columnconfigure(0, weight=1)

	phy_template_var = tk.StringVar(value="")
	phy_effective_var = tk.StringVar(value="")
	ttk.Label(phy_box, textvariable=phy_template_var, justify="left", wraplength=640).grid(
		row=0, column=0, sticky="w"
	)
	ttk.Label(phy_box, textvariable=phy_effective_var, justify="left", wraplength=640).grid(
		row=1, column=0, sticky="w", pady=(4, 0)
	)

	phy_line = ttk.Frame(phy_box)
	phy_line.grid(row=2, column=0, sticky="w", pady=(8, 0))
	ttk.Checkbutton(
		phy_line,
		text="以棋子物伤作为原伤害基础值",
		variable=main_ui.attribute_action_attack_vars["phy_base_from_piece"],
	).grid(row=0, column=0, sticky="w", padx=(0, 12))
	ttk.Label(phy_line, text="覆盖基础值(未勾选时必填)").grid(row=0, column=1, sticky="w")
	phy_base_override_entry = tk.Entry(
		phy_line,
		textvariable=main_ui.attribute_action_attack_vars["phy_base_override"],
		width=10,
	)
	phy_base_override_entry.grid(
		row=0, column=2, sticky="w", padx=(6, 12)
	)
	ttk.Label(phy_line, text="固定加值").grid(row=0, column=3, sticky="w")
	tk.Entry(phy_line, textvariable=main_ui.attribute_action_attack_vars["phy_flat_bonus"], width=8).grid(
		row=0, column=4, sticky="w", padx=(6, 0)
	)

	phy_line2 = ttk.Frame(phy_box)
	phy_line2.grid(row=3, column=0, sticky="w", pady=(8, 0))
	ttk.Label(phy_line2, text="原始伤害 = 基础值 + 固定加值").grid(row=0, column=0, sticky="w")

	# ---- 普通法术攻击伤害 ----
	mag_box = ttk.LabelFrame(attack_content, text="普通法术攻击伤害", padding=10)
	mag_box.grid(row=3, column=0, sticky="ew", pady=(10, 0))
	mag_box.columnconfigure(0, weight=1)

	mag_template_var = tk.StringVar(value="")
	mag_effective_var = tk.StringVar(value="")
	ttk.Label(mag_box, textvariable=mag_template_var, justify="left", wraplength=640).grid(
		row=0, column=0, sticky="w"
	)
	ttk.Label(mag_box, textvariable=mag_effective_var, justify="left", wraplength=640).grid(
		row=1, column=0, sticky="w", pady=(4, 0)
	)

	mag_line = ttk.Frame(mag_box)
	mag_line.grid(row=2, column=0, sticky="w", pady=(8, 0))
	ttk.Checkbutton(
		mag_line,
		text="以棋子法伤作为原伤害基础值",
		variable=main_ui.attribute_action_attack_vars["mag_base_from_piece"],
	).grid(row=0, column=0, sticky="w", padx=(0, 12))
	ttk.Label(mag_line, text="覆盖基础值(未勾选时必填)").grid(row=0, column=1, sticky="w")
	mag_base_override_entry = tk.Entry(
		mag_line,
		textvariable=main_ui.attribute_action_attack_vars["mag_base_override"],
		width=10,
	)
	mag_base_override_entry.grid(
		row=0, column=2, sticky="w", padx=(6, 12)
	)
	ttk.Label(mag_line, text="固定加值").grid(row=0, column=3, sticky="w")
	tk.Entry(mag_line, textvariable=main_ui.attribute_action_attack_vars["mag_flat_bonus"], width=8).grid(
		row=0, column=4, sticky="w", padx=(6, 0)
	)

	mag_line2 = ttk.Frame(mag_box)
	mag_line2.grid(row=3, column=0, sticky="w", pady=(8, 0))
	ttk.Label(mag_line2, text="原始伤害 = 基础值 + 固定加值").grid(row=0, column=0, sticky="w")

	def _effective_float(var_key: str, default_key: str, fallback: float) -> float:
		var = main_ui.attribute_action_attack_vars.get(var_key)
		if var is None:
			return float(main_ui.attribute_action_attack_defaults.get(default_key, fallback))
		raw = str(var.get()).strip()
		if raw == "":
			return float(main_ui.attribute_action_attack_defaults.get(default_key, fallback))
		return main_ui._safe_float(raw, float(main_ui.attribute_action_attack_defaults.get(default_key, fallback)))

	def _refresh_formulas(*_args: Any) -> None:
		use_d20 = bool(main_ui.attribute_action_attack_vars.get("enable_d20").get())
		crit_on_20 = bool(main_ui.attribute_action_attack_vars.get("hit_crit_on_20").get())
		fail_on_1 = bool(main_ui.attribute_action_attack_vars.get("hit_fail_on_1").get())

		d20_rule: list[str] = []
		if use_d20:
			d20_rule.append("使用 d20")
			if fail_on_1:
				d20_rule.append("1 大失败")
			if crit_on_20:
				d20_rule.append("20 大成功且暴击")
			else:
				d20_rule.append("20 大成功")
		else:
			d20_rule.append("不使用 d20")
		d20_rule_text = "；".join(d20_rule)

		def _def_mod_desc(label: str, default_label: str) -> str:
			label = str(label or "").strip() or default_label
			if label == "无":
				return "无"
			return f"{label}"

		def _defense_formula_text(
			base_coeff: float,
			base_name: str,
			attr_coeff: float,
			attr_name: str,
			flat_bonus: float,
		) -> str:
			parts: list[str] = []
			if abs(base_coeff) > 1e-9:
				parts.append(f"{base_coeff:g}×{base_name}")
			if attr_name != "无" and abs(attr_coeff) > 1e-9:
				parts.append(f"{attr_coeff:g}×{attr_name}")
			if abs(flat_bonus) > 1e-9:
				parts.append(f"{flat_bonus:g}（固定加值）")
			return " + ".join(parts) if parts else "0"

		# --- 物理攻击命中 ---
		hit_a = _effective_float("hit_coeff_strength", "hit_coeff_strength", 1.0)
		hit_adv = _effective_float("hit_coeff_dexterity", "hit_coeff_dexterity", 1.0)
		hit_bonus = main_ui._safe_float(str(main_ui.attribute_action_attack_vars.get("hit_bonus_flat").get()).strip(), 0.0)
		phy_def_mod = _def_mod_desc(
			str(main_ui.attribute_action_attack_vars.get("phy_defense_modifier").get()),
			"敏捷修正",
		)
		phy_def_base_coeff = _effective_float("phy_def_base_coeff", "phy_def_base_coeff", 1.0)
		phy_def_attr_coeff = _effective_float("phy_def_attr_coeff", "phy_def_attr_coeff", 1.0)
		phy_def_flat = _effective_float("phy_def_flat_bonus", "phy_def_flat_bonus", 0.0)
		phy_def_text = _defense_formula_text(
			phy_def_base_coeff,
			"目标物理豁免值(物抗)",
			phy_def_attr_coeff,
			phy_def_mod,
			phy_def_flat,
		)

		hit_parts: list[str] = []
		if use_d20:
			hit_parts.append("d20")
		if abs(hit_a) > 1e-9:
			hit_parts.append(f"{hit_a:g}×力量修正")
		if abs(hit_adv) > 1e-9:
			hit_parts.append(f"{hit_adv:g}×优势值")
		if abs(hit_bonus) > 1e-9:
			hit_parts.append(f"{hit_bonus:g}（固定加值）")
		attack_throw_text = " + ".join(hit_parts) if hit_parts else "0"
		phy_hit_formula_var.set(
			"\n".join(
				[
					f"命中判定（是否命中）：攻击投掷 > 豁免值(防御值)",
					f"d20 规则：{d20_rule_text}",
					f"攻击投掷 = {attack_throw_text}",
					f"豁免值(防御值) = {phy_def_text}",
				]
			)
		)

		# --- 普通法术攻击命中 ---
		mag_hit_int = _effective_float(
			"magic_hit_coeff_intelligence", "magic_hit_coeff_intelligence", 1.0
		)
		mag_hit_adv = _effective_float(
			"magic_hit_coeff_advantage", "magic_hit_coeff_advantage", 1.0
		)
		mag_hit_bonus = main_ui._safe_float(
			str(main_ui.attribute_action_attack_vars.get("magic_hit_bonus_flat").get()).strip(), 0.0
		)
		mag_def_mod = _def_mod_desc(
			str(main_ui.attribute_action_attack_vars.get("mag_defense_modifier").get()),
			"无",
		)
		mag_def_base_coeff = _effective_float("mag_def_base_coeff", "mag_def_base_coeff", 1.0)
		mag_def_attr_coeff = _effective_float("mag_def_attr_coeff", "mag_def_attr_coeff", 1.0)
		mag_def_flat = _effective_float("mag_def_flat_bonus", "mag_def_flat_bonus", 0.0)
		mag_def_text = _defense_formula_text(
			mag_def_base_coeff,
			"目标法术豁免值(法抗)",
			mag_def_attr_coeff,
			mag_def_mod,
			mag_def_flat,
		)

		mag_hit_parts: list[str] = []
		if use_d20:
			mag_hit_parts.append("d20")
		if abs(mag_hit_int) > 1e-9:
			mag_hit_parts.append(f"{mag_hit_int:g}×智力修正")
		if abs(mag_hit_adv) > 1e-9:
			mag_hit_parts.append(f"{mag_hit_adv:g}×优势值")
		if abs(mag_hit_bonus) > 1e-9:
			mag_hit_parts.append(f"{mag_hit_bonus:g}（固定加值）")
		mag_attack_throw_text = " + ".join(mag_hit_parts) if mag_hit_parts else "0"
		mag_hit_formula_var.set(
			"\n".join(
				[
					f"命中判定（是否命中）：攻击投掷 > 豁免值(防御值)",
					f"d20 规则：{d20_rule_text}",
					f"攻击投掷 = {mag_attack_throw_text}",
					f"豁免值(防御值) = {mag_def_text}",
				]
			)
		)

		phy_flat = main_ui._safe_float(str(main_ui.attribute_action_attack_vars.get("phy_flat_bonus").get()).strip(), 0.0)
		use_piece_phy = bool(main_ui.attribute_action_attack_vars.get("phy_base_from_piece").get())
		phy_base_src = "棋子物伤" if use_piece_phy else "覆盖基础值"
		phy_base_override = str(main_ui.attribute_action_attack_vars.get("phy_base_override").get()).strip()
		if (not use_piece_phy) and phy_base_override != "":
			phy_base_src = f"覆盖基础值={phy_base_override}"
		phy_parts = [phy_base_src]
		if abs(phy_flat) > 1e-9:
			phy_parts.append(f"{phy_flat:g}（固定加值）")
		raw_phy = " + ".join(phy_parts) if phy_parts else "0"
		phy_template_var.set(
			"\n".join(
				[
					"规则说明（应用时生效）：",
					"原始伤害 = 基础值 + 固定加值",
					"说明：基础值为“棋子物伤”或“覆盖基础值”（由下方勾选决定）",
				]
			)
		)
		phy_effective_var.set(
			"\n".join(
				[
					"生效式（应用时生效）：",
					f"原始伤害 = {raw_phy}",
					"暴击：原始伤害 × 2",
				]
			)
		)

		mag_flat = main_ui._safe_float(str(main_ui.attribute_action_attack_vars.get("mag_flat_bonus").get()).strip(), 0.0)
		use_piece_mag = bool(main_ui.attribute_action_attack_vars.get("mag_base_from_piece").get())
		mag_base_src = "棋子法伤" if use_piece_mag else "覆盖基础值"
		mag_base_override = str(main_ui.attribute_action_attack_vars.get("mag_base_override").get()).strip()
		if (not use_piece_mag) and mag_base_override != "":
			mag_base_src = f"覆盖基础值={mag_base_override}"
		mag_parts = [mag_base_src]
		if abs(mag_flat) > 1e-9:
			mag_parts.append(f"{mag_flat:g}（固定加值）")
		raw_mag = " + ".join(mag_parts) if mag_parts else "0"
		mag_template_var.set(
			"\n".join(
				[
					"规则说明（应用时生效）：",
					"原始伤害 = 基础值 + 固定加值",
					"说明：基础值为“棋子法伤”或“覆盖基础值”（由下方勾选决定）",
				]
			)
		)
		mag_effective_var.set(
			"\n".join(
				[
					"生效式（应用时生效）：",
					f"原始伤害 = {raw_mag}",
					"暴击：原始伤害 × 2",
				]
			)
		)

	# 绑定刷新
	for key in (
		"enable_d20",
		"hit_crit_on_20",
		"hit_fail_on_1",
		"hit_coeff_strength",
		"hit_coeff_dexterity",
		"hit_bonus_flat",
		"phy_defense_modifier",
		"phy_def_base_coeff",
		"phy_def_attr_coeff",
		"phy_def_flat_bonus",
		"magic_hit_coeff_intelligence",
		"magic_hit_coeff_advantage",
		"magic_hit_bonus_flat",
		"mag_defense_modifier",
		"mag_def_base_coeff",
		"mag_def_attr_coeff",
		"mag_def_flat_bonus",
		"phy_base_from_piece",
		"phy_base_override",
		"phy_flat_bonus",
		"mag_base_from_piece",
		"mag_base_override",
		"mag_flat_bonus",
	):
		var = main_ui.attribute_action_attack_vars.get(key)
		if var is None:
			continue
		try:
			var.trace_add("write", _refresh_formulas)
		except Exception:
			pass
	_refresh_formulas()

	def _refresh_base_override_state(*_args: Any) -> None:
		try:
			use_piece_phy = bool(main_ui.attribute_action_attack_vars.get("phy_base_from_piece").get())
		except Exception:
			use_piece_phy = True
		try:
			use_piece_mag = bool(main_ui.attribute_action_attack_vars.get("mag_base_from_piece").get())
		except Exception:
			use_piece_mag = True
		try:
			phy_base_override_entry.configure(state=("disabled" if use_piece_phy else "normal"))
		except Exception:
			pass
		try:
			mag_base_override_entry.configure(state=("disabled" if use_piece_mag else "normal"))
		except Exception:
			pass

	for k in ("phy_base_from_piece", "mag_base_from_piece"):
		var = main_ui.attribute_action_attack_vars.get(k)
		if var is None:
			continue
		try:
			var.trace_add("write", _refresh_base_override_state)
		except Exception:
			pass
	_refresh_base_override_state()

	# --- 法术 TAB ---
	spell_tab.columnconfigure(0, weight=1)
	spell_tab.rowconfigure(1, weight=1)
	spell_tab.configure(padding=10)
	ttk.Label(
		spell_tab,
		text="勾选‘覆盖’后，应用时才会生效（未勾选则使用后端默认值）。",
		foreground="#4b5563",
	).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)

	scroll_host = ttk.Frame(spell_tab)
	scroll_host.grid(row=1, column=0, sticky="nsew")
	scroll_host.columnconfigure(0, weight=1)
	scroll_host.rowconfigure(0, weight=1)

	spell_canvas = tk.Canvas(scroll_host, highlightthickness=0, borderwidth=0)
	v_scroll = ttk.Scrollbar(scroll_host, orient="vertical", command=spell_canvas.yview)
	spell_canvas.configure(yscrollcommand=v_scroll.set)
	spell_canvas.grid(row=0, column=0, sticky="nsew")
	v_scroll.grid(row=0, column=1, sticky="ns")

	scroll_content = ttk.Frame(spell_canvas)
	canvas_window = spell_canvas.create_window((0, 0), window=scroll_content, anchor="nw")

	def _sync_scroll_region(_event: Any = None) -> None:
		# 用内容的 req 尺寸精确设置滚动区域，避免能滚到空白。
		try:
			scroll_content.update_idletasks()
			req_w = int(scroll_content.winfo_reqwidth())
			req_h = int(scroll_content.winfo_reqheight())
			spell_canvas.configure(scrollregion=(0, 0, max(req_w, 1), max(req_h, 1)))
		except Exception:
			spell_canvas.configure(scrollregion=spell_canvas.bbox("all"))

	def _fit_scroll_content_width(event: Any) -> None:
		spell_canvas.itemconfigure(canvas_window, width=int(event.width))

	scroll_content.bind("<Configure>", _sync_scroll_region)
	spell_canvas.bind("<Configure>", _fit_scroll_content_width)
	spell_canvas.bind("<Enter>", lambda _e: active_scroll_canvas.__setitem__("canvas", spell_canvas))
	scroll_content.bind("<Enter>", lambda _e: active_scroll_canvas.__setitem__("canvas", spell_canvas))

	head = ttk.Frame(scroll_content)
	head.grid(row=0, column=0, sticky="ew")
	cols = [
		("覆盖", 6),
		("法术", 16),
		("基础值", 8),
		("距离", 6),
		("半径", 6),
		("消耗", 6),
		("寿命", 6),
	]
	for cidx, (title, w) in enumerate(cols):
		ttk.Label(head, text=title, width=w).grid(row=0, column=cidx, sticky="w", padx=(0, 6))

	for ridx, spell in enumerate(SpellFactory.get_all_spells(), start=1):
		sid = int(getattr(spell, "id", 0))
		if sid <= 0:
			continue
		enable_var = main_ui.attribute_action_spell_enable_vars.get(sid)
		vars_map = main_ui.attribute_action_spell_vars.get(sid)
		if enable_var is None or vars_map is None:
			continue

		rowf = ttk.Frame(scroll_content)
		rowf.grid(row=ridx, column=0, sticky="ew", pady=(0, 4))
		ttk.Checkbutton(rowf, variable=enable_var).grid(row=0, column=0, sticky="w", padx=(0, 6))
		name = f"{sid}:{getattr(spell, 'name', '')}"
		ttk.Label(rowf, text=name, width=16).grid(row=0, column=1, sticky="w", padx=(0, 6))
		tk.Entry(rowf, textvariable=vars_map["base_value"], width=8).grid(row=0, column=2, sticky="w", padx=(0, 6))
		tk.Entry(rowf, textvariable=vars_map["range"], width=6).grid(row=0, column=3, sticky="w", padx=(0, 6))
		tk.Entry(rowf, textvariable=vars_map["area_radius"], width=6).grid(row=0, column=4, sticky="w", padx=(0, 6))
		tk.Entry(rowf, textvariable=vars_map["spell_cost"], width=6).grid(row=0, column=5, sticky="w", padx=(0, 6))
		tk.Entry(rowf, textvariable=vars_map["base_lifespan"], width=6).grid(row=0, column=6, sticky="w")

	# --- 底部按钮（冻结） ---
	btn_row = ttk.Frame(wrapper)
	btn_row.grid(row=3, column=0, sticky="ew", pady=(10, 0))
	btn_row.columnconfigure(0, weight=1)
	left = ttk.Frame(btn_row)
	left.grid(row=0, column=0, sticky="w")
	ttk.Button(left, text="恢复默认", command=lambda: reset_action_attribute_to_defaults(main_ui)).pack(side="left")
	ttk.Button(left, text="应用（本局）", command=lambda: apply_action_attribute_changes(main_ui)).pack(side="left", padx=(8, 0))

	right = ttk.Frame(btn_row)
	right.grid(row=0, column=1, sticky="e")
	main_ui.attribute_action_warning_label = ttk.Label(right, text="")
	main_ui.attribute_action_warning_label.pack(side="right", padx=(8, 0))
	main_ui.attribute_action_apply_status_label = ttk.Label(right, text="")
	main_ui.attribute_action_apply_status_label.pack(side="right")

	def _mark_dirty(*_args: Any) -> None:
		if bool(getattr(main_ui, "action_attribute_internal_update", False)):
			return
		label = main_ui.attribute_action_apply_status_label
		if label is None or (hasattr(label, "winfo_exists") and not label.winfo_exists()):
			return
		try:
			label.configure(text="未应用（有修改）", foreground="#b45309")
		except Exception:
			return

	if not bool(getattr(main_ui, "_action_attribute_dirty_trace_bound", False)):
		# 仅绑定一次，避免每次切换页面重复 trace 导致回调叠加。
		for var in main_ui.attribute_action_attack_vars.values():
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass
		for var in main_ui.attribute_action_spell_enable_vars.values():
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass
		for vars_map in main_ui.attribute_action_spell_vars.values():
			for var in vars_map.values():
				try:
					var.trace_add("write", _mark_dirty)
				except Exception:
					pass
		main_ui._action_attribute_dirty_trace_bound = True
