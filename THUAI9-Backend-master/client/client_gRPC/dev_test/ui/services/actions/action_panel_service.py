"""ui.services.actions.action_panel_service

职责/边界
- 承载 `main_ui.py` 中“棋子行动面板”相关的大块逻辑：目标下拉收集、棋盘选点覆盖层、行动面板渲染、
  runtime 行动日志/公式输出、runtime 陷阱（延时法术）简化实现、以及“行动完毕”推进回合。

接口约定
- 本模块所有函数都以 `main_ui` 实例作为第一个参数；其余参数保持与 `MainUI` 同名方法签名一致。
- 该模块不拥有状态；状态读写仍落在 `main_ui` 实例字段上（例如 `action_*`、`runtime_*`）。

注意
- 这里的实现应保持与迁移前 `main_ui` 中逻辑等价；不改变 UI/流程/文案。
"""

from __future__ import annotations

from typing import Any, Optional

import tkinter as tk
from tkinter import ttk

import numpy as np

from env import Point
from logic.test_mock_gameplay import ensure_test_mock_gameplay_installed


def collect_action_target_options(main_ui: Any) -> list[str]:
	"""收集可用于攻击/法术下拉框的目标候选。"""
	env = main_ui.controller.environment
	if env is not None:
		current_piece = main_ui._get_runtime_current_piece(env)
		current_team = int(getattr(current_piece, "team", -1)) if current_piece is not None else -1
		options: list[str] = []
		for piece in main_ui._coerce_piece_list(getattr(env, "action_queue", [])):
			if not bool(getattr(piece, "is_alive", False)):
				continue
			piece_team = int(getattr(piece, "team", -1))
			if piece_team == current_team:
				continue
			options.append(main_ui._format_action_target_option(piece))
		if options:
			return options

	if main_ui.mock_initial_positions:
		return [
			f"ID{int(pid)} ({int(state.get('x', -1))}, {int(state.get('y', -1))})"
			for pid, state in sorted(main_ui.mock_initial_positions.items())
		]

	return ["目标A", "目标B"]


def format_action_target_option(main_ui: Any, piece: Any) -> str:
	piece_code = main_ui._get_piece_short_code(piece)
	x = int(getattr(getattr(piece, "position", None), "x", -1))
	y = int(getattr(getattr(piece, "position", None), "y", -1))
	return f"{piece_code} ({x}, {y})"


def resolve_action_target_piece(main_ui: Any, selected_text: str) -> Any:
	env = main_ui.controller.environment
	if env is None:
		return None
	current_piece = main_ui._get_runtime_current_piece(env)
	current_team = int(getattr(current_piece, "team", -1)) if current_piece is not None else -1
	for piece in main_ui._coerce_piece_list(getattr(env, "action_queue", [])):
		if not bool(getattr(piece, "is_alive", False)):
			continue
		if int(getattr(piece, "team", -1)) == current_team:
			continue
		if main_ui._format_action_target_option(piece) == selected_text:
			return piece
	return None


def get_piece_short_code(main_ui: Any, piece: Any) -> str:
	"""返回棋子简称（如 1A、2C），找不到时回退为 ?。"""
	if piece is None:
		return "?"

	if not main_ui.runtime_card_slots and main_ui.controller.environment is not None:
		main_ui._initialize_runtime_card_slots()

	for slot in main_ui.runtime_card_slots:
		if slot.get("piece") is piece:
			return str(slot.get("slot_code", "?"))

	env = main_ui.controller.environment
	if env is not None:
		for team_id, player_attr in ((1, "player1"), (2, "player2")):
			player = getattr(env, player_attr, None)
			pieces = main_ui._coerce_piece_list(getattr(player, "pieces", None) if player is not None else None)
			for idx, p in enumerate(pieces[:3], start=1):
				if p is piece:
					return main_ui._slot_code(team_id, idx)

	return "?"


def get_current_actor_text(main_ui: Any) -> str:
	env = main_ui.controller.environment
	if env is not None:
		curr = main_ui._get_runtime_current_piece(env)
		if curr is not None:
			piece_code = main_ui._get_piece_short_code(curr)
			pos = getattr(curr, "position", None)
			if pos is not None:
				return f"棋子{piece_code}({int(pos.x)},{int(pos.y)})"
			return f"棋子{piece_code}"
	return "棋子?(-,-)"


def stop_action_move_point_pick(main_ui: Any) -> None:
	main_ui.action_move_pick_waiting = False
	main_ui.action_pick_mode = ""
	overlay = main_ui.action_move_pick_overlay
	main_ui.action_move_pick_overlay = None
	if overlay is not None and overlay.winfo_exists():
		overlay.destroy()


def resolve_piece_at_board_xy(main_ui: Any, x: int, y: int) -> Any:
	env = main_ui.controller.environment
	if env is None:
		return None
	for piece in main_ui._coerce_piece_list(getattr(env, "action_queue", [])):
		if not bool(getattr(piece, "is_alive", False)):
			continue
		pos = getattr(piece, "position", None)
		px = int(getattr(pos, "x", -1)) if pos is not None else -1
		py = int(getattr(pos, "y", -1)) if pos is not None else -1
		if px == x and py == y:
			return piece
	return None


def on_action_move_pick_overlay_click(main_ui: Any, event: tk.Event) -> str:
	if not main_ui.action_move_pick_waiting:
		return "break"
	board_x, board_y = main_ui.left_board_panel.get_board_xy_from_root(int(event.x_root), int(event.y_root))
	if board_x is None or board_y is None:
		main_ui.right_info_panel.append_content("\n[UI] 请选择棋盘中的合法格子")
		return "break"
	if main_ui.action_pick_mode == "move":
		main_ui.action_move_x_var.set(str(board_x))
		main_ui.action_move_y_var.set(str(board_y))
		main_ui.right_info_panel.append_content(f"\n[UI] 已选定移动目标: ({board_x}, {board_y})")
	elif main_ui.action_pick_mode == "spell_point":
		main_ui.action_spell_point_x_var.set(str(board_x))
		main_ui.action_spell_point_y_var.set(str(board_y))
		main_ui.right_info_panel.append_content(f"\n[UI] 已选定法术施用坐标: ({board_x}, {board_y})")
	elif main_ui.action_pick_mode == "spell_target":
		selected_piece = main_ui._resolve_piece_at_board_xy(board_x, board_y)
		if selected_piece is None:
			main_ui.right_info_panel.append_content("\n[UI] 所点格子没有存活棋子")
			return "break"
		selected_option = main_ui._format_action_target_option(selected_piece)
		if selected_option not in main_ui.action_spell_target_option_map:
			main_ui.right_info_panel.append_content("\n[UI] 所点棋子不是该法术合法目标")
			return "break"
		main_ui.action_spell_target_var.set(selected_option)
		main_ui.right_info_panel.append_content(f"\n[UI] 已选定法术目标: {selected_option}")
	else:
		main_ui.right_info_panel.append_content("\n[UI] 当前不在选点模式")
		return "break"
	main_ui._stop_action_move_point_pick()
	return "break"


