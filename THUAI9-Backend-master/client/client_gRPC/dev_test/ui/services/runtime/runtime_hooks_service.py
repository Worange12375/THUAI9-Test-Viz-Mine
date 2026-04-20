"""运行时 Hook 注入服务（Phase 1 拆分产物）。

本文件负责：
- 将“玩法设计/系统设置”等 UI 配置写入 runtime `env`，并安装测试端 hook（幂等）。
- 提供跨局保持（persistent）配置的重应用入口。

不负责：
- Tk 控件创建与布局（应在 view/main_ui 中）；
- 具体页面变量的采集与校验（仍在 MainUI 的页面代码中）。

设计说明（务实版）：
- Phase 1 目标是“搬家不改逻辑”。因此这里的函数会接收 `main_ui` 实例，
  继续复用其 logger/回调（例如 `right_info_panel.append_content`、`_rerender_spell_mode_if_needed`）。
- 等后续 Phase 逐步引入 state/service 分层后，再把对 MainUI 的依赖收敛成更小的接口。
"""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

from env import SpellFactory
from logic.test_mock_gameplay import ensure_test_mock_gameplay_installed


def reapply_persistent_design_settings(main_ui: Any, env: Any) -> None:
	"""新对局加载后自动重应用（跨局保持）的玩法设计配置。"""
	if env is None or getattr(getattr(main_ui, "controller", None), "runtime_source", None) != "runtime_env":
		return

	try:
		cfg = getattr(main_ui, "_persistent_near_death_design_config", None)
		if isinstance(cfg, dict):
			apply_near_death_config(main_ui, cfg or {})
			main_ui.right_info_panel.append_content("\n[UI] 已自动重应用：濒死系统配置（跨局保持）")
	except Exception:
		pass

	try:
		cfg = getattr(main_ui, "_persistent_spell_pool_design_config", None)
		if isinstance(cfg, dict):
			apply_spell_pool_config(main_ui, cfg or {})
			main_ui.right_info_panel.append_content("\n[UI] 已自动重应用：法术池配置（跨局保持）")
	except Exception:
		pass


