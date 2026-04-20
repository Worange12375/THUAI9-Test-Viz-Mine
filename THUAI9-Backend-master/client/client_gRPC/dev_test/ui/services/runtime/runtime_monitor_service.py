"""Runtime monitor 服务。

本文件负责从 `main_ui.py` 下沉的“运行时监控类逻辑”，包括：
- 统一存活判定（兼容濒死系统）；
- flush runtime env 暂存信息（并把 ID=xx 替换为棋子代号）；
- 😇 角标到期刷新调度；
- UI 侧主动检查并播报胜负。

约束：
- 不创建/布局 Tk 控件；
- 不 import main_ui（避免循环依赖）；
- 通过 duck-typing 访问 main_ui 的方法与字段，保持 UX/行为不变。
"""

from __future__ import annotations

import re
import time
from typing import Any


def get_runtime_near_death_cfg(env: Any) -> dict[str, Any]:
	cfg = getattr(env, "_ui_near_death_config", None)
	return cfg if isinstance(cfg, dict) else {}


def is_runtime_piece_in_near_death(env: Any, piece: Any) -> bool:
	if env is None or piece is None:
		return False
	cfg = get_runtime_near_death_cfg(env)
	if not bool(cfg.get("enabled", False)):
		return False
	try:
		is_dying = bool(getattr(piece, "is_dying", False))
		hp = int(getattr(piece, "health", 0))
		alive = bool(getattr(piece, "is_alive", True))
	except Exception:
		return False
	return bool(is_dying and alive and hp <= 0)


def near_death_can_move(env: Any) -> bool:
	cfg = get_runtime_near_death_cfg(env)
	return bool(cfg.get("can_move_when_dying", False))


def near_death_can_act(env: Any) -> bool:
	cfg = get_runtime_near_death_cfg(env)
	return bool(cfg.get("can_attack_or_spell_when_dying", False))


def is_piece_alive_by_hp(main_ui: Any, piece: Any) -> bool:
	"""统一存活判定。

	- 默认：仅 HP>0 视为存活；HP==0 视为死亡。
	- 若启用“濒死系统”（测试端注入）：允许出现 HP==0 且 is_dying==True 的“仍存活”状态。

	说明：负 HP 在初始化输入阶段视为非法；在对局结算中若出现负值，这里按 0 处理。
	"""
	if piece is None:
		return False
	try:
		hp = int(getattr(piece, "health", 0))
	except Exception:
		hp = 0
	if hp < 0:
		hp = 0

	try:
		alive_flag = bool(getattr(piece, "is_alive", True))
	except Exception:
		alive_flag = True
	if not alive_flag:
		return False

	# 濒死系统：HP==0 且 is_dying==True 仍视为“存活”。
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	near_cfg = getattr(env, "_ui_near_death_config", None) if env is not None else None
	near_enabled = bool(near_cfg.get("enabled", False)) if isinstance(near_cfg, dict) else False
	if near_enabled:
		try:
			dy = bool(getattr(piece, "is_dying", False))
		except Exception:
			dy = False
		if dy and hp <= 0:
			return True

	return hp > 0


def flush_runtime_pending_messages(main_ui: Any, env: Any) -> None:
	if env is None:
		return
	try:
		pending = getattr(env, "_ui_pending_info_messages", None)
	except Exception:
		pending = None
	if not isinstance(pending, list) or not pending:
		return

	# 濒死/死亡系统消息多用 ID=xx 标记棋子；对玩家不直观。
	# 这里在 UI flush 时统一把 ID=xx 替换为棋子代号（如 1A、2B）。
	id_to_code: dict[int, str] = {}
	try:
		all_pieces: list[Any] = []
		all_pieces.extend(main_ui._coerce_piece_list(getattr(getattr(env, "player1", None), "pieces", [])))
		all_pieces.extend(main_ui._coerce_piece_list(getattr(getattr(env, "player2", None), "pieces", [])))
		all_pieces.extend(main_ui._coerce_piece_list(getattr(env, "action_queue", [])))
		for p in all_pieces:
			if p is None:
				continue
			try:
				pid = int(getattr(p, "id", -1))
			except Exception:
				pid = -1
			if pid < 0 or pid in id_to_code:
				continue
			try:
				code = str(main_ui._get_piece_short_code(p))
			except Exception:
				code = ""
			if code:
				id_to_code[pid] = code
	except Exception:
		id_to_code = {}
	try:
		setattr(env, "_ui_pending_info_messages", [])
	except Exception:
		pending.clear()

	# 统一按队列顺序刷到右侧日志。
	id_pat = re.compile(r"\bID=(\-?\d+)\b")
	for msg in pending:
		try:
			text = str(msg)
			if id_to_code and "ID=" in text:

				def _rep(m: re.Match[str]) -> str:
					try:
						pid2 = int(m.group(1))
					except Exception:
						return m.group(0)
					code2 = id_to_code.get(pid2)
					return code2 if code2 else m.group(0)

				text = id_pat.sub(_rep, text)
			main_ui.right_info_panel.append_content(f"\n{text}")
		except Exception:
			continue


def mark_runtime_piece_angel(main_ui: Any, env: Any, piece: Any, *, seconds: float) -> None:
	"""为棋盘角标设置 😇，并安排到期刷新。"""
	if env is None or piece is None:
		return
	try:
		piece_id = int(getattr(piece, "id", -1))
	except Exception:
		piece_id = -1
	if piece_id < 0:
		return
	until_map = getattr(env, "_ui_board_angel_until", None)
	if not isinstance(until_map, dict):
		until_map = {}
		setattr(env, "_ui_board_angel_until", until_map)
	until_map[piece_id] = float(time.time() + max(0.0, float(seconds)))
	schedule_runtime_angel_refresh(main_ui, env)


