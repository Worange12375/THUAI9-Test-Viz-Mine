"""法术行动提交（Phase 2 拆分产物）。

本文件负责：
- 处理“行动面板 -> 确认行动 -> spell”分支。
- 覆盖：锁定法术（对棋子）/ 非锁定法术（对坐标/AOE）/ 位移/陷阱类法术的 UI 侧特殊处理。
- 保持行为不变：复用 MainUI 现有的方法（解析、结算辅助、日志、刷新、兜底等）。

不负责：
- 行动面板控件的创建与渲染（仍在 MainUI / views）。

设计说明：
- 目前为了最小改动，这里接收 `main_ui` 实例并直接访问其字段/方法。
"""

from __future__ import annotations

from typing import Any

from env import ActionSet, Area, SpellContext
from logic.test_mock_gameplay import ensure_test_mock_gameplay_installed


def _resolve_spell_targeting(
	main_ui: Any,
	env: Any,
	caster: Any,
	spell: Any,
	*,
	spell_range: float,
	area_radius: int,
	is_locking_spell: bool,
	caster_x: int,
	caster_y: int,
) -> tuple[Any | None, Any | None, list[str], list[Any], dict[int, int]] | None:
	"""解析法术目标（锁定/非锁定）并做基础校验。

	返回：
	- target_piece: 锁定法术的目标棋子（非锁定为 None）
	- target_area: 目标区域（锁定时 radius=0；非锁定时为 AOE 区域）
	- target_codes: 目标棋子的 short code 列表（用于日志展示）
	- target_pieces: 目标棋子对象列表
	- before_hp: 目标棋子的施法前 HP 快照（key=id(piece)）

	返回 None 表示已在此函数内写入 UI 失败提示并应直接 return。
	"""
	target_piece = None
	target_area = None
	target_codes: list[str] = []
	target_pieces: list[Any] = []
	before_hp: dict[int, int] = {}

	if is_locking_spell:
		target_text = main_ui.action_spell_target_var.get().strip()
		target_piece = main_ui._resolve_spell_target_piece(target_text, spell, caster)
		if target_piece is None:
			main_ui._set_action_feedback("行动失败：法术目标无效", False)
			return None
		target_pos = getattr(target_piece, "position", None)
		tx = int(getattr(target_pos, "x", -1)) if target_pos is not None else -1
		ty = int(getattr(target_pos, "y", -1)) if target_pos is not None else -1
		distance = ((caster_x - tx) ** 2 + (caster_y - ty) ** 2) ** 0.5
		if distance > spell_range:
			main_ui._set_action_feedback("行动失败：目标超出施法范围", False)
			return None
		target_area = Area(tx, ty, 0)
		target_codes = [main_ui._get_piece_short_code(target_piece)]
		target_pieces = [target_piece]
		before_hp[id(target_piece)] = int(getattr(target_piece, "health", 0))
		return target_piece, target_area, target_codes, target_pieces, before_hp

	try:
		tx = int(main_ui.action_spell_point_x_var.get().strip())
		ty = int(main_ui.action_spell_point_y_var.get().strip())
	except Exception:
		main_ui._set_action_feedback("行动失败：请输入合法施法坐标", False)
		return None
	board = getattr(env, "board", None)
	width = int(getattr(board, "width", 0)) if board is not None else 0
	height = int(getattr(board, "height", 0)) if board is not None else 0
	if not (0 <= tx < width and 0 <= ty < height):
		main_ui._set_action_feedback("行动失败：施法坐标越界", False)
		return None
	distance = ((caster_x - tx) ** 2 + (caster_y - ty) ** 2) ** 0.5
	if distance > spell_range:
		main_ui._set_action_feedback("行动失败：施法点超出施法范围", False)
		return None
	target_area = Area(tx, ty, max(0, area_radius))
	area_targets = main_ui._collect_area_spell_targets(env, caster, spell, target_area)
	target_codes = [main_ui._get_piece_short_code(p) for p in area_targets]
	target_pieces = list(area_targets)
	for p in area_targets:
		before_hp[id(p)] = int(getattr(p, "health", 0))
	return target_piece, target_area, target_codes, target_pieces, before_hp