def apply_spell_pool_config(main_ui: Any, config: dict[str, Any]) -> bool:
	"""将“法术池配置”注入到 runtime env，并覆盖 `env.get_available_spells`。"""
	controller = getattr(main_ui, "controller", None)
	if getattr(controller, "runtime_source", None) != "runtime_env":
		return False
	env = getattr(controller, "environment", None)
	if env is None:
		return False

	use_test = True
	try:
		use_test = bool(config.get("use_test_spell_impl", True)) if isinstance(config, dict) else True
	except Exception:
		use_test = True
	priorities = config.get("spell_priorities", {}) if isinstance(config, dict) else {}
	if not isinstance(priorities, dict):
		priorities = {}
	setattr(env, "_ui_use_test_spell_impl", bool(use_test))
	setattr(env, "_ui_spell_priorities_config", copy.deepcopy(priorities))

	def _normalize_spell_key(name: str) -> str:
		key = str(name or "").strip().lower()
		key = key.replace(" ", "")
		if key in ("arrowhit", "arrow_hit"):
			return "arrow_hit"
		if key == "fireball":
			return "fireball"
		if key == "trap":
			return "trap"
		if key == "heal":
			return "heal"
		if key in ("teleport", "move"):
			return "teleport"
		return key

	def _get_spell_order_keys_fixed() -> list[str]:
		"""行动下拉展示顺序：与玩法设计表格纵轴一致（固定顺序）。

		当前显示：箭击 -> 陷阱 -> 治愈 -> 瞬移 -> 火球。
		未来新法术可在此处扩展（先不在 UI 中显示）。
		"""
		# TODO: future spells (reserved)
		return ["arrow_hit", "trap", "heal", "teleport", "fireball"]

	setattr(env, "_ui_spell_order_keys", _get_spell_order_keys_fixed())

	orig_fetcher = getattr(env, "get_available_spells", None)
	if callable(orig_fetcher) and not bool(getattr(orig_fetcher, "_ui_spell_pool_marker", False)):
		setattr(env, "_ui_orig_get_available_spells_spell_pool", orig_fetcher)

	def get_available_spells_hook(piece: Any = None) -> list[Any]:
		# 与后端 env.get_available_spells 行为对齐：piece=None 则默认 current_piece。
		if piece is None:
			piece = getattr(env, "current_piece", None)
		if piece is None or not bool(getattr(piece, "is_alive", True)):
			return []

		def _get_piece_weapon_id(p: Any) -> int | None:
			for attr in ("weapon_id", "weaponId", "weapon", "weapon_type", "weaponType"):
				if hasattr(p, attr):
					try:
						return int(getattr(p, attr))
					except Exception:
						pass
			eq = getattr(p, "equip", None)
			if eq is not None:
				for attr in ("x", "X"):
					if hasattr(eq, attr):
						try:
							return int(getattr(eq, attr))
						except Exception:
							pass
				try:
					if isinstance(eq, (tuple, list)) and len(eq) >= 1:
						return int(eq[0])
				except Exception:
					pass
			return None

		def _get_prof_key(p: Any) -> str:
			t = str(getattr(p, "type", "") or "").strip()
			if t in ("WarriorLong", "WarriorShort", "Archer", "Mage"):
				return t
			wid = _get_piece_weapon_id(p)
			if wid == 1:
				return "WarriorLong"
			if wid == 2:
				return "WarriorShort"
			if wid == 3:
				return "Archer"
			if wid == 4:
				return "Mage"
			if t == "Warrior":
				return "WarriorLong"
			if t in ("Archer", "Mage"):
				return t
			return t or "Unknown"

		def _apply_action_spell_overrides(spells: list[Any]) -> list[Any]:
			"""与“行动属性-法术覆盖”兼容：若本局已应用 spell_overrides，则对返回法术做属性覆写。"""
			try:
				snap = getattr(env, "_ui_action_settings_snapshot", None)
				if not isinstance(snap, dict):
					return spells
				overrides = snap.get("spell_overrides", {})
				if not isinstance(overrides, dict) or not overrides:
					return spells
			except Exception:
				return spells
			out: list[Any] = []
			for spell in spells:
				try:
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
				except Exception:
					out.append(spell)
			return out

		# 模式 1：走后端实现（直接委托原逻辑）
		if not bool(getattr(env, "_ui_use_test_spell_impl", True)):
			orig = getattr(env, "_ui_orig_get_available_spells_spell_pool", None)
			base = list(orig(piece)) if callable(orig) else SpellFactory.get_available_spells(piece)
			return _apply_action_spell_overrides(base)

		# 模式 2：测试端独立实现（优先级 + 智力上限）
		prof_key = _get_prof_key(piece)
		priorities_cfg = getattr(env, "_ui_spell_priorities_config", None)
		if not isinstance(priorities_cfg, dict):
			priorities_cfg = {}

		default_test_priorities: dict[str, dict[str, int]] = {
			"WarriorLong": {"arrow_hit": 1, "heal": 2},
			"WarriorShort": {"trap": 1, "heal": 2},
			"Archer": {"arrow_hit": 1, "trap": 2},
			"Mage": {"arrow_hit": 1, "trap": 2, "heal": 3, "teleport": 4, "fireball": 5},
		}

		# 若未提供任何优先级配置，则使用测试端默认池（避免空配置导致下拉为空）。
		if not priorities_cfg:
			priorities_cfg = default_test_priorities

		prof_map = priorities_cfg.get(prof_key, {}) if isinstance(priorities_cfg.get(prof_key, {}), dict) else {}
		if not prof_map:
			prof_map = default_test_priorities.get(prof_key, {})

		# build key->spell
		all_spells = list(SpellFactory.get_all_spells())
		spell_by_key: dict[str, Any] = {}
		for sp in all_spells:
			k = _normalize_spell_key(str(getattr(sp, "name", "")))
			if k and k not in spell_by_key:
				spell_by_key[k] = sp

		order_keys = getattr(env, "_ui_spell_order_keys", None)
		if not isinstance(order_keys, list) or not order_keys:
			order_keys = _get_spell_order_keys_fixed()

		# candidates
		candidates: list[str] = []
		for k, raw_pri in prof_map.items():
			try:
				pri = int(raw_pri)
			except Exception:
				pri = 0
			if pri > 0 and k in spell_by_key:
				candidates.append(str(k))
		if not candidates:
			return []

		# N by intelligence
		try:
			intel = int(getattr(piece, "intelligence", 0) or 0)
		except Exception:
			intel = 0
		intel = max(0, int(intel))
		is_mage = (prof_key == "Mage") or (str(getattr(piece, "type", "")).strip() == "Mage")
		if is_mage:
			max_spells = 2 * (intel // 4) + 1
		else:
			max_spells = (intel // 4) + 1
		max_spells = max(1, int(max_spells))

		idx: dict[str, int] = {str(k): i for i, k in enumerate(order_keys)}

		def _sort_key(k: str) -> tuple[int, int]:
			try:
				pri = int(prof_map.get(k, 0))
			except Exception:
				pri = 0
			# 数字越小优先级越高；相同优先级按表格行顺序稳定排序。
			return (pri, idx.get(k, 10**9))

		sorted_keys = sorted(candidates, key=_sort_key)
		selected_set = set(sorted_keys[: max_spells])
		base: list[Any] = [spell_by_key[k] for k in order_keys if k in selected_set]
		return _apply_action_spell_overrides(base)

	setattr(get_available_spells_hook, "_ui_spell_pool_marker", True)
	setattr(env, "get_available_spells", get_available_spells_hook)

	# 立即刷新行动面板“法术”模式下的下拉框
	try:
		main_ui._rerender_spell_mode_if_needed()
	except Exception:
		pass

	return True


def apply_near_death_config(main_ui: Any, config: dict[str, Any]) -> bool:
	"""将“濒死系统配置”写入 runtime env，并确保 hook 已安装。"""
	controller = getattr(main_ui, "controller", None)
	if getattr(controller, "runtime_source", None) != "runtime_env":
		return False
	env = getattr(controller, "environment", None)
	if env is None:
		return False

	setattr(env, "_ui_near_death_config", config.get("near_death", {}) if isinstance(config, dict) else {})

	# 安装测试端玩法 hook（仅一次），并在 hook 内动态读取 _ui_near_death_config。
	def _queue_near_death_msg(msg: str) -> None:
		try:
			pending = getattr(env, "_ui_pending_info_messages", None)
			if not isinstance(pending, list):
				pending = []
				setattr(env, "_ui_pending_info_messages", pending)
			pending.append(str(msg))
		except Exception:
			return

	try:
		ensure_test_mock_gameplay_installed(env, logger=_queue_near_death_msg)
	except Exception:
		try:
			ensure_test_mock_gameplay_installed(env)
		except Exception:
			pass

	# 若已安装行动设置 hook，需要确保其对“濒死目标可被攻击”兼容（hook 内动态读取配置）。
	try:
		snapshot = (
			main_ui.action_settings_snapshot
			if isinstance(getattr(main_ui, "action_settings_snapshot", None), dict) and main_ui.action_settings_snapshot
			else main_ui._default_action_settings_snapshot()
		)
		main_ui._apply_action_settings_to_runtime_environment(snapshot)
	except Exception:
		pass

	return True


def apply_talent_gradient_config(main_ui: Any, config: dict[str, Any]) -> bool:
	"""将“派生上限梯度配置”写入 runtime env，并确保 hook 已安装和当前局立刻生效。"""
	controller = getattr(main_ui, "controller", None)
	if getattr(controller, "runtime_source", None) != "runtime_env":
		return False
	env = getattr(controller, "environment", None)
	if env is None:
		return False

	# 语义：派生上限梯度（最大行动位/最大法术位）
	setattr(env, "_ui_talent_derived_config", config if isinstance(config, dict) else {})

	# 安装测试端玩法 hook（幂等），由 hook 动态读取 _ui_talent_derived_config。
	try:
		ensure_test_mock_gameplay_installed(env, logger=lambda msg: main_ui.right_info_panel.append_content(f"\n{msg}"))
	except Exception:
		try:
			ensure_test_mock_gameplay_installed(env)
		except Exception:
			pass

	# 立即重算当前场上的上限，保证本局立刻可见。
	try:
		for player_attr in ("player1", "player2"):
			player = getattr(env, player_attr, None)
			pieces = getattr(player, "pieces", None) if player is not None else None
			if not pieces:
				continue
			for piece in list(pieces):
				acc = piece.get_accessor() if hasattr(piece, "get_accessor") else None
				if acc is None:
					continue
				try:
					if callable(getattr(acc, "set_max_action_points", None)):
						acc.set_max_action_points()
					if callable(getattr(acc, "set_max_spell_slots", None)):
						acc.set_max_spell_slots()
					try:
						piece.action_points = min(
							int(getattr(piece, "action_points", 0)), int(getattr(piece, "max_action_points", 0))
						)
					except Exception:
						pass
					try:
						piece.spell_slots = min(int(getattr(piece, "spell_slots", 0)), int(getattr(piece, "max_spell_slots", 0)))
					except Exception:
						pass
				except Exception:
					continue
	except Exception:
		pass

	return True