def schedule_runtime_angel_refresh(main_ui: Any, env: Any) -> None:
	"""按最早过期时间安排一次刷新，让 😇 角标自动消失。"""
	if env is None:
		return
	until_map = getattr(env, "_ui_board_angel_until", None)
	if not isinstance(until_map, dict) or not until_map:
		return
	try:
		now = float(time.time())
	except Exception:
		now = 0.0
	try:
		min_until = min(float(v) for v in until_map.values() if v is not None)
	except Exception:
		return
	delay_s = max(0.0, min_until - now)
	delay_ms = max(50, int(delay_s * 1000) + 30)
	# 取消旧定时器，避免堆积。
	if getattr(main_ui, "_angel_refresh_job", None) is not None:
		try:
			main_ui.root.after_cancel(main_ui._angel_refresh_job)
		except Exception:
			pass
		main_ui._angel_refresh_job = None

	def _do_refresh() -> None:
		main_ui._angel_refresh_job = None
		try:
			if main_ui.root is None or not bool(main_ui.root.winfo_exists()):
				return
		except Exception:
			return
		try:
			main_ui._refresh_piece_cards()
		except Exception:
			pass
		try:
			main_ui._refresh_board_view()
		except Exception:
			pass

	try:
		main_ui._angel_refresh_job = main_ui.root.after(delay_ms, _do_refresh)
	except Exception:
		main_ui._angel_refresh_job = None


def check_and_announce_runtime_game_over(main_ui: Any, env: Any, *, show_dialog: bool) -> None:
	"""在 UI 侧主动检查并播报胜负。

	用于：
	- 手动应用属性后（可能直接把某方全灭）
	- 初始化配置应用后（防止 0HP 开局未触发任何行动导致不结算）
	"""
	if env is None:
		return
	# 去重：若 env 或 UI 已标记结束，则不重复播报。
	if bool(getattr(env, "is_game_over", False)) or bool(getattr(main_ui, "game_over_message_shown", False)):
		return
	p1_pieces = main_ui._coerce_piece_list(getattr(getattr(env, "player1", None), "pieces", []))
	p2_pieces = main_ui._coerce_piece_list(getattr(getattr(env, "player2", None), "pieces", []))
	p1_alive = any(is_piece_alive_by_hp(main_ui, p) for p in p1_pieces)
	p2_alive = any(is_piece_alive_by_hp(main_ui, p) for p in p2_pieces)
	if p1_alive and p2_alive:
		return
	winner = "玩家1" if p1_alive else ("玩家2" if p2_alive else "无人")
	setattr(env, "is_game_over", True)
	main_ui.game_over_message_shown = True
	main_ui.right_info_panel.append_content(f"\n游戏结束，胜者：{winner}")
	if show_dialog and getattr(getattr(main_ui, "controller", None), "runtime_source", None) == "runtime_env":
		main_ui._show_game_over_reset_dialog()


def on_event_game_loaded(main_ui: Any, event: Any) -> None:
	main_ui.runtime_trap_effects = []
	main_ui.game_over_message_shown = False
	try:
		payload = getattr(event, "payload", {})
		source = payload.get("source") if isinstance(payload, dict) else None
		mode = payload.get("mode") if isinstance(payload, dict) else None
		main_ui.right_info_panel.append_content(f"\n[EVENT] GAME_LOADED source={source} mode={mode}")
	except Exception:
		main_ui.right_info_panel.append_content("\n[EVENT] GAME_LOADED")


def on_event_round_started(main_ui: Any, event: Any) -> None:
	try:
		payload = getattr(event, "payload", {})
		round_number = payload.get("round_number") if isinstance(payload, dict) else None
		source = payload.get("source") if isinstance(payload, dict) else None
		main_ui.right_info_panel.append_content(
			f"\n[EVENT] ROUND_STARTED round={round_number} source={source}"
		)
	except Exception:
		main_ui.right_info_panel.append_content("\n[EVENT] ROUND_STARTED")


def on_event_round_finished(main_ui: Any, event: Any) -> None:
	try:
		payload = getattr(event, "payload", {})
		round_number = payload.get("round_number") if isinstance(payload, dict) else None
		is_game_over = payload.get("is_game_over") if isinstance(payload, dict) else None
		main_ui.right_info_panel.append_content(
			f"\n[EVENT] ROUND_FINISHED round={round_number} game_over={is_game_over}"
		)
	except Exception:
		main_ui.right_info_panel.append_content("\n[EVENT] ROUND_FINISHED")


def on_event_game_over(main_ui: Any, _event: Any) -> None:
	if bool(getattr(main_ui, "game_over_message_shown", False)):
		return
	env = getattr(getattr(main_ui, "controller", None), "environment", None)
	winner = "未知"
	if env is not None:
		p1_alive = any(
			bool(getattr(p, "is_alive", False))
			for p in main_ui._coerce_piece_list(getattr(getattr(env, "player1", None), "pieces", []))
		)
		p2_alive = any(
			bool(getattr(p, "is_alive", False))
			for p in main_ui._coerce_piece_list(getattr(getattr(env, "player2", None), "pieces", []))
		)
		winner = "玩家1" if p1_alive else ("玩家2" if p2_alive else "无人")
	main_ui.game_over_message_shown = True
	main_ui.right_info_panel.append_content(f"\nGAME_OVER，胜者：{winner}")