def _try_handle_special_spell_types(
	main_ui: Any,
	env: Any,
	caster: Any,
	spell: Any,
	*,
	spell_cost: int,
	spell_name: str,
	is_teleport_spell: bool,
	is_trap_spell: bool,
) -> bool:
	"""处理位移/陷阱类法术（若命中则在此函数内完成并 return True）。"""
	if is_teleport_spell:
		success, summary, target_codes, damage_by_target = main_ui._apply_custom_teleport_spell(env, caster, spell, spell_cost)
		if not success:
			main_ui._set_action_feedback(summary, False)
			return True
		main_ui._append_runtime_action_log(
			actor_code=main_ui._get_piece_short_code(caster),
			action_label=f"法术:{spell_name}",
			summary=summary,
			targets=target_codes,
			damage_by_target=damage_by_target,
		)
		main_ui._try_trigger_runtime_trap_on_piece(env, caster, reason="位移完成触发")
		main_ui._set_action_feedback("行动成功", True)
		main_ui._update_cards_from_env()
		main_ui._refresh_piece_cards()
		main_ui._refresh_board_view()
		try:
			main_ui._flush_runtime_pending_messages(env)
		except Exception:
			pass
		return True

	if is_trap_spell:
		success, summary, target_codes, damage_by_target = main_ui._place_runtime_trap_spell(env, caster, spell, spell_cost)
		if not success:
			main_ui._set_action_feedback(summary, False)
			return True
		main_ui._append_runtime_action_log(
			actor_code=main_ui._get_piece_short_code(caster),
			action_label=f"法术:{spell_name}",
			summary=summary,
			targets=target_codes,
			damage_by_target=damage_by_target,
		)
		main_ui._set_action_feedback("行动成功", True)
		main_ui._update_cards_from_env()
		main_ui._refresh_piece_cards()
		main_ui._refresh_board_view()
		try:
			main_ui._flush_runtime_pending_messages(env)
		except Exception:
			pass
		return True

	return False


def _build_spell_action_set(
	*,
	caster: Any,
	spell: Any,
	target_piece: Any | None,
	target_area: Any,
	spell_cost: int,
) -> ActionSet:
	"""构造 SpellContext + ActionSet（不执行）。"""
	spell_context = SpellContext()
	spell_context.caster = caster
	spell_context.target = target_piece
	spell_context.spell = spell
	spell_context.target_area = target_area
	spell_context.is_delay_spell = bool(getattr(spell, "is_delay_spell", False))
	spell_context.delay_add = False
	spell_context.spell_cost = spell_cost
	spell_context.spell_lifespan = int(getattr(spell, "base_lifespan", 0))

	action = ActionSet()
	action.move = False
	action.attack = False
	action.spell = True
	action.spell_context = spell_context
	return action


def _execute_spell_action(env: Any, caster: Any, action: ActionSet) -> None:
	"""执行法术 action（与 main_ui 时代一致：先设置 env.current_piece）。"""
	setattr(env, "current_piece", caster)
	env.execute_player_action(action)


def _compute_spell_damage_by_target(
	main_ui: Any,
	env: Any,
	*,
	target_codes: list[str],
	before_hp: dict[int, int],
) -> dict[str, int]:
	"""统计每个目标 code 的掉血量（用于 action log 的 damage_by_target）。"""
	damage_by_target: dict[str, int] = {}
	for code in target_codes:
		piece = None
		for p in main_ui._coerce_piece_list(getattr(env, "action_queue", [])):
			if main_ui._get_piece_short_code(p) == code:
				piece = p
				break
		if piece is None:
			continue
		old_hp2 = before_hp.get(id(piece), int(getattr(piece, "health", 0)))
		new_hp2 = int(getattr(piece, "health", 0))
		delta = max(0, old_hp2 - new_hp2)
		if delta > 0:
			damage_by_target[code] = delta
	return damage_by_target


