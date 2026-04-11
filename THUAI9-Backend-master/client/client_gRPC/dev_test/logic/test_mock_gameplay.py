from __future__ import annotations

from typing import Any, Callable, Optional


def ensure_test_mock_gameplay_installed(env: Any, logger: Optional[Callable[[str], None]] = None) -> None:
	"""Install playtest-only rule hooks onto a runtime env instance.

	This module is intentionally isolated under dev_test/logic to avoid mixing
	playtest rules into UI code and to avoid modifying backend files.

	Current rules:
	- Near-death system (濒死系统) described in warchess_plan (1).md
	- Derived cap gradients (派生上限梯度):
	  - strength -> max_action_points (<=13/21 -> 1/2 else 3 by default)
	  - intelligence -> max_spell_slots (<=3/7/12/16/21 -> 1/2/3/5/8 else 9 by default)

	Hooks are idempotent (safe to call multiple times).
	Runtime configs are read from:
	- env._ui_near_death_config (dict)
	- env._ui_talent_derived_config (dict)
	"""

	if env is None:
		return

	def _log(message: str) -> None:
		try:
			if callable(logger):
				logger(f"[TestMockGameplay] {message}")
		except Exception:
			return

	# Always refresh class-level pointers/configs even if already installed.
	_patch_piece_accessor_derived_caps(env, _log)

	already = bool(getattr(env, "_ui_test_mock_gameplay_installed", False)) or bool(
		getattr(env, "_ui_house_rules_installed", False)
	)
	setattr(env, "_ui_test_mock_gameplay_installed", True)
	if already:
		return

	def _get_near_cfg() -> dict[str, Any]:
		cfg = getattr(env, "_ui_near_death_config", None)
		return cfg if isinstance(cfg, dict) else {}

	def _near_enabled() -> bool:
		return bool(_get_near_cfg().get("enabled", False))

	def _get_state() -> dict[int, int]:
		state = getattr(env, "_ui_near_death_state", None)
		if isinstance(state, dict):
			return state
		state = {}
		setattr(env, "_ui_near_death_state", state)
		return state

	def _set_piece_alive(piece: Any, alive: bool) -> None:
		try:
			accessor = piece.get_accessor() if hasattr(piece, "get_accessor") else None
			if accessor is not None and hasattr(accessor, "set_alive"):
				accessor.set_alive(bool(alive))
			else:
				setattr(piece, "is_alive", bool(alive))
		except Exception:
			try:
				setattr(piece, "is_alive", bool(alive))
			except Exception:
				pass

	def _set_piece_dying(piece: Any, dying: bool) -> None:
		try:
			accessor = piece.get_accessor() if hasattr(piece, "get_accessor") else None
			if accessor is not None and hasattr(accessor, "set_dying"):
				accessor.set_dying(bool(dying))
			else:
				setattr(piece, "is_dying", bool(dying))
		except Exception:
			try:
				setattr(piece, "is_dying", bool(dying))
			except Exception:
				pass

	def _set_piece_health(piece: Any, hp: int) -> None:
		try:
			accessor = piece.get_accessor() if hasattr(piece, "get_accessor") else None
			if accessor is not None and hasattr(accessor, "set_health_to"):
				accessor.set_health_to(int(hp))
			else:
				setattr(piece, "health", int(hp))
		except Exception:
			try:
				setattr(piece, "health", int(hp))
			except Exception:
				pass

	def _remove_from_queue(piece: Any) -> None:
		try:
			q = getattr(env, "action_queue", [])
		except Exception:
			return

		try:
			as_list = list(q)  # works for np.array and list
		except Exception:
			return

		new_list = [p for p in as_list if p is not piece]

		# keep original container type if possible
		try:
			import numpy as np  # local import

			if hasattr(q, "dtype"):
				setattr(env, "action_queue", np.array(new_list, dtype=object))
				return
		except Exception:
			pass

		try:
			setattr(env, "action_queue", new_list)
		except Exception:
			pass

	def _append_dead(piece: Any) -> None:
		try:
			dead = getattr(env, "new_dead_this_round", None)
		except Exception:
			return

		try:
			import numpy as np

			if dead is None:
				setattr(env, "new_dead_this_round", np.array([piece], dtype=object))
				return
			if hasattr(dead, "dtype"):
				setattr(env, "new_dead_this_round", np.append(dead, [piece]))
				return
		except Exception:
			pass

		try:
			if dead is None:
				setattr(env, "new_dead_this_round", [piece])
			elif isinstance(dead, list):
				dead.append(piece)
			else:
				setattr(env, "new_dead_this_round", [dead, piece])
		except Exception:
			pass

	def _kill_piece(piece: Any, reason: str) -> None:
		if piece is None:
			return

		_set_piece_dying(piece, False)
		_set_piece_alive(piece, False)

		try:
			board = getattr(env, "board", None)
			if board is not None and callable(getattr(board, "remove_piece", None)):
				board.remove_piece(piece)
		except Exception:
			pass

		_remove_from_queue(piece)
		_append_dead(piece)

		try:
			setattr(piece, "death_round", int(getattr(env, "round_number", -1)))
		except Exception:
			pass

		try:
			state = _get_state()
			state.pop(id(piece), None)
		except Exception:
			pass

		_log(f"棋子死亡：{reason}")

	# --- hook: handle_death_check ---
	orig_handle_death_check = getattr(env, "handle_death_check", None)
	if callable(orig_handle_death_check):
		setattr(env, "_ui_orig_handle_death_check", orig_handle_death_check)

	def handle_death_check_hook(target: Any) -> None:
		if not _near_enabled():
			orig = getattr(env, "_ui_orig_handle_death_check", None)
			if callable(orig):
				return orig(target)
			return

		cfg = _get_near_cfg()
		revive_hp = int(cfg.get("revive_hp_on_20", 1) or 1)
		turns_to_die = int(cfg.get("turns_to_die", 1) or 1)
		turns_to_die = max(1, min(3, turns_to_die))
		die_on_damage = bool(cfg.get("die_on_damage_when_dying", True))

		if target is None:
			return

		# healed above 0 => clear dying
		try:
			hp_now = int(getattr(target, "health", 0))
		except Exception:
			hp_now = 0

		if hp_now > 0:
			_set_piece_dying(target, False)
			try:
				_get_state().pop(id(target), None)
			except Exception:
				pass
			return

		# already dying and got damaged again => direct death
		if bool(getattr(target, "is_dying", False)) and die_on_damage:
			return _kill_piece(target, reason="濒死期间再次受伤")

		# perform death save
		roll = 0
		try:
			roll_func = getattr(env, "roll_dice", None)
			if callable(roll_func):
				roll = int(roll_func(1, 20))
		except Exception:
			roll = 0

		if roll == 20:
			_set_piece_health(target, max(1, revive_hp))
			_set_piece_dying(target, False)
			_set_piece_alive(target, True)
			try:
				_get_state().pop(id(target), None)
			except Exception:
				pass
			_log("死亡检定=20：恢复")
			return

		if roll == 1:
			return _kill_piece(target, reason="死亡检定=1")

		# near-death
		_set_piece_health(target, 0)
		_set_piece_alive(target, True)
		_set_piece_dying(target, True)
		_get_state()[id(target)] = int(turns_to_die)
		_log("进入濒死")

	setattr(env, "handle_death_check", handle_death_check_hook)

	# --- hook: input_manager.handle_action_input (skip dying turns) ---
	input_manager = getattr(env, "input_manager", None)
	if input_manager is not None:
		orig_handle_action_input = getattr(input_manager, "handle_action_input", None)
		if callable(orig_handle_action_input):
			setattr(env, "_ui_orig_handle_action_input", orig_handle_action_input)

			def handle_action_input_hook(player_id: int, env_obj: Any):
				if _near_enabled():
					piece = getattr(env_obj, "current_piece", None)
					if piece is not None:
						try:
							hp = int(getattr(piece, "health", 0))
						except Exception:
							hp = 0
						if bool(getattr(piece, "is_dying", False)) and hp <= 0:
							return None
				orig = getattr(env, "_ui_orig_handle_action_input", None)
				if callable(orig):
					return orig(player_id, env_obj)
				return None

			setattr(input_manager, "handle_action_input", handle_action_input_hook)

	# --- hook: step (post-step countdown / cleanup) ---
	orig_step = getattr(env, "step", None)
	if callable(orig_step):
		setattr(env, "_ui_orig_step", orig_step)

		def step_hook(*args: Any, **kwargs: Any):
			out = getattr(env, "_ui_orig_step")(*args, **kwargs)

			if not _near_enabled():
				return out

			# clear dying if healed
			try:
				q = list(getattr(env, "action_queue", []))
			except Exception:
				q = []
			for p in q:
				try:
					if bool(getattr(p, "is_dying", False)) and int(getattr(p, "health", 0)) > 0:
						_set_piece_dying(p, False)
						_get_state().pop(id(p), None)
				except Exception:
					continue

			# countdown when a dying piece reaches its turn (it will be skipped by input hook)
			piece = getattr(env, "current_piece", None)
			if piece is not None:
				try:
					hp = int(getattr(piece, "health", 0))
				except Exception:
					hp = 0
				if bool(getattr(piece, "is_dying", False)) and hp <= 0 and bool(getattr(piece, "is_alive", True)):
					state = _get_state()
					remaining = int(state.get(id(piece), int(_get_near_cfg().get("turns_to_die", 1) or 1)))
					remaining -= 1
					state[id(piece)] = remaining
					if remaining <= 0:
						_kill_piece(piece, reason="濒死超时")

			return out

		setattr(env, "step", step_hook)

	_log("已安装 playtest 规则 hooks")