def _create_action_pick_overlay(main_ui: Any) -> tk.Toplevel:
	overlay = tk.Toplevel(main_ui.root)
	overlay.overrideredirect(True)
	overlay.attributes("-alpha", 0.01)
	overlay.attributes("-topmost", True)
	overlay.lift(main_ui.root)
	overlay.geometry(
		f"{main_ui.root.winfo_width()}x{main_ui.root.winfo_height()}+{main_ui.root.winfo_rootx()}+{main_ui.root.winfo_rooty()}"
	)
	overlay.bind("<Button-1>", main_ui._on_action_move_pick_overlay_click)
	overlay.bind("<ButtonRelease-1>", lambda _e: "break")
	return overlay


def begin_action_move_point_pick(main_ui: Any) -> None:
	if main_ui.controller.runtime_source != "runtime_env" or main_ui.controller.environment is None:
		main_ui._set_action_feedback("当前模式不支持棋盘选点", False)
		return
	main_ui._stop_action_move_point_pick()
	main_ui.action_move_pick_waiting = True
	main_ui.action_pick_mode = "move"
	overlay = _create_action_pick_overlay(main_ui)
	main_ui.action_move_pick_overlay = overlay
	main_ui.right_info_panel.append_content("\n[UI] 棋盘选点模式：请点击一个目标格")


def begin_action_spell_point_pick(main_ui: Any) -> None:
	if main_ui.controller.runtime_source != "runtime_env" or main_ui.controller.environment is None:
		main_ui._set_action_feedback("当前模式不支持法术棋盘选点", False)
		return
	main_ui._stop_action_move_point_pick()
	main_ui.action_move_pick_waiting = True
	main_ui.action_pick_mode = "spell_point"
	overlay = _create_action_pick_overlay(main_ui)
	main_ui.action_move_pick_overlay = overlay
	main_ui.right_info_panel.append_content("\n[UI] 法术坐标选点：请点击施法中心格")


def begin_action_spell_target_pick(main_ui: Any) -> None:
	if main_ui.controller.runtime_source != "runtime_env" or main_ui.controller.environment is None:
		main_ui._set_action_feedback("当前模式不支持法术目标选定", False)
		return
	if not main_ui.action_spell_target_option_map:
		main_ui._set_action_feedback("当前法术无有效目标，无法点选", False)
		return
	main_ui._stop_action_move_point_pick()
	main_ui.action_move_pick_waiting = True
	main_ui.action_pick_mode = "spell_target"
	overlay = _create_action_pick_overlay(main_ui)
	main_ui.action_move_pick_overlay = overlay
	main_ui.right_info_panel.append_content("\n[UI] 法术目标选定：请点击合法目标棋子所在格")


def build_runtime_turn_round_status(main_ui: Any) -> str:
	"""构造 runtime 模式下简洁回合信息文本。"""
	env = main_ui.controller.environment
	if main_ui.controller.runtime_source != "runtime_env" or env is None:
		return "【回合信息】当前为非 runtime 模式"

	alive_queue = [
		p
		for p in main_ui._coerce_piece_list(getattr(env, "action_queue", []))
		if bool(getattr(p, "is_alive", True))
	]
	total_alive = len(alive_queue)
	round_display = max(1, int(getattr(env, "round_number", 0)) + 1)

	if total_alive <= 0:
		return f"【回合信息】第{round_display}轮第0/0手，(总共)第{max(0, int(main_ui.runtime_completed_turns))}回合，当前行动：无"

	alive_ids = {int(getattr(p, "id", -1)) for p in alive_queue if int(getattr(p, "id", -1)) >= 0}
	done_count = len(alive_ids.intersection(main_ui.runtime_cycle_done_piece_ids))
	piece_turn_index = min(total_alive, done_count + 1)
	current_piece = main_ui._get_runtime_current_piece(env)
	current_code = main_ui._get_piece_short_code(current_piece) if current_piece is not None else "无"
	total_turn_display = max(1, int(main_ui.runtime_completed_turns) + 1)
	return (
		f"【回合信息】第{round_display}轮第{piece_turn_index}/{total_alive}手，"
		f"(总共)第{total_turn_display}回合，当前行动：{current_code}"
	)


def append_runtime_turn_round_status(main_ui: Any) -> None:
	"""将 runtime 回合信息追加到右下区（去重，避免刷屏）。"""
	line = main_ui._build_runtime_turn_round_status()
	if line == main_ui.runtime_last_round_info_line:
		return
	main_ui.runtime_last_round_info_line = line
	main_ui.right_info_panel.append_content(f"\n{line}")


def append_runtime_action_log(
	main_ui: Any,
	actor_code: str,
	action_label: str,
	summary: str,
	targets: Optional[list[str]] = None,
	damage_by_target: Optional[dict[str, int]] = None,
) -> None:
	"""输出简洁行动记录（黑色默认文本），并预留多目标伤害展示。"""
	parts = [f"行动记录：{actor_code} {action_label}，{summary}"]
	if targets:
		if damage_by_target:
			segments = []
			for target in targets:
				dmg = damage_by_target.get(target)
				segments.append(f"{target}({dmg})" if dmg is not None else f"{target}(?)")
			parts.append(f"受击：{'、'.join(segments)}")
		else:
			parts.append(f"目标：{'、'.join(targets)}")
	main_ui.right_info_panel.append_content(f"\n{'；'.join(parts)}")