def _append_spell_formula_and_try_death_checks(
	main_ui: Any,
	env: Any,
	*,
	spell_name: str,
	target_pieces: list[Any],
	before_hp: dict[int, int],
) -> None:
	"""在右侧信息面板输出公式说明，并做必要的 HP 修正与死亡检定兜底。"""
	for p in target_pieces:
		if p is None:
			continue
		code = main_ui._get_piece_short_code(p)
		old_hp3 = before_hp.get(id(p), int(getattr(p, "health", 0)))
		new_hp3 = int(getattr(p, "health", 0))
		alive_flag = bool(getattr(p, "is_alive", True))
		dy_flag = bool(getattr(p, "is_dying", False))
		old_text = "💀" if dy_flag and int(old_hp3) <= 0 and alive_flag else str(old_hp3)
		new_text = "💀" if dy_flag and int(new_hp3) <= 0 and alive_flag else str(new_hp3)
		delta2 = int(old_hp3 - new_hp3)
		if delta2 > 0:
			main_ui.right_info_panel.append_content(
				f"\n[公式] 结算：{spell_name} 对 {code} 造成 {delta2} 点伤害（HP {old_text}->{new_text}）"
			)
		elif delta2 < 0:
			heal = -delta2
			main_ui.right_info_panel.append_content(
				f"\n[公式] 结算：{spell_name} 为 {code} 恢复 {heal} 点生命（HP {old_text}->{new_text}）"
			)
		if new_hp3 < 0:
			try:
				p.get_accessor().set_health_to(0)
			except Exception:
				setattr(p, "health", 0)
			new_hp3 = 0
		# 仅在“从 >0 降到 0”时兜底触发死亡检定，避免对已濒死(0HP)目标重复触发。
		if new_hp3 == 0 and int(old_hp3) > 0:
			# 若后端在 execute_player_action 内已触发死亡检定并进入濒死/死亡，则不要重复触发。
			try:
				already_dying = bool(getattr(p, "is_dying", False)) and int(getattr(p, "health", 0)) <= 0
			except Exception:
				already_dying = False
			try:
				alive_flag2 = bool(getattr(p, "is_alive", True))
			except Exception:
				alive_flag2 = True
			if not already_dying and alive_flag2:
				main_ui._handle_death_check_if_possible(env, p)


def _cleanup_spell_point_and_overlay_if_needed(main_ui: Any, spell: Any) -> None:
	"""清理施法点坐标与 AOE 预览，避免范围可视化残留。"""
	if not bool(getattr(spell, "is_locking_spell", False)):
		try:
			main_ui.action_spell_point_x_var.set("")
			main_ui.action_spell_point_y_var.set("")
		except Exception:
			pass
		try:
			main_ui.left_board_panel.set_spell_aoe_overlay([], "#f97316")
		except Exception:
			pass


