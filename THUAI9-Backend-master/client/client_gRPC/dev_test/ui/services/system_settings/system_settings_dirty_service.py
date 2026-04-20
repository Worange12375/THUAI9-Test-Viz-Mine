"""System settings dirty/snapshot management service.

职责：
- 管理系统设置窗口各 section 的 dirty 标记（用于显示“未应用”与关闭回滚）。
- 提供抑制 dirty 的屏障（初始化/同步/回滚时避免 trace 误触发）。
- 关闭窗口时按 dirty 标记回滚到最近一次“已应用”基线。

约束：不改变现有行为，仅做代码搬家。
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from typing import Any


def set_system_settings_dirty(main_ui: object, section: str, dirty: bool) -> None:
	# dirty 屏障：内部同步/回滚/初始化时，不应触发“写入即脏”。
	# 说明：通常 dirty=True 来自 trace 回调；dirty=False 来自显式 apply/回滚。
	try:
		suppress_depth = int(getattr(main_ui, "_system_settings_dirty_suppress_depth", 0) or 0)
	except Exception:
		suppress_depth = 0
	if bool(dirty) and suppress_depth > 0:
		return
	flags = getattr(main_ui, "_system_settings_dirty_flags", None)
	if not isinstance(flags, dict):
		return
	flags[str(section)] = bool(dirty)
	label_vars = getattr(main_ui, "_system_settings_dirty_label_vars", None)
	if not isinstance(label_vars, dict):
		return
	var = label_vars.get(str(section))
	if var is not None:
		try:
			var.set("（未应用）" if dirty else "")
		except Exception:
			pass


@contextlib.contextmanager
def suppress_system_settings_dirty(main_ui: object) -> Any:
	"""暂时抑制 system_settings 的 dirty 标记（用于内部同步/回滚/初始化）。"""
	try:
		setattr(
			main_ui,
			"_system_settings_dirty_suppress_depth",
			int(getattr(main_ui, "_system_settings_dirty_suppress_depth", 0) or 0) + 1,
		)
	except Exception:
		setattr(main_ui, "_system_settings_dirty_suppress_depth", 1)
	try:
		yield
	finally:
		try:
			setattr(
				main_ui,
				"_system_settings_dirty_suppress_depth",
				max(0, int(getattr(main_ui, "_system_settings_dirty_suppress_depth", 1) or 1) - 1),
			)
		except Exception:
			setattr(main_ui, "_system_settings_dirty_suppress_depth", 0)


def suppress_system_settings_dirty_until_idle(main_ui: object) -> None:
	"""抑制 dirty 直到下一次 Tk idle。

	用于解决“页面构建/控件创建时，控件内部会延迟写回 Variable 导致 trace 误触发”问题。
	"""
	try:
		setattr(
			main_ui,
			"_system_settings_dirty_suppress_depth",
			int(getattr(main_ui, "_system_settings_dirty_suppress_depth", 0) or 0) + 1,
		)
	except Exception:
		setattr(main_ui, "_system_settings_dirty_suppress_depth", 1)

	def _release() -> None:
		try:
			setattr(
				main_ui,
				"_system_settings_dirty_suppress_depth",
				max(0, int(getattr(main_ui, "_system_settings_dirty_suppress_depth", 1) or 1) - 1),
			)
		except Exception:
			setattr(main_ui, "_system_settings_dirty_suppress_depth", 0)

	try:
		getattr(main_ui, "root").after_idle(_release)
	except Exception:
		_release()


def has_any_system_settings_dirty(main_ui: object) -> bool:
	flags = getattr(main_ui, "_system_settings_dirty_flags", None)
	if not isinstance(flags, dict):
		return False
	return any(bool(v) for v in flags.values())


def discard_unapplied_system_settings_changes(main_ui: object) -> None:
	"""回滚系统设置中未应用的修改，并清空 dirty 状态。"""
	flags = getattr(main_ui, "_system_settings_dirty_flags", None)
	if not isinstance(flags, dict) or not flags:
		return

	apply_general_snapshot = getattr(main_ui, "_apply_system_general_settings_snapshot_to_vars")
	apply_design_attr_snapshot = getattr(main_ui, "_apply_design_attribute_talent_gradient_snapshot_to_vars")

	with suppress_system_settings_dirty(main_ui):
		# 综合设置
		try:
			if bool(flags.get("general", False)) and isinstance(
				getattr(main_ui, "_applied_system_general_settings_snapshot", None), dict
			):
				apply_general_snapshot(getattr(main_ui, "_applied_system_general_settings_snapshot", {}) or {})
		except Exception:
			pass

		# 玩法设计-全局：濒死系统
		try:
			if bool(flags.get("design_global_near_death", False)):
				cfg = getattr(main_ui, "_persistent_near_death_design_config", None)
				near = cfg.get("near_death", {}) if isinstance(cfg, dict) else {}
				if not isinstance(near, dict):
					near = {}
				getattr(main_ui, "design_near_death_enabled_var").set(bool(near.get("enabled", False)))
				revive_hp = near.get("revive_hp_on_20", 1)
				getattr(main_ui, "design_near_death_revive_hp_var").set(str(revive_hp if revive_hp is not None else 1))
				try:
					getattr(main_ui, "design_near_death_turns_to_die_var").set(int(near.get("turns_to_die", 1)))
				except Exception:
					getattr(main_ui, "design_near_death_turns_to_die_var").set(1)
				getattr(main_ui, "design_near_death_die_on_damage_var").set(bool(near.get("die_on_damage_when_dying", True)))
				getattr(main_ui, "design_near_death_can_move_var").set(bool(near.get("can_move_when_dying", False)))
				getattr(main_ui, "design_near_death_can_attack_spell_var").set(bool(near.get("can_attack_or_spell_when_dying", False)))
		except Exception:
			pass

		# 玩法设计-属性：派生上限梯度
		try:
			if bool(flags.get("design_attribute", False)):
				snap = getattr(main_ui, "_applied_design_attribute_talent_gradients_snapshot", None)
				if isinstance(snap, dict) and snap:
					apply_design_attr_snapshot(snap)
		except Exception:
			pass

		# 玩法设计-法术：法术池配置
		try:
			if bool(flags.get("design_spell_pool", False)):
				cfg = getattr(main_ui, "_persistent_spell_pool_design_config", None)
				use_test = True
				try:
					use_test = bool(cfg.get("use_test_spell_impl", True)) if isinstance(cfg, dict) else True
				except Exception:
					use_test = True
				try:
					getattr(main_ui, "design_spell_use_test_impl_var").set(bool(use_test))
				except Exception:
					pass

				priorities = cfg.get("spell_priorities", {}) if isinstance(cfg, dict) else {}
				if not isinstance(priorities, dict) or not priorities:
					# 无已应用快照：清空，让下次打开时走默认初始化。
					setattr(main_ui, "design_spell_priority_vars", {})
				else:
					# 复用/重建 StringVar，避免页面未打开时引用丢失。
					out: dict[str, dict[str, tk.StringVar]] = {}
					for prof, spell_map in priorities.items():
						if not isinstance(spell_map, dict):
							continue
						out_prof: dict[str, tk.StringVar] = {}
						for k, v in spell_map.items():
							out_prof[str(k)] = tk.StringVar(value=str(v))
						out[str(prof)] = out_prof
					setattr(main_ui, "design_spell_priority_vars", out)
				# 清空缓存，保证回到“已应用”基线。
				setattr(main_ui, "_spell_priority_cache_when_test_impl_enabled", None)
		except Exception:
			pass

	# 清空 dirty 状态
	try:
		for section in list(flags.keys()):
			set_system_settings_dirty(main_ui, str(section), False)
	except Exception:
		pass