def set_action_feedback(main_ui: Any, message: str, success: bool) -> None:
	label = main_ui.action_feedback_label
	if label is None:
		return
	if main_ui.action_feedback_clear_job is not None:
		try:
			main_ui.root.after_cancel(main_ui.action_feedback_clear_job)
		except Exception:
			pass
		main_ui.action_feedback_clear_job = None
	label.configure(text=message, foreground="#059669" if success else "#dc2626")
	if message:
		main_ui.action_feedback_clear_job = main_ui.root.after(5000, main_ui._clear_action_feedback)


def clear_action_feedback(main_ui: Any) -> None:
	main_ui.action_feedback_clear_job = None
	if main_ui.action_feedback_label is not None:
		main_ui.action_feedback_label.configure(text="")


def collapse_action_detail(main_ui: Any) -> None:
	main_ui._stop_action_move_point_pick()
	container = main_ui.action_detail_container
	if container is not None:
		for widget in container.winfo_children():
			widget.destroy()
	main_ui.action_mode_body_container = None
	if main_ui.action_confirm_button is not None:
		main_ui.action_confirm_button.pack_forget()
	main_ui.action_ui_mode.set("")
	main_ui.action_spell_target_option_map = {}
	main_ui._refresh_board_view()


def switch_action_mode(main_ui: Any, mode: str, body_container: ttk.Frame) -> None:
	main_ui._stop_action_move_point_pick()
	main_ui.action_spell_target_option_map = {}
	main_ui.action_ui_mode.set(mode)
	main_ui.action_mode_body_container = body_container
	for widget in body_container.winfo_children():
		widget.destroy()
	main_ui._render_action_mode_body(body_container)
	if main_ui.action_confirm_button is not None:
		main_ui.action_confirm_button.pack(side="left", padx=(8, 0))
	main_ui._set_action_feedback("", True)
	main_ui._refresh_board_view()


def rerender_attack_mode_if_needed(main_ui: Any) -> None:
	if main_ui._rendering_action_mode_body:
		return
	if main_ui.action_ui_mode.get().strip().lower() != "attack":
		return
	container = main_ui.action_mode_body_container
	if container is None:
		return
	for widget in container.winfo_children():
		widget.destroy()
	main_ui._render_action_mode_body(container)
	main_ui._refresh_board_view()


def refresh_custom_attack_preview(main_ui: Any) -> None:
	main_ui.action_custom_preview_var.set("")


def on_open_custom_attack_advanced_settings(main_ui: Any) -> None:
	return


def rerender_spell_mode_if_needed(main_ui: Any) -> None:
	if main_ui._rendering_action_mode_body:
		return
	if main_ui.action_ui_mode.get().strip().lower() != "spell":
		return
	container = main_ui.action_mode_body_container
	if container is None:
		return
	for widget in container.winfo_children():
		widget.destroy()
	main_ui._render_action_mode_body(container)
	main_ui._refresh_board_view()


def spell_display_name(main_ui: Any, spell: Any) -> str:
	name = str(getattr(spell, "name", "法术"))
	name_map = {
		"fireball": "火球术",
		"heal": "治疗术",
		"arrow hit": "箭击",
		"arrowhit": "箭击",
		"trap": "陷阱",
		"move": "瞬移",
		"teleport": "瞬移",
	}
	alias = name_map.get(name.lower(), "")
	if alias and alias != name:
		return f"{alias} ({name})"
	return name


def spell_effect_key(main_ui: Any, spell: Any) -> str:
	effect = getattr(spell, "effect_type", "")
	text = str(getattr(effect, "value", effect)).strip()
	return text.lower()


def collect_available_spell_options(main_ui: Any, caster: Any) -> tuple[list[str], dict[str, Any]]:
	env = main_ui.controller.environment
	if env is None or caster is None:
		return ["法术A"], {}
	fetcher = getattr(env, "get_available_spells", None)
	if not callable(fetcher):
		return ["法术A"], {}
	spells = [s for s in main_ui._coerce_piece_list(fetcher(caster)) if s is not None]
	if not spells:
		return ["法术A"], {}
	option_map: dict[str, Any] = {}
	options: list[str] = []
	for spell in spells:
		name = main_ui._spell_display_name(spell)
		is_locking = bool(getattr(spell, "is_locking_spell", False))
		target_text = "锁定" if is_locking else "非锁定"
		option = f"{name} [{target_text}]"
		option_map[option] = spell
		options.append(option)
	return options, option_map


def resolve_selected_spell(main_ui: Any) -> Any:
	selected = main_ui.action_spell_type_var.get().strip()
	return main_ui.action_spell_option_map.get(selected)


def collect_spell_target_options(main_ui: Any, spell: Any, caster: Any) -> list[str]:
	env = main_ui.controller.environment
	if env is None or spell is None or caster is None:
		return []
	fetcher = getattr(env, "get_spell_targets", None)
	if callable(fetcher):
		targets = [t for t in main_ui._coerce_piece_list(fetcher(spell, caster)) if t is not None]
		return [main_ui._format_action_target_option(t) for t in targets]
	return []


def resolve_spell_target_piece(main_ui: Any, selected_text: str, spell: Any, caster: Any) -> Any:
	mapped_piece = main_ui.action_spell_target_option_map.get(selected_text)
	if mapped_piece is not None:
		return mapped_piece
	env = main_ui.controller.environment
	if env is None:
		return None
	fetcher = getattr(env, "get_spell_targets", None)
	candidates: list[Any] = []
	if callable(fetcher):
		candidates = [t for t in main_ui._coerce_piece_list(fetcher(spell, caster)) if t is not None]
	else:
		candidates = [
			p
			for p in main_ui._coerce_piece_list(getattr(env, "action_queue", []))
			if bool(getattr(p, "is_alive", False))
		]
	for piece in candidates:
		if main_ui._format_action_target_option(piece) == selected_text:
			return piece
	return None