def handle_preview_spell(main_ui: Any) -> None:
	"""提交法术行动（spell）。

	覆盖：
	- 锁定法术（对棋子）与非锁定法术（对坐标/AOE）
	- 位移类法术与陷阱类法术的 UI 侧特殊处理

	注意：目前仍复用 MainUI 的解析/结算辅助方法，保持行为不变。
	"""
	env = main_ui.controller.environment
	if env is None:
		main_ui._set_action_feedback("行动失败：环境未初始化", False)
		return
	ensure_test_mock_gameplay_installed(env)

	caster = main_ui._get_runtime_current_piece(env)
	if caster is None:
		main_ui._set_action_feedback("行动失败：未定位到当前行动棋子", False)
		return
	# 濒死行动限制：按玩法设计配置拦截。
	if main_ui._is_runtime_piece_in_near_death(env, caster) and not main_ui._near_death_can_act(env):
		main_ui._set_action_feedback("行动失败：濒死状态下不能攻击或法术", False)
		main_ui.right_info_panel.append_content("\n[UI] 法术提交失败：濒死状态下不能攻击或法术")
		return

	spell = main_ui._resolve_selected_spell()
	if spell is None:
		main_ui._set_action_feedback("行动失败：法术无效", False)
		return

	old_ap = int(getattr(caster, "action_points", 0))
	old_sp = int(getattr(caster, "spell_slots", 0))
	if old_ap <= 0:
		main_ui._set_action_feedback("行动失败：当前棋子行动位不足", False)
		return

	spell_cost = int(getattr(spell, "spell_cost", 1))
	if old_sp < spell_cost:
		main_ui._set_action_feedback("行动失败：当前棋子法术位不足", False)
		return

	spell_name = main_ui._spell_display_name(spell)
	spell_range = float(getattr(spell, "range", 0.0))
	is_locking_spell = bool(getattr(spell, "is_locking_spell", False))
	area_radius = int(getattr(spell, "area_radius", 0))
	is_teleport_spell = main_ui._is_teleport_spell(spell)
	is_trap_spell = main_ui._is_trap_spell(spell)

	caster_pos = getattr(caster, "position", None)
	caster_x = int(getattr(caster_pos, "x", -1)) if caster_pos is not None else -1
	caster_y = int(getattr(caster_pos, "y", -1)) if caster_pos is not None else -1

	if _try_handle_special_spell_types(
		main_ui,
		env,
		caster,
		spell,
		spell_cost=spell_cost,
		spell_name=spell_name,
		is_teleport_spell=is_teleport_spell,
		is_trap_spell=is_trap_spell,
	):
		return

	resolved = _resolve_spell_targeting(
		main_ui,
		env,
		caster,
		spell,
		spell_range=spell_range,
		area_radius=area_radius,
		is_locking_spell=is_locking_spell,
		caster_x=caster_x,
		caster_y=caster_y,
	)
	if resolved is None:
		return
	target_piece, target_area, target_codes, target_pieces, before_hp = resolved

	action = _build_spell_action_set(
		caster=caster,
		spell=spell,
		target_piece=target_piece,
		target_area=target_area,
		spell_cost=spell_cost,
	)
	_execute_spell_action(env, caster, action)

	new_ap = int(getattr(caster, "action_points", 0))
	new_sp = int(getattr(caster, "spell_slots", 0))
	damage_by_target = _compute_spell_damage_by_target(
		main_ui,
		env,
		target_codes=target_codes,
		before_hp=before_hp,
	)

	if new_ap == old_ap and new_sp == old_sp:
		main_ui._set_action_feedback("行动失败：法术未生效（目标/范围/资源不满足）", False)
		return

	main_ui.right_info_panel.append_content(f"\n[公式] 资源消耗：AP {old_ap}->{new_ap}，SP {old_sp}->{new_sp}")
	_append_spell_formula_and_try_death_checks(
		main_ui,
		env,
		spell_name=spell_name,
		target_pieces=target_pieces,
		before_hp=before_hp,
	)

	summary_targets = ",".join(target_codes) if target_codes else "无"
	summary = f"目标[{summary_targets}]，AP {old_ap}->{new_ap}，SP {old_sp}->{new_sp}"
	main_ui._append_runtime_action_log(
		actor_code=main_ui._get_piece_short_code(caster),
		action_label=f"法术:{spell_name}",
		summary=summary,
		targets=target_codes,
		damage_by_target=damage_by_target,
	)
	for p in target_pieces:
		if p is None:
			continue
		main_ui._append_runtime_death_and_game_over_info(p, main_ui._get_piece_short_code(p))

	_cleanup_spell_point_and_overlay_if_needed(main_ui, spell)
	main_ui._set_action_feedback("行动成功", True)
	main_ui._update_cards_from_env()
	main_ui._refresh_piece_cards()
	main_ui._refresh_board_view()
	try:
		main_ui._flush_runtime_pending_messages(env)
	except Exception:
		pass
	return
