from __future__ import annotations

import inspect
import time

from typing import Any, Callable, Optional


def _nddbg(env: Any, message: str) -> None:
	"""Near-death debug print (terminal).

	可还原性：所有调用行或 print 行末统一带 # NDDBG（便于全文检索删除）。
	默认开启；如需临时关闭可在运行时设置 env._ui_near_death_debug_print = False。
	"""
	try:
		if env is None:
			return
		if not bool(getattr(env, "_ui_near_death_debug_print", True)):
			return
		print(f"[NDDBG] {message}", flush=True)  # NDDBG
	except Exception:
		pass


def ensure_d20_force_installed(env: Any, logger: Optional[Callable[[str], None]] = None) -> None:
	"""Install a dev_test-only roll override: force selected d20 rolls to a fixed value.

	Config (set by UI):
	- env._ui_force_d20_flags: dict[str, bool]
	- env._ui_force_d20_values: dict[str, int]  # optional, 1-20
	Keys (current):
	Keys (current):
	- attack_hit: 命中检定（物理/普通法术）
	- death_check: 死亡检定（HP→0）
	- initiative: 先攻（行动队列）
	"""
	if env is None:
		return

	# 允许 UI 运行中重复调用：刷新 logger，保证系统消息可见。
	try:
		setattr(env, "_ui_test_mock_gameplay_logger", logger)
	except Exception:
		pass

	def _log(message: str) -> None:
		try:
			if callable(logger):
				logger(f"[ForceD20] {message}")
		except Exception:
			return

	current_roll = getattr(env, "roll_dice", None)
	if callable(current_roll) and bool(getattr(current_roll, "_ui_force_d20_marker", False)):
		return

	orig_roll = current_roll
	if not callable(orig_roll):
		return

	setattr(env, "_ui_force_d20_installed", True)
	setattr(env, "_ui_orig_roll_dice_force_d20", orig_roll)

	def _resolve_kind_from_stack() -> str:
		try:
			# Limit frames for performance.
			for frame_info in inspect.stack()[1:10]:
				fn = frame_info.function
				if fn == "execute_attack":
					return "attack_hit"
				if fn == "_on_preview_submit_action":
					return "attack_hit"
				if fn in ("handle_death_check", "handle_death_check_hook"):
					return "death_check"
				if fn == "initialize":
					return "initiative"
		except Exception:
			return ""
		return ""

	def roll_dice_hook(n: int, sides: int):
		if int(n) == 1 and int(sides) == 20:
			flags = getattr(env, "_ui_force_d20_flags", None)
			if isinstance(flags, dict) and flags:
				kind = _resolve_kind_from_stack()
				if kind and bool(flags.get(kind, False)):
					values = getattr(env, "_ui_force_d20_values", None)
					forced = None
					if isinstance(values, dict):
						forced = values.get(kind)
					try:
						forced_i = int(forced)
					except Exception:
						forced_i = 20
					if forced_i < 1 or forced_i > 20:
						forced_i = 20
					# UI 的 runtime death_check 提示会依赖 env._ui_last_deathcheck_roll。
					# 但“强制点数”分支会直接 return，导致 UI 的 roll_dice_hook 无法记录。
					# 因此这里主动写入，避免右侧日志出现 d20=?。
					if kind == "death_check" and bool(getattr(env, "_ui_in_deathcheck", False)):
						try:
							setattr(env, "_ui_last_deathcheck_roll", int(forced_i))
						except Exception:
							pass
					return forced_i
		return getattr(env, "_ui_orig_roll_dice_force_d20")(n, sides)

	# 允许其它 hook（例如 UI 的 death_check 记录 hook）在安装时解包到原始实现，避免形成递归环。
	setattr(roll_dice_hook, "_ui_force_d20_marker", True)
	setattr(roll_dice_hook, "_ui_force_d20_orig", orig_roll)

	setattr(env, "roll_dice", roll_dice_hook)
	_log("已安装 d20 强制点数 覆盖")


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

	# 允许 UI 运行中重复调用：刷新 logger，保证系统消息可见。
	try:
		setattr(env, "_ui_test_mock_gameplay_logger", logger)
	except Exception:
		pass

	def _queue_message(message: str) -> None:
		"""向 UI/外部注入的 logger 或 env 队列发送一条消息。"""
		try:
			rt_logger = getattr(env, "_ui_test_mock_gameplay_logger", None)
			if callable(rt_logger):
				rt_logger(str(message))
				return
		except Exception:
			pass
		try:
			pending = getattr(env, "_ui_pending_info_messages", None)
			if not isinstance(pending, list):
				pending = []
				setattr(env, "_ui_pending_info_messages", pending)
			pending.append(str(message))
		except Exception:
			return

	def _log(message: str) -> None:
		_queue_message(f"[TestMockGameplay] {message}")

	def _sys(message: str) -> None:
		_queue_message(f"[系统] {message}")

	# Always refresh class-level pointers/configs even if already installed.
	ensure_d20_force_installed(env, logger=logger)
	_patch_piece_accessor_derived_caps(env, _log)

	already = bool(getattr(env, "_ui_test_mock_gameplay_installed", False)) or bool(
		getattr(env, "_ui_house_rules_installed", False)
	)
	setattr(env, "_ui_test_mock_gameplay_installed", True)
	_nddbg(env, f"ensure_test_mock_gameplay_installed called; already={already}")  # NDDBG
	# 即使已安装过，也不要在这里 return：
	# - UI 可能在运行中刷新配置
	# - env.step / input_manager.handle_action_input 可能被其它逻辑覆盖，需要自愈式重新挂钩

	def _get_near_cfg() -> dict[str, Any]:
		cfg = getattr(env, "_ui_near_death_config", None)
		return cfg if isinstance(cfg, dict) else {}

	def _near_enabled() -> bool:
		enabled = bool(_get_near_cfg().get("enabled", False))
		return enabled

	def _get_state() -> dict[int, int]:
		state = getattr(env, "_ui_near_death_state", None)
		if isinstance(state, dict):
			return state
		state = {}
		setattr(env, "_ui_near_death_state", state)
		return state

	def _piece_key(piece: Any) -> int:
		"""用于 env._ui_near_death_state 的稳定 key。

		优先使用 piece.id（更稳定、便于 UI/日志定位）；缺失时回退到 python 对象 id。
		"""
		try:
			pid = int(getattr(piece, "id", -1))
		except Exception:
			pid = -1
		if pid >= 0:
			return pid
		return -int(id(piece))

	def _iter_all_pieces() -> list[Any]:
		# 兼容：有些阶段棋子可能暂时只出现在 action_queue（或 UI 侧拿不到 player.pieces）。
		pieces: list[Any] = []
		for player_attr in ("player1", "player2"):
			player = getattr(env, player_attr, None)
			for p in _coerce_piece_list(getattr(player, "pieces", None) if player is not None else None):
				pieces.append(p)
		try:
			for p in list(getattr(env, "action_queue", [])):
				pieces.append(p)
		except Exception:
			pass
		# 去重：按对象身份去重即可（避免重复扫描导致重复扣减）。
		uniq: list[Any] = []
		seen: set[int] = set()
		for p in pieces:
			if p is None:
				continue
			k = id(p)
			if k in seen:
				continue
			seen.add(k)
			uniq.append(p)
		return uniq

	def _coerce_piece_list(pieces_obj: Any) -> list[Any]:
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

	def _count_alive_pieces() -> int:
		# 以“场上未死亡棋子数”估算一轮的回合数。
		# 优先从 player1/player2.pieces 统计；缺失时回落到 action_queue。
		total = 0
		pieces = _iter_all_pieces()
		if pieces:
			seen_keys: set[int] = set()
			for p in pieces:
				try:
					if bool(getattr(p, "is_alive", True)):
						k = _piece_key(p)
						if k in seen_keys:
							continue
						seen_keys.add(k)
						total += 1
				except Exception:
					continue
			return max(1, int(total))
		try:
			q = list(getattr(env, "action_queue", []))
		except Exception:
			q = []
		for p in q:
			try:
				if p is not None and bool(getattr(p, "is_alive", True)):
					total += 1
			except Exception:
				continue
		return max(1, int(total))

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
		try:
			pid_dbg = int(getattr(piece, "id", -1))
		except Exception:
			pid_dbg = -1
		try:
			q_obj = getattr(env, "action_queue", [])
			q_len = len(list(q_obj))
		except Exception:
			q_len = -1
		_nddbg(env, f"KILL start: id={pid_dbg} reason={reason} q_len={q_len}")  # NDDBG

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
			q_obj2 = getattr(env, "action_queue", [])
			q_len2 = len(list(q_obj2))
		except Exception:
			q_len2 = -1
		_nddbg(env, f"KILL done:  id={pid_dbg} q_len_after={q_len2}")  # NDDBG

		try:
			setattr(piece, "death_round", int(getattr(env, "round_number", -1)))
		except Exception:
			pass

		try:
			state = _get_state()
			state.pop(_piece_key(piece), None)
		except Exception:
			pass

		_log(f"棋子死亡：{reason}")
		try:
			pid2 = int(getattr(piece, "id", -1))
		except Exception:
			pid2 = -1
		if pid2 >= 0:
			_sys(f"ID={pid2} 已死亡（{reason}）")

	# --- hook: handle_death_check ---
	ui_wrapper_installed = bool(getattr(env, "_ui_deathcheck_hook_installed", False))
	prev_impl = getattr(env, "_ui_handle_death_check_impl", None) if ui_wrapper_installed else getattr(env, "handle_death_check", None)
	if callable(prev_impl):
		setattr(env, "_ui_orig_handle_death_check", prev_impl)

	def handle_death_check_hook(target: Any) -> None:
		if not _near_enabled():
			orig = getattr(env, "_ui_orig_handle_death_check", None)
			if callable(orig):
				return orig(target)
			return

		cfg = _get_near_cfg()
		revive_hp = int(cfg.get("revive_hp_on_20", 1) or 1)
		# UI 文案已改为“经过 N 轮（= 若干回合）后死亡”，这里把 turns_to_die 视为“轮数”。
		rounds_to_die = int(cfg.get("turns_to_die", 1) or 1)
		rounds_to_die = max(1, min(3, rounds_to_die))
		die_on_damage = bool(cfg.get("die_on_damage_when_dying", True))

		if target is None:
			return

		# NOTE: 部分动作（尤其是法术）可能在一次结算过程中重复触发 handle_death_check。
		# 这会导致“刚进入濒死”紧接着又被误判为“濒死期间再次受伤”。
		# 用一个单调序号做轻量去重：若上一条 death_check 刚把该目标置为濒死，
		# 则紧随其后的下一次 death_check 不触发“再次受伤直接死亡”。
		try:
			seq = int(getattr(env, "_ui_near_death_deathcheck_seq", 0)) + 1
			setattr(env, "_ui_near_death_deathcheck_seq", seq)
		except Exception:
			seq = 0
		target_token = _piece_key(target)
		try:
			enter_map = getattr(env, "_ui_near_death_last_enter_dying_seq", None)
			if not isinstance(enter_map, dict):
				enter_map = {}
				setattr(env, "_ui_near_death_last_enter_dying_seq", enter_map)
		except Exception:
			enter_map = None

		# healed above 0 => clear dying
		try:
			hp_now = int(getattr(target, "health", 0))
		except Exception:
			hp_now = 0

		if hp_now > 0:
			_set_piece_dying(target, False)
			try:
				_get_state().pop(_piece_key(target), None)
			except Exception:
				pass
			return

		# already dying and got damaged again => direct death
		# NOTE: 后端/其它逻辑可能会在结算中短暂覆写 target.is_dying，
		# 因此这里同时以 _ui_near_death_state 作为“已处于濒死”的判据。
		try:
			state_now = _get_state()
		except Exception:
			state_now = {}
		was_dying_flag = bool(getattr(target, "is_dying", False))
		was_dying_state = bool(isinstance(state_now, dict) and target_token in state_now)
		if (was_dying_flag or was_dying_state) and die_on_damage:
			try:
				last_enter_seq = None if not isinstance(enter_map, dict) else enter_map.get(target_token)
			except Exception:
				last_enter_seq = None
			# 若刚在上一条 death_check 中进入濒死，则本次视为同一动作的重复回调，跳过“再次受伤”判定。
			if last_enter_seq is not None and seq and int(last_enter_seq) == int(seq) - 1:
				try:
					pid_dbg2s = int(getattr(target, "id", -1))
				except Exception:
					pid_dbg2s = -1
				_nddbg(env, f"death_check: skip immediate recheck after enter dying id={pid_dbg2s}")  # NDDBG
				return
			try:
				pid_dbg2 = int(getattr(target, "id", -1))
			except Exception:
				pid_dbg2 = -1
			_nddbg(env, f"death_check: dying damaged again => direct kill id={pid_dbg2}")  # NDDBG
			return _kill_piece(target, reason="濒死期间再次受伤")

		# perform death save
		roll = 0
		try:
			roll_func = getattr(env, "roll_dice", None)
			if callable(roll_func):
				roll = int(roll_func(1, 20))
		except Exception:
			roll = 0

		try:
			pid = int(getattr(target, "id", -1))
		except Exception:
			pid = -1
		piece_tag = f"ID={pid}" if pid >= 0 else "(unknown)"
		_log(f"触发死亡检定：{piece_tag} d20={roll if roll else '?'}")
		_nddbg(env, f"death_check roll: {piece_tag} d20={roll if roll else '?'}")  # NDDBG

		if roll == 20:
			# 角标：😇 显示 10 秒（由 UI 刷新时读取并自动过期）。
			try:
				piece_id = int(getattr(target, "id", -1))
			except Exception:
				piece_id = -1
			if piece_id >= 0:
				try:
					until_map = getattr(env, "_ui_board_angel_until", None)
					if not isinstance(until_map, dict):
						until_map = {}
						setattr(env, "_ui_board_angel_until", until_map)
					until_map[piece_id] = float(time.time() + 10.0)
				except Exception:
					pass
			_set_piece_health(target, max(1, revive_hp))
			_set_piece_dying(target, False)
			_set_piece_alive(target, True)
			try:
				_get_state().pop(_piece_key(target), None)
			except Exception:
				pass
			_log(f"死亡检定=20：恢复至 {max(1, revive_hp)}HP")
			_nddbg(env, f"death_check=20 revive: {piece_tag} hp={max(1, revive_hp)}")  # NDDBG
			return

		if roll == 1:
			_nddbg(env, f"death_check=1 direct death: {piece_tag}")  # NDDBG
			return _kill_piece(target, reason="死亡检定=1")

		# near-death
		_set_piece_health(target, 0)
		_set_piece_alive(target, True)
		_set_piece_dying(target, True)
		try:
			if isinstance(enter_map, dict) and seq:
				enter_map[target_token] = int(seq)
		except Exception:
			pass
		alive_cnt = _count_alive_pieces()
		remaining_turns = int(max(1, alive_cnt) * int(rounds_to_die))
		_get_state()[_piece_key(target)] = int(remaining_turns)
		_log(f"进入濒死：经过 {rounds_to_die} 轮（共 {remaining_turns} 回合）后死亡")
		_nddbg(
			env,
			f"enter dying: {piece_tag} rounds_to_die={rounds_to_die} remaining_turns={remaining_turns} alive_cnt={alive_cnt}",
		)  # NDDBG

	# 若 UI 已安装“死亡检定入口 hook”，则不要覆盖 env.handle_death_check，
	# 仅替换 impl（由 UI hook 负责记录/展示 d20，并调用 impl）。
	if ui_wrapper_installed:
		setattr(env, "_ui_handle_death_check_impl", handle_death_check_hook)
	else:
		setattr(env, "handle_death_check", handle_death_check_hook)

	# --- hook: input_manager.handle_action_input (skip dying turns) ---
	input_manager = getattr(env, "input_manager", None)
	if input_manager is not None:
		current_handle_action_input = getattr(input_manager, "handle_action_input", None)
		if callable(current_handle_action_input) and not bool(
			getattr(current_handle_action_input, "_ui_near_death_input_marker", False)
		):
			orig_handle_action_input = current_handle_action_input
			setattr(env, "_ui_orig_handle_action_input", orig_handle_action_input)

			def handle_action_input_hook(player_id: int, env_obj: Any):
				if _near_enabled():
					piece = getattr(env_obj, "current_piece", None)
					if piece is not None:
						try:
							hp = int(getattr(piece, "health", 0))
						except Exception:
							hp = 0
						if bool(getattr(piece, "is_dying", False)) and hp <= 0 and bool(getattr(piece, "is_alive", True)):
							# 濒死人物行动能力：若明确允许“移动”或“攻击/法术”，则不跳过。
							# 否则按默认口径：轮到其行动时跳过。
							cfg = _get_near_cfg()
							can_move = bool(cfg.get("can_move_when_dying", False))
							can_act = bool(cfg.get("can_attack_or_spell_when_dying", False))
							if not (can_move or can_act):
								# 倒计时在 step_hook 中按“每回合（env.step）”统一递减，避免重复扣减。
								try:
									pid_dbg3 = int(getattr(piece, "id", -1))
								except Exception:
									pid_dbg3 = -1
								_nddbg(env, f"handle_action_input: skip dying turn id={pid_dbg3}")  # NDDBG
								return None
				if callable(orig_handle_action_input):
					return orig_handle_action_input(player_id, env_obj)
				return None

			setattr(handle_action_input_hook, "_ui_near_death_input_marker", True)
			setattr(handle_action_input_hook, "_ui_near_death_input_orig", orig_handle_action_input)
			setattr(input_manager, "handle_action_input", handle_action_input_hook)

	# --- hook: execute_player_action (ensure die-on-damage for already-dying targets) ---
	current_exec = getattr(env, "execute_player_action", None)
	if callable(current_exec) and not bool(getattr(current_exec, "_ui_near_death_exec_marker", False)):
		orig_exec = current_exec
		setattr(env, "_ui_orig_execute_player_action_near_death", orig_exec)

		def execute_player_action_hook(action: Any = None):
			if not _near_enabled():
				return getattr(env, "_ui_orig_execute_player_action_near_death")(action)
			cfg = _get_near_cfg()
			die_on_damage = bool(cfg.get("die_on_damage_when_dying", True))
			# 仅处理“濒死期间再次受伤直接死亡”分支；关闭时完全委托原实现。
			if not die_on_damage:
				return getattr(env, "_ui_orig_execute_player_action_near_death")(action)

			try:
				state_pre = _get_state()
			except Exception:
				state_pre = {}
			dying_tokens_pre: set[int] = set(state_pre.keys()) if isinstance(state_pre, dict) else set()

			# 采集本次动作涉及的目标（尽量小范围，避免误杀）。
			targets: list[Any] = []
			attack_ctx = getattr(action, "attack_context", None)
			if bool(getattr(action, "attack", False)) and attack_ctx is not None:
				targets.append(getattr(attack_ctx, "target", None))
			spell_ctx = getattr(action, "spell_context", None)
			if bool(getattr(action, "spell", False)) and spell_ctx is not None:
				# 兼容不同实现的字段名
				tgt = getattr(spell_ctx, "target", None)
				if tgt is None:
					tgt = getattr(spell_ctx, "target_piece", None)
				targets.append(tgt)

			# 记录“动作前已处于濒死”的目标 token
			target_was_dying: dict[int, Any] = {}
			for t in targets:
				if t is None:
					continue
				try:
					if not bool(getattr(t, "is_alive", True)):
						continue
					token = _piece_key(t)
					hp = int(getattr(t, "health", 0))
				except Exception:
					continue
				# 仅当“已濒死（hp<=0）”时才计入（避免把 is_dying 未清理但已回血的情况误判）。
				if hp <= 0 and (token in dying_tokens_pre or bool(getattr(t, "is_dying", False))):
					target_was_dying[token] = t

			out = getattr(env, "_ui_orig_execute_player_action_near_death")(action)

			# 动作后：若对“已濒死”的目标造成了>0伤害，则直接击杀。
			# 说明：有些后端实现可能不会在 hp 已为 0 时再次调用 handle_death_check。
			for token, t in list(target_was_dying.items()):
				try:
					if t is None or not bool(getattr(t, "is_alive", True)):
						continue
					hp_post = int(getattr(t, "health", 0))
				except Exception:
					continue
				if hp_post > 0:
					continue
				damage = 0
				try:
					if bool(getattr(action, "attack", False)) and attack_ctx is not None and t is getattr(attack_ctx, "target", None):
						damage = int(getattr(attack_ctx, "damage_dealt", 0) or 0)
				except Exception:
					damage = 0
				try:
					if damage <= 0 and bool(getattr(action, "spell", False)) and spell_ctx is not None:
						damage = int(getattr(spell_ctx, "damage_dealt", 0) or 0)
				except Exception:
					pass
				if damage > 0:
					_nddbg(env, f"exec_action: dying damaged again => direct kill token={token} dmg={damage}")  # NDDBG
					_kill_piece(t, reason="濒死期间再次受伤")
			return out

		setattr(execute_player_action_hook, "_ui_near_death_exec_marker", True)
		setattr(execute_player_action_hook, "_ui_near_death_exec_orig", orig_exec)
		setattr(env, "execute_player_action", execute_player_action_hook)

	# --- hook: step (cleanup only) ---
	current_step = getattr(env, "step", None)
	if callable(current_step) and not bool(getattr(current_step, "_ui_near_death_step_marker", False)):
		orig_step = current_step
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
						_get_state().pop(_piece_key(p), None)
				except Exception:
					continue

			# 濒死倒计时：每回合（每次 step）统一递减。
			state = _get_state()
			alive_cnt = _count_alive_pieces()
			cfg = _get_near_cfg()
			try:
				rounds_to_die = int(cfg.get("turns_to_die", 1) or 1)
			except Exception:
				rounds_to_die = 1
			rounds_to_die = max(1, min(3, rounds_to_die))
			default_remaining = int(max(1, alive_cnt) * int(rounds_to_die))

			# 低频打印：仅当存在濒死状态或检测到濒死棋子时输出，避免刷屏。
			dy_state_nonempty = bool(state)

			dying_pieces: list[Any] = []
			for p in _iter_all_pieces():
				try:
					if not bool(getattr(p, "is_alive", True)):
						state.pop(_piece_key(p), None)
						continue
					hp = int(getattr(p, "health", 0))
					dy = bool(getattr(p, "is_dying", False))
				except Exception:
					continue
				if dy and hp <= 0:
					dying_pieces.append(p)
				elif dy and hp > 0:
					# 被治疗到 >0：清除濒死并清理计时
					_set_piece_dying(p, False)
					state.pop(_piece_key(p), None)

			if dying_pieces:
				try:
					ids_dbg = []
					for pp in dying_pieces:
						ids_dbg.append(int(getattr(pp, "id", -1)))
				except Exception:
					ids_dbg = []
				_nddbg(env, f"step: dying_detected ids={ids_dbg} state_keys={list(state.keys())[:10]}")  # NDDBG
				# 先扣减
				killed: list[Any] = []
				for p in dying_pieces:
					remaining = int(state.get(_piece_key(p), default_remaining))
					remaining -= 1
					state[_piece_key(p)] = int(remaining)
					try:
						pid_dbg4 = int(getattr(p, "id", -1))
					except Exception:
						pid_dbg4 = -1
					_nddbg(env, f"tick: id={pid_dbg4} remaining={remaining}")  # NDDBG
					if remaining <= 0:
						killed.append(p)
				for p in killed:
					_kill_piece(p, reason="濒死超时")
					state.pop(_piece_key(p), None)
					try:
						pid_dbg5 = int(getattr(p, "id", -1))
					except Exception:
						pid_dbg5 = -1
					_nddbg(env, f"tick: id={pid_dbg5} expired => killed")  # NDDBG
				# 输出系统通知（仅当仍存在濒死棋子时）
				items: list[str] = []
				for p in dying_pieces:
					try:
						if not bool(getattr(p, "is_alive", True)):
							continue
						if not bool(getattr(p, "is_dying", False)):
							continue
						pid = int(getattr(p, "id", -1))
						hp = int(getattr(p, "health", 0))
						if hp > 0:
							continue
						remaining = int(state.get(_piece_key(p), 0))
					except Exception:
						continue
					if remaining > 0:
						items.append(f"ID={pid} 剩余{remaining}回合")
				if items:
					_sys("濒死列表：" + "；".join(items))
			else:
				# 如果 state 非空但本回合没扫到濒死棋子，输出一次诊断（低频）
				if dy_state_nonempty:
					_nddbg(
						env,
						f"step: state_nonempty_but_no_dying; state_keys={list(state.keys())[:10]} q_len={len(list(getattr(env, 'action_queue', []) or []))}"
					)  # NDDBG

			try:
				q2 = list(getattr(env, "action_queue", []))
			except Exception:
				q2 = []
			try:
				alive_list = [p for p in q2 if p is not None and bool(getattr(p, "is_alive", True))]
			except Exception:
				alive_list = q2
			try:
				import numpy as np  # local import

				setattr(env, "action_queue", np.array(alive_list, dtype=object))
			except Exception:
				try:
					setattr(env, "action_queue", alive_list)
				except Exception:
					pass

			return out

		setattr(step_hook, "_ui_near_death_step_marker", True)
		setattr(step_hook, "_ui_near_death_step_orig", orig_step)
		setattr(env, "step", step_hook)
		_nddbg(env, "installed step_hook")  # NDDBG
	else:
		_nddbg(env, "skip installing step_hook (already marked)")  # NDDBG

	def _near_death_tick(reason: str = "") -> None:
		"""手动推进一次濒死倒计时。

		用于 UI 直接调用 execute_player_action/handle_death_check 而不走 env.step 的场景。
		低频：仅当存在 state 或检测到濒死棋子时打印。
		"""
		if not _near_enabled():
			return
		state = _get_state()
		dy_state_nonempty = bool(state)
		alive_cnt = _count_alive_pieces()
		cfg = _get_near_cfg()
		try:
			rounds_to_die = int(cfg.get("turns_to_die", 1) or 1)
		except Exception:
			rounds_to_die = 1
		rounds_to_die = max(1, min(3, rounds_to_die))
		default_remaining = int(max(1, alive_cnt) * int(rounds_to_die))

		dying_pieces: list[Any] = []
		for p in _iter_all_pieces():
			try:
				if not bool(getattr(p, "is_alive", True)):
					state.pop(_piece_key(p), None)
					continue
				hp = int(getattr(p, "health", 0))
				dy = bool(getattr(p, "is_dying", False))
			except Exception:
				continue
			if dy and hp <= 0:
				dying_pieces.append(p)
			elif dy and hp > 0:
				_set_piece_dying(p, False)
				state.pop(_piece_key(p), None)

		if dying_pieces:
			try:
				ids_dbg = [int(getattr(pp, "id", -1)) for pp in dying_pieces]
			except Exception:
				ids_dbg = []
			_nddbg(env, f"tick_manual: reason={reason} ids={ids_dbg} state_keys={list(state.keys())[:10]}")  # NDDBG
			killed: list[Any] = []
			for p in dying_pieces:
				remaining = int(state.get(_piece_key(p), default_remaining))
				remaining -= 1
				state[_piece_key(p)] = int(remaining)
				try:
					pid_dbg4 = int(getattr(p, "id", -1))
				except Exception:
					pid_dbg4 = -1
				_nddbg(env, f"tick_manual: id={pid_dbg4} remaining={remaining}")  # NDDBG
				if remaining <= 0:
					killed.append(p)
			for p in killed:
				_kill_piece(p, reason="濒死超时")
				state.pop(_piece_key(p), None)
				try:
					pid_dbg5 = int(getattr(p, "id", -1))
				except Exception:
					pid_dbg5 = -1
				_nddbg(env, f"tick_manual: id={pid_dbg5} expired => killed")  # NDDBG
			items: list[str] = []
			for p in dying_pieces:
				try:
					if not bool(getattr(p, "is_alive", True)):
						continue
					if not bool(getattr(p, "is_dying", False)):
						continue
					pid = int(getattr(p, "id", -1))
					hp = int(getattr(p, "health", 0))
					if hp > 0:
						continue
					remaining = int(state.get(_piece_key(p), 0))
				except Exception:
					continue
				if remaining > 0:
					items.append(f"ID={pid} 剩余{remaining}回合")
			if items:
				_sys("濒死列表：" + "；".join(items))
		elif dy_state_nonempty:
			_nddbg(env, f"tick_manual: state_nonempty_but_no_dying reason={reason} keys={list(state.keys())[:10]}")  # NDDBG

	# 暴露给 UI：每次动作后可手动 tick。
	try:
		setattr(env, "_ui_near_death_tick", _near_death_tick)
	except Exception:
		pass

	if already:
		_log("已刷新 playtest 规则 hooks")
	else:
		_log("已安装 playtest 规则 hooks")
	_nddbg(env, "hooks ready")  # NDDBG


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