def collect_area_spell_targets(main_ui: Any, env: Any, caster: Any, spell: Any, area: Any) -> list[Any]:
	effect_key = main_ui._spell_effect_key(spell)
	targets: list[Any] = []
	for piece in main_ui._coerce_piece_list(getattr(env, "action_queue", [])):
		if not bool(getattr(piece, "is_alive", False)):
			continue
		contains = bool(getattr(area, "contains", lambda _p: False)(getattr(piece, "position", None)))
		if not contains:
			continue
		if effect_key in ("damage", "debuff"):
			if int(getattr(piece, "team", -1)) != int(getattr(caster, "team", -2)):
				targets.append(piece)
		elif effect_key in ("heal", "buff"):
			if int(getattr(piece, "team", -1)) == int(getattr(caster, "team", -2)):
				targets.append(piece)
		elif effect_key == "move":
			if piece is caster:
				targets.append(piece)
		else:
			targets.append(piece)
	return targets


def is_teleport_spell(main_ui: Any, spell: Any) -> bool:
	effect_key = main_ui._spell_effect_key(spell)
	name = str(getattr(spell, "name", "")).strip().lower()
	return effect_key == "move" or name in ("teleport", "move")


def is_trap_spell(main_ui: Any, spell: Any) -> bool:
	name = str(getattr(spell, "name", "")).strip().lower()
	return bool(getattr(spell, "is_delay_spell", False)) or "trap" in name


def apply_custom_teleport_spell(
	main_ui: Any,
	env: Any,
	caster: Any,
	spell: Any,
	spell_cost: int,
) -> tuple[bool, str, list[str], dict[str, int]]:
	try:
		tx = int(main_ui.action_spell_point_x_var.get().strip())
		ty = int(main_ui.action_spell_point_y_var.get().strip())
	except Exception:
		return False, "行动失败：请输入合法瞬移坐标", [], {}

	board = getattr(env, "board", None)
	width = int(getattr(board, "width", 0)) if board is not None else 0
	height = int(getattr(board, "height", 0)) if board is not None else 0
	if not (0 <= tx < width and 0 <= ty < height):
		return False, "行动失败：瞬移坐标越界", [], {}

	if board is not None:
		try:
			height_map = getattr(board, "height_map", None)
			if height_map is not None and int(height_map[tx][ty]) == -1:
				return False, "行动失败：目标地块不可传送", [], {}
		except Exception:
			return False, "行动失败：目标地块不可访问", [], {}

	occupant = main_ui._resolve_piece_at_board_xy(tx, ty)
	if occupant is not None and occupant is not caster:
		return False, "行动失败：目标格已有其他棋子", [], {}

	old_pos = getattr(caster, "position", None)
	old_x = int(getattr(old_pos, "x", -1)) if old_pos is not None else -1
	old_y = int(getattr(old_pos, "y", -1)) if old_pos is not None else -1
	if (old_x, old_y) == (tx, ty):
		return False, "行动失败：当前已在目标格", [], {}

	if board is not None:
		try:
			old_cell = board.grid[old_x][old_y]
			new_cell = board.grid[tx][ty]
			old_cell.state = 1
			old_cell.player_id = 0
			old_cell.piece_id = -1
			new_cell.state = 2
			new_cell.player_id = int(getattr(caster, "team", 0))
			new_cell.piece_id = int(getattr(caster, "id", -1))
		except Exception:
			pass

	caster.get_accessor().set_position(Point(tx, ty))
	caster.get_accessor().change_action_points_by(-1)
	caster.get_accessor().change_spell_slots_by(-spell_cost)
	summary = f"瞬移到({tx},{ty})，AP/SP 已消耗"
	return True, summary, [], {}


def place_runtime_trap_spell(
	main_ui: Any,
	env: Any,
	caster: Any,
	spell: Any,
	spell_cost: int,
) -> tuple[bool, str, list[str], dict[str, int]]:
	try:
		tx = int(main_ui.action_spell_point_x_var.get().strip())
		ty = int(main_ui.action_spell_point_y_var.get().strip())
	except Exception:
		return False, "行动失败：请输入合法陷阱坐标", [], {}

	board = getattr(env, "board", None)
	width = int(getattr(board, "width", 0)) if board is not None else 0
	height = int(getattr(board, "height", 0)) if board is not None else 0
	if not (0 <= tx < width and 0 <= ty < height):
		return False, "行动失败：陷阱坐标越界", [], {}

	base_lifespan = max(1, int(getattr(spell, "base_lifespan", 1)))
	base_value = max(0, int(getattr(spell, "base_value", 0)))
	trap = {
		"x": tx,
		"y": ty,
		"remaining": base_lifespan,
		"damage": base_value,
		"spell_name": main_ui._spell_display_name(spell),
		"caster_team": int(getattr(caster, "team", -1)),
	}
	main_ui.runtime_trap_effects.append(trap)
	caster.get_accessor().change_action_points_by(-1)
	caster.get_accessor().change_spell_slots_by(-spell_cost)

	# 若该格已有“非当前行动”的棋子，则陷阱在施放完成后立即触发并消失。
	occupant = main_ui._resolve_piece_at_board_xy(tx, ty)
	if occupant is not None and occupant is not caster and bool(getattr(occupant, "is_alive", True)):
		main_ui._try_trigger_runtime_trap_on_piece(
			env,
			occupant,
			reason="施放完成触发",
		)

	summary = f"在({tx},{ty})放置陷阱，持续{base_lifespan}回合"
	return True, summary, [], {}


def pop_runtime_trap_at_xy(main_ui: Any, x: int, y: int) -> dict[str, Any] | None:
	for trap in list(main_ui.runtime_trap_effects):
		if int(trap.get("remaining", 0)) <= 0:
			continue
		if int(trap.get("x", -1)) == int(x) and int(trap.get("y", -1)) == int(y):
			try:
				main_ui.runtime_trap_effects.remove(trap)
			except ValueError:
				pass
			return trap
	return None


def handle_death_check_if_possible(main_ui: Any, env: Any, piece: Any) -> None:
	if env is None or piece is None:
		return
	try:
		hp = int(getattr(piece, "health", 0))
	except Exception:
		hp = 0
	if hp < 0:
		try:
			piece.get_accessor().set_health_to(0)
		except Exception:
			setattr(piece, "health", 0)
		hp = 0
	# 仅当 HP==0 才触发死亡检定（0 才是死亡；负数视为非法并夹到 0）。
	if hp != 0:
		return
	try:
		if callable(getattr(env, "handle_death_check", None)):
			env.handle_death_check(piece)
	except Exception:
		return