def _piecewise_by_threshold(num: int, thresholds: list[int], values: list[int]) -> int:
	if not values:
		return 0
	if not thresholds or len(values) == 1:
		return int(values[0])
	for idx, th in enumerate(thresholds):
		try:
			if int(num) <= int(th):
				return int(values[idx])
		except Exception:
			continue
	return int(values[-1])


def _patch_piece_accessor_derived_caps(env: Any, log: Callable[[str], None]) -> None:
	"""Patch PieceAccessor methods to read env._ui_talent_derived_config.

	Since PieceAccessor methods do not receive env, we keep a class-level pointer
	to the latest config dict from the active env. This is sufficient for dev_test.
	"""
	try:
		import importlib

		env_mod = importlib.import_module("env")
		piece_accessor_cls = getattr(env_mod, "PieceAccessor", None)
		if piece_accessor_cls is None:
			return
	except Exception:
		return

	# Refresh class-level config pointer each time.
	try:
		cfg = getattr(env, "_ui_talent_derived_config", None)
		piece_accessor_cls._ui_talent_derived_cfg = cfg if isinstance(cfg, dict) else {}
	except Exception:
		piece_accessor_cls._ui_talent_derived_cfg = {}

	if bool(getattr(piece_accessor_cls, "_ui_derived_caps_hooked", False)):
		return
	setattr(piece_accessor_cls, "_ui_derived_caps_hooked", True)

	orig_ap = getattr(piece_accessor_cls, "set_max_action_points", None)
	if callable(orig_ap):
		setattr(piece_accessor_cls, "_ui_orig_set_max_action_points", orig_ap)

		def set_max_action_points_hook(self: Any):
			cfg2 = getattr(piece_accessor_cls, "_ui_talent_derived_cfg", {})
			stat_cfg = cfg2.get("strength") if isinstance(cfg2, dict) else None
			if isinstance(stat_cfg, dict):
				ths = stat_cfg.get("thresholds")
				vals = stat_cfg.get("values")
				if isinstance(ths, list) and isinstance(vals, list) and len(vals) == len(ths) + 1:
					try:
						ths_i = [int(x) for x in ths]
						vals_i = [int(x) for x in vals]
					except Exception:
						ths_i, vals_i = [], []
					try:
						num = int(getattr(getattr(self, "piece", None), "strength", 0))
					except Exception:
						num = 0
					if vals_i:
						v = _piecewise_by_threshold(num, ths_i, vals_i)
						try:
							return self.set_max_action_points_to(int(v))
						except Exception:
							pass
			orig = getattr(piece_accessor_cls, "_ui_orig_set_max_action_points", None)
			return orig(self) if callable(orig) else None

		setattr(piece_accessor_cls, "set_max_action_points", set_max_action_points_hook)

	orig_ss = getattr(piece_accessor_cls, "set_max_spell_slots", None)
	if callable(orig_ss):
		setattr(piece_accessor_cls, "_ui_orig_set_max_spell_slots", orig_ss)

		def set_max_spell_slots_hook(self: Any):
			cfg2 = getattr(piece_accessor_cls, "_ui_talent_derived_cfg", {})
			stat_cfg = cfg2.get("intelligence") if isinstance(cfg2, dict) else None
			if isinstance(stat_cfg, dict):
				ths = stat_cfg.get("thresholds")
				vals = stat_cfg.get("values")
				if isinstance(ths, list) and isinstance(vals, list) and len(vals) == len(ths) + 1:
					try:
						ths_i = [int(x) for x in ths]
						vals_i = [int(x) for x in vals]
					except Exception:
						ths_i, vals_i = [], []
					try:
						num = int(getattr(getattr(self, "piece", None), "intelligence", 0))
					except Exception:
						num = 0
					if vals_i:
						v = _piecewise_by_threshold(num, ths_i, vals_i)
						try:
							return self.set_max_spell_slots_to(int(v))
						except Exception:
							pass
			orig = getattr(piece_accessor_cls, "_ui_orig_set_max_spell_slots", None)
			return orig(self) if callable(orig) else None

		setattr(piece_accessor_cls, "set_max_spell_slots", set_max_spell_slots_hook)

	log("已 hook 派生上限梯度（max_action_points/max_spell_slots）")


# Backward-compat alias (old name)
ensure_house_rules_installed = ensure_test_mock_gameplay_installed