def try_trigger_runtime_trap_on_piece(main_ui: Any, env: Any, piece: Any, *, reason: str) -> int | None:
	if piece is None or not bool(getattr(piece, "is_alive", True)):
		return None
	pos = getattr(piece, "position", None)
	x = int(getattr(pos, "x", -1)) if pos is not None else -1
	y = int(getattr(pos, "y", -1)) if pos is not None else -1
	trap = main_ui._pop_runtime_trap_at_xy(x, y)
	if trap is None:
		return None

	damage = max(0, int(trap.get("damage", 0)))
	old_hp = int(getattr(piece, "health", 0))
	try:
		if callable(getattr(piece, "receive_damage", None)):
			piece.receive_damage(damage, "physical")
		else:
			setattr(piece, "health", max(0, old_hp - damage))
	except Exception:
		setattr(piece, "health", max(0, old_hp - damage))
	new_hp = int(getattr(piece, "health", 0))
	if new_hp < 0:
		try:
			piece.get_accessor().set_health_to(0)
		except Exception:
			setattr(piece, "health", 0)
		new_hp = 0
	real = max(0, old_hp - new_hp)
	code = main_ui._get_piece_short_code(piece)

	main_ui._handle_death_check_if_possible(env, piece)
	main_ui._append_runtime_action_log(
		actor_code="TRAP",
		action_label=f"触发@({x},{y})",
		summary=f"{reason}，造成{real}点伤害，陷阱消失",
		targets=[code],
		damage_by_target={code: real},
	)
	main_ui._append_runtime_death_and_game_over_info(piece, code)
	return real


def tick_runtime_traps(main_ui: Any, env: Any, *, round_advanced: bool) -> None:
	"""按“回合”更新陷阱寿命。

	- 每进入新一轮(所有存活棋子行动时段结束一次)才递减 remaining
	- remaining 归零的陷阱自动消散
	- 触发伤害由动作执行后/行动时段结束时单独判定
	"""
	if not round_advanced or not main_ui.runtime_trap_effects:
		return
	next_traps: list[dict[str, Any]] = []
	for trap in main_ui.runtime_trap_effects:
		remaining = int(trap.get("remaining", 0)) - 1
		if remaining <= 0:
			continue
		trap["remaining"] = remaining
		next_traps.append(trap)
	main_ui.runtime_trap_effects = next_traps


def append_attack_formula_info(
	main_ui: Any,
	attack_type: str,
	attacker: Any,
	target: Any,
	*,
	attack_roll: int | None,
	raw_damage: int,
	real_damage: int,
	is_hit: bool,
) -> None:
	env = main_ui.controller.environment
	if env is None:
		return
	step_func = getattr(env, "step_modified_func", None)
	if not callable(step_func):
		return

	snapshot = getattr(env, "_ui_action_settings_snapshot", None)
	if not isinstance(snapshot, dict) or not snapshot:
		snapshot = (
			main_ui.action_settings_snapshot
			if isinstance(main_ui.action_settings_snapshot, dict)
			else main_ui._default_action_settings_snapshot()
		)
	attack_model = snapshot.get("attack_model", {}) if isinstance(snapshot, dict) else {}
	enable_d20 = bool(attack_model.get("enable_d20", True))
	hit_cfg = attack_model.get("hit", {}) if isinstance(attack_model.get("hit"), dict) else {}
	magic_hit_cfg = (
		attack_model.get("magic_hit", {})
		if isinstance(attack_model.get("magic_hit"), dict)
		else {}
	)
	phy_dmg_cfg = (
		attack_model.get("physical_damage", {})
		if isinstance(attack_model.get("physical_damage"), dict)
		else {}
	)
	mag_dmg_cfg = (
		attack_model.get("magic_damage", {})
		if isinstance(attack_model.get("magic_damage"), dict)
		else {}
	)
	fail_on_1 = bool(hit_cfg.get("fail_on_1", True))
	crit_on_20 = bool(hit_cfg.get("crit_on_20", True))

	advantage_func = getattr(env, "calculate_advantage_value", None)
	advantage_impl = callable(advantage_func)
	adv_value = 0
	if advantage_impl:
		try:
			adv_value = int(advantage_func(attacker, target))
		except Exception:
			adv_value = 0

	attack_name = "物理攻击" if attack_type == "物理攻击" else "普通法术攻击"
	roll_value = int(attack_roll) if (attack_roll is not None and enable_d20) else (0 if not enable_d20 else -1)

	if attack_type == "普通法术攻击":
		bonus_flat = float(magic_hit_cfg.get("bonus_flat", 0.0) or 0.0)
		coeff_int = float(magic_hit_cfg.get("coeff_intelligence", 1.0) or 1.0)
		adv_coeff = float(magic_hit_cfg.get("coeff_advantage", 1.0) or 1.0)
		def_attr = magic_hit_cfg.get("defense_modifier_attr", None)
		def_base_coeff = float(magic_hit_cfg.get("defense_base_coeff", 1.0) or 1.0)
		def_attr_coeff = float(magic_hit_cfg.get("defense_attr_coeff", 1.0) or 1.0)
		def_flat_bonus = float(magic_hit_cfg.get("defense_flat_bonus", 0.0) or 0.0)
		attack_part = int(step_func(int(getattr(attacker, "intelligence", 0))))
		attack_score = (
			(float(max(0, roll_value)) + bonus_flat + coeff_int * float(attack_part) + adv_coeff * float(adv_value))
			if roll_value >= 0
			else None
		)
		base_def = float(getattr(target, "magic_resist", 0))
		attr_def = (
			float(step_func(int(getattr(target, str(def_attr), 0))))
			if def_attr not in (None, "", "none")
			else 0.0
		)
		defense_score = def_base_coeff * base_def + def_attr_coeff * attr_def + def_flat_bonus
		symbol = ">" if (attack_score is not None and attack_score > defense_score) else "<="

		if enable_d20 and roll_value == 1 and fail_on_1:
			main_ui.right_info_panel.append_content(
				f"\n[公式] {attack_name}命中判定：天然1直接未命中（roll=1）"
			)
		elif enable_d20 and roll_value == 20 and crit_on_20:
			main_ui.right_info_panel.append_content(
				f"\n[公式] {attack_name}命中判定：天然20直接命中（roll=20）"
			)
		elif attack_score is not None:
			main_ui.right_info_panel.append_content(
				f"\n[公式] {attack_name}命中判定：{roll_value}(投掷)+{bonus_flat:.1f}(加值)+{coeff_int:.1f}*{attack_part}(智力修正)+{adv_coeff:.1f}*{adv_value:.0f}(优势) {symbol} "
				f"{def_base_coeff:.1f}*{int(base_def)}(法抗)+{def_attr_coeff:.1f}*{int(attr_def)}(防御修正)+{def_flat_bonus:.1f}(加值)；即 {attack_score:.1f} {symbol} {defense_score:.1f}"
			)
		else:
			main_ui.right_info_panel.append_content(f"\n[公式] {attack_name}命中判定：未捕获到投掷值")

		if not advantage_impl:
			main_ui.right_info_panel.append_content("\n[公式] 优势值：未实现，按 0 处理")

		resist_part = int(getattr(target, "magic_resist", 0))
		base_from_piece = bool(mag_dmg_cfg.get("base_from_piece", True))
		base_override = mag_dmg_cfg.get("base_override", None)
		if base_from_piece:
			base_damage = int(getattr(attacker, "magic_damage", 0))
			base_label = "法伤"
		else:
			try:
				base_damage = int(float(base_override)) if base_override is not None else 0
			except Exception:
				base_damage = 0
			base_label = "设定值"
		if not is_hit:
			main_ui.right_info_panel.append_content("\n[公式] 伤害计算：未命中，本次原始伤害=0；实际伤害=0")
		else:
			crit_text = " x2(暴击)" if (enable_d20 and roll_value == 20 and crit_on_20) else ""
			main_ui.right_info_panel.append_content(
				f"\n[公式] 伤害计算：原始伤害={base_damage}({base_label}){crit_text}={raw_damage}；实际伤害=max(0, {raw_damage}-{resist_part})={real_damage}"
			)
		return

	bonus_flat = float(hit_cfg.get("bonus_flat", 0.0) or 0.0)
	coeff_strength = float(hit_cfg.get("coeff_strength", 1.0) or 1.0)
	adv_coeff = float(hit_cfg.get("coeff_advantage", 1.0) or 1.0)
	def_attr = hit_cfg.get("defense_modifier_attr", "dexterity")
	def_base_coeff = float(hit_cfg.get("defense_base_coeff", 1.0) or 1.0)
	def_attr_coeff = float(hit_cfg.get("defense_attr_coeff", 1.0) or 1.0)
	def_flat_bonus = float(hit_cfg.get("defense_flat_bonus", 0.0) or 0.0)
	strength_part = int(step_func(int(getattr(attacker, "strength", 0))))
	resist_part = int(getattr(target, "physical_resist", 0))
	attack_score = (
		(float(max(0, roll_value)) + bonus_flat + coeff_strength * float(strength_part) + adv_coeff * float(adv_value))
		if roll_value >= 0
		else None
	)
	attr_def = (
		float(step_func(int(getattr(target, str(def_attr), 0))))
		if def_attr not in (None, "", "none")
		else 0.0
	)
	defense_score = def_base_coeff * float(resist_part) + def_attr_coeff * float(attr_def) + def_flat_bonus
	symbol = ">" if (attack_score is not None and attack_score > defense_score) else "<="

	if enable_d20 and roll_value == 1 and fail_on_1:
		main_ui.right_info_panel.append_content(
			f"\n[公式] {attack_name}命中判定：天然1直接未命中（roll=1）"
		)
	elif enable_d20 and roll_value == 20 and crit_on_20:
		main_ui.right_info_panel.append_content(
			f"\n[公式] {attack_name}命中判定：天然20直接命中（roll=20）"
		)
	elif attack_score is not None:
		main_ui.right_info_panel.append_content(
			f"\n[公式] {attack_name}命中判定：{roll_value}(投掷)+{bonus_flat:.1f}(加值)+{coeff_strength:.1f}*{strength_part}(力量修正)+{adv_coeff:.1f}*{adv_value:.0f}(优势) {symbol} "
			f"{def_base_coeff:.1f}*{resist_part}(物抗)+{def_attr_coeff:.1f}*{int(attr_def)}(防御修正)+{def_flat_bonus:.1f}(加值)；即 {attack_score:.1f} {symbol} {defense_score:.1f}"
		)
	else:
		main_ui.right_info_panel.append_content(f"\n[公式] {attack_name}命中判定：未捕获到投掷值")

	if not advantage_impl:
		main_ui.right_info_panel.append_content("\n[公式] 优势值：未实现，按 0 处理")

	base_from_piece = bool(phy_dmg_cfg.get("base_from_piece", True))
	base_override = phy_dmg_cfg.get("base_override", None)
	if base_from_piece:
		base_damage = int(getattr(attacker, "physical_damage", 0))
		base_label = "物伤"
	else:
		try:
			base_damage = int(float(base_override)) if base_override is not None else 0
		except Exception:
			base_damage = 0
		base_label = "设定值"
	if not is_hit:
		main_ui.right_info_panel.append_content("\n[公式] 伤害计算：未命中，本次原始伤害=0；实际伤害=0")
	else:
		crit_text = " x2(暴击)" if (enable_d20 and roll_value == 20 and crit_on_20) else ""
		main_ui.right_info_panel.append_content(
			f"\n[公式] 伤害计算：原始伤害={base_damage}({base_label}){crit_text}={raw_damage}；"
			f"实际伤害=max(0, {raw_damage}-{resist_part})={real_damage}"
		)


def append_runtime_death_and_game_over_info(main_ui: Any, target_piece: Any, target_code: str) -> None:
	env = main_ui.controller.environment
	if env is None:
		return
	# 保证日志顺序：先输出行动记录/公式，再输出死亡检定/濒死提示。
	main_ui._flush_runtime_pending_messages(env)
	if target_piece is not None and (not main_ui._is_piece_alive_by_hp(target_piece)):
		main_ui.right_info_panel.append_content(f"\n棋子 {target_code} 已死亡")
	main_ui._check_and_announce_runtime_game_over(env, show_dialog=True)


def render_action_mode_body(main_ui: Any, body_container: ttk.Frame) -> None:
	main_ui._rendering_action_mode_body = True
	try:
		mode = main_ui.action_ui_mode.get().strip().lower()

		if mode == "move":
			row = ttk.Frame(body_container)
			row.pack(fill="x")
			actor_text = main_ui._get_current_actor_text()
			main_ui.action_move_piece_var.set(actor_text)
			ttk.Label(row, text="移动").pack(side="left")
			ttk.Entry(row, textvariable=main_ui.action_move_piece_var, width=12, state="readonly").pack(
				side="left", padx=(4, 4)
			)
			ttk.Label(row, text="到 (").pack(side="left")
			tk.Entry(row, textvariable=main_ui.action_move_x_var, width=3).pack(side="left")
			ttk.Label(row, text=", ").pack(side="left")
			tk.Entry(row, textvariable=main_ui.action_move_y_var, width=3).pack(side="left")
			ttk.Label(row, text=")").pack(side="left")
			ttk.Button(row, text="棋盘选点", command=main_ui._begin_action_move_point_pick).pack(
				side="left", padx=(6, 0)
			)
			return

		target_options = main_ui._collect_action_target_options()

		if mode == "attack":
			attack_types = ["物理攻击", "普通法术攻击", "定制攻击"]
			if (
				not main_ui.action_attack_target_var.get().strip()
				or main_ui.action_attack_target_var.get() not in target_options
			):
				main_ui.action_attack_target_var.set(target_options[0])
			if (
				not main_ui.action_attack_type_var.get().strip()
				or main_ui.action_attack_type_var.get() not in attack_types
			):
				main_ui.action_attack_type_var.set(attack_types[0])

			row = ttk.Frame(body_container)
			row.pack(fill="x")
			ttk.Label(row, text="对").pack(side="left")
			ttk.Combobox(
				row,
				textvariable=main_ui.action_attack_target_var,
				values=target_options,
				state="readonly",
				width=18,
			).pack(side="left", padx=(4, 4))
			ttk.Label(row, text="使用").pack(side="left")
			attack_type_combo = ttk.Combobox(
				row,
				textvariable=main_ui.action_attack_type_var,
				values=attack_types,
				state="readonly",
				width=12,
			)
			attack_type_combo.pack(side="left", padx=(4, 4))
			attack_type_combo.bind("<<ComboboxSelected>>", lambda _e: main_ui._rerender_attack_mode_if_needed())
			ttk.Label(row, text="。").pack(side="left")

			if main_ui.action_attack_type_var.get().strip() == "定制攻击":
				row2 = ttk.Frame(body_container)
				row2.pack(fill="x", pady=(6, 0))
				ttk.Label(row2, text="造成").pack(side="left")
				tk.Entry(row2, textvariable=main_ui.action_custom_damage_var, width=6).pack(
					side="left", padx=(4, 4)
				)
				ttk.Label(row2, text="真实伤害").pack(side="left", padx=(0, 8))
				ttk.Button(row2, text="高级设置", command=main_ui._on_open_custom_attack_advanced_settings).pack(
					side="left", padx=(0, 8)
				)
				ttk.Label(row2, text="(测试用)", foreground="#6b7280").pack(side="left")
			return

		env = main_ui.controller.environment
		caster = main_ui._get_runtime_current_piece(env) if env is not None else None
		spell_options, spell_option_map = main_ui._collect_available_spell_options(caster)
		main_ui.action_spell_option_map = spell_option_map
		if (
			not main_ui.action_spell_type_var.get().strip()
			or main_ui.action_spell_type_var.get() not in spell_options
		):
			main_ui.action_spell_type_var.set(spell_options[0])

		row1 = ttk.Frame(body_container)
		row1.pack(fill="x")
		ttk.Label(row1, text="施用").pack(side="left")
		spell_combo = ttk.Combobox(
			row1,
			textvariable=main_ui.action_spell_type_var,
			values=spell_options,
			state="readonly",
			width=26,
		)
		spell_combo.pack(side="left", padx=(4, 4))
		spell_combo.bind("<<ComboboxSelected>>", lambda _e: main_ui._rerender_spell_mode_if_needed())
		ttk.Label(row1, text="法术。").pack(side="left")

		selected_spell = main_ui._resolve_selected_spell()
		if selected_spell is None:
			return

		is_locking_spell = bool(getattr(selected_spell, "is_locking_spell", False)) and not main_ui._is_teleport_spell(selected_spell)
		row2 = ttk.Frame(body_container)
		row2.pack(fill="x", pady=(6, 0))
		if is_locking_spell:
			target_candidates = main_ui._collect_spell_target_options(selected_spell, caster)
			main_ui.action_spell_target_option_map = {}
			for option in target_candidates:
				piece = main_ui._resolve_spell_target_piece(option, selected_spell, caster)
				if piece is not None:
					main_ui.action_spell_target_option_map[option] = piece
			if not target_candidates:
				target_candidates = ["无有效目标"]
			if (
				not main_ui.action_spell_target_var.get().strip()
				or main_ui.action_spell_target_var.get() not in target_candidates
			):
				main_ui.action_spell_target_var.set(target_candidates[0])
			ttk.Label(row2, text="对").pack(side="left")
			ttk.Combobox(
				row2,
				textvariable=main_ui.action_spell_target_var,
				values=target_candidates,
				state="readonly",
				width=18,
			).pack(side="left", padx=(4, 4))
			ttk.Button(row2, text="棋子点选", command=main_ui._begin_action_spell_target_pick).pack(
				side="left", padx=(4, 4)
			)
			ttk.Label(row2, text="施用").pack(side="left")
		else:
			main_ui.action_spell_target_option_map = {}
			ttk.Label(row2, text="在 (").pack(side="left")
			tk.Entry(row2, textvariable=main_ui.action_spell_point_x_var, width=4).pack(side="left")
			ttk.Label(row2, text=", ").pack(side="left")
			tk.Entry(row2, textvariable=main_ui.action_spell_point_y_var, width=4).pack(side="left")
			ttk.Label(row2, text=") 处施用").pack(side="left")
			ttk.Button(row2, text="棋盘选点", command=main_ui._begin_action_spell_point_pick).pack(
				side="left", padx=(4, 4)
			)
		ttk.Label(row2, text="。", foreground="#6b7280").pack(side="left")
	finally:
		main_ui._rendering_action_mode_body = False


def on_finish_current_piece_turn(main_ui: Any) -> None:
	"""结束当前棋子行动时段：若未提交动作，则按空行动推进到下一棋子。"""
	main_ui._stop_action_move_point_pick()
	if main_ui.controller.runtime_source != "runtime_env" or main_ui.controller.environment is None:
		main_ui.right_info_panel.append_content("\n[UI] 仅 runtime 模式支持“行动完毕”")
		return
	env = main_ui.controller.environment
	piece = main_ui._get_runtime_current_piece(env)
	if piece is None:
		main_ui.right_info_panel.append_content("\n[UI] 当前无可行动棋子")
		main_ui._set_action_feedback("行动失败：当前无可行动棋子", False)
		return
	piece_code = main_ui._get_piece_short_code(piece)
	main_ui.right_info_panel.append_content(f"\n[UI] 行动完毕：结束 {piece_code} 的行动时段")
	main_ui.runtime_completed_turns += 1
	curr_id = int(getattr(piece, "id", -1))
	if curr_id >= 0:
		main_ui.runtime_cycle_done_piece_ids.add(curr_id)
	ended_piece = piece

	alive_queue = [
		p
		for p in main_ui._coerce_piece_list(getattr(env, "action_queue", []))
		if bool(getattr(p, "is_alive", True))
	]
	if not alive_queue:
		main_ui._set_action_feedback("行动失败：当前无可行动棋子", False)
		return

	try:
		idx = next(i for i, p in enumerate(alive_queue) if p is piece)
	except StopIteration:
		idx = 0
	rotated = alive_queue[idx + 1 :] + alive_queue[: idx + 1]
	setattr(env, "action_queue", np.array(rotated, dtype=object))
	setattr(env, "current_piece", rotated[0] if rotated else None)

	alive_ids = {int(getattr(p, "id", -1)) for p in rotated if int(getattr(p, "id", -1)) >= 0}
	round_advanced = False
	if alive_ids and main_ui.runtime_cycle_done_piece_ids.issuperset(alive_ids):
		for p in rotated:
			if bool(getattr(p, "is_alive", True)):
				p.set_action_points(int(getattr(p, "max_action_points", getattr(p, "action_points", 0))))
		main_ui.runtime_cycle_done_piece_ids.clear()
		setattr(env, "round_number", int(getattr(env, "round_number", 0)) + 1)
		round_advanced = True
		main_ui.right_info_panel.append_content("\n[UI] 新一轮开始：已重置全部存活棋子的行动位")

	# 行动时段结束后：若结束行动的棋子站在陷阱上，且此刻不再是当前行动，则触发并消失。
	if ended_piece is not getattr(env, "current_piece", None):
		main_ui._try_trigger_runtime_trap_on_piece(env, ended_piece, reason="行动完毕触发")

	main_ui._tick_runtime_traps(env, round_advanced=round_advanced)

	# 濒死系统：倒计时口径=行动队列推进一次（相当于一个“回合/turn”）。
	# UI 的手动行动不会调用 env.step，因此在“行动完毕”这里手动推进一次。
	try:
		ensure_test_mock_gameplay_installed(env)
		tick = getattr(env, "_ui_near_death_tick", None)
		if callable(tick):
			tick("end_turn")
		main_ui._flush_runtime_pending_messages(env)
		# tick 可能导致棋子死亡（例如濒死超时），需要立刻结算胜负。
		main_ui._check_and_announce_runtime_game_over(env, show_dialog=True)
	except Exception:
		pass

	main_ui._append_runtime_turn_round_status()

	main_ui._collapse_action_detail()
	main_ui._set_action_feedback("已结束当前行动时段", True)
	main_ui._update_cards_from_env()
	main_ui._refresh_piece_cards()
	main_ui._refresh_board_view()
	main_ui._on_click_piece_action()


def on_click_piece_action(main_ui: Any) -> None:
	"""点击“棋子行动”后，在可变区显示行动编辑面板。"""
	main_ui.right_top_composite_panel.clear_variable_area()
	main_ui.action_panel_status_label = None

	container = ttk.Frame(main_ui.right_top_composite_panel.variable_frame)
	container.pack(fill="both", expand=True)
	container.columnconfigure(0, weight=1)

	main_ui.action_panel_status_label = ttk.Label(container, text="", foreground="#374151")
	main_ui.action_panel_status_label.grid(row=0, column=0, sticky="w", pady=(0, 6))
	main_ui._refresh_piece_action_status_line()

	row1 = ttk.Frame(container)
	row1.grid(row=1, column=0, sticky="ew", pady=(0, 6))
	row1.columnconfigure(0, weight=1)
	row1.columnconfigure(1, weight=1)
	row1.columnconfigure(2, weight=1)

	ttk.Button(row1, text="移动", command=lambda: main_ui._switch_action_mode("move", row2)).grid(
		row=0, column=0, sticky="ew", padx=(0, 4)
	)
	ttk.Button(row1, text="攻击", command=lambda: main_ui._switch_action_mode("attack", row2)).grid(
		row=0, column=1, sticky="ew", padx=4
	)
	ttk.Button(row1, text="法术", command=lambda: main_ui._switch_action_mode("spell", row2)).grid(
		row=0, column=2, sticky="ew", padx=(4, 0)
	)

	row2 = ttk.Frame(container)
	row2.grid(row=2, column=0, sticky="ew")
	main_ui.action_detail_container = row2

	submit_row = ttk.Frame(container)
	submit_row.grid(row=3, column=0, sticky="ew", pady=(6, 0))
	main_ui.action_confirm_button = ttk.Button(submit_row, text="确认行动", command=main_ui._on_preview_submit_action)
	ttk.Button(submit_row, text="行动完毕", command=main_ui._on_finish_current_piece_turn).pack(side="left", padx=(8, 0))

	feedback_row = ttk.Frame(container)
	feedback_row.grid(row=4, column=0, sticky="w", pady=(4, 0))
	main_ui.action_feedback_label = ttk.Label(feedback_row, text="", foreground="#059669")
	main_ui.action_feedback_label.pack(side="left")

	main_ui.right_info_panel.append_content("\n[UI] 已进入棋子行动面板：请选择移动/攻击/法术，或点击行动完毕")
	main_ui._append_runtime_turn_round_status()
