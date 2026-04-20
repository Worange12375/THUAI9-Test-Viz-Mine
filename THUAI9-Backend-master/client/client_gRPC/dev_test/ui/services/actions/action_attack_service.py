"""攻击行动提交（Phase 2 拆分产物）。

本文件负责：
- 处理“行动面板 -> 确认行动 -> attack”分支。
- 覆盖：物理攻击 / 普通法术攻击 / 定制攻击（真实伤害测试用）。
- 保持行为不变：复用 MainUI 现有的方法（日志、刷新、目标解析、兜底等）。

不负责：
- 行动面板控件的创建与渲染（仍在 MainUI / views）。

设计说明：
- 目前为了最小改动，这里接收 `main_ui` 实例并直接访问其字段/方法。
"""

from __future__ import annotations

from typing import Any

from env import ActionSet, AttackContext
from logic.test_mock_gameplay import ensure_test_mock_gameplay_installed


def _ensure_test_mock_gameplay_installed_best_effort_for_attack(env: Any) -> None:
	"""确保测试端玩法 hooks 已安装（best-effort）。

	为什么只对 attack 做 logger：
	- attack 分支里更依赖“濒死系统”等 house rules 的即时提示；
	- 这里把 hooks 安装过程中的信息写入 `env._ui_pending_info_messages`，最后由 UI flush。
	"""
	# 确保测试端玩法 hooks 已安装：濒死系统的判定逻辑仅来自 dev_test/logic/test_mock_gameplay.py。
	# 避免未安装 hooks 时落回后端 handle_death_check（后端实现不支持濒死分支）。
	try:
		def _queue_house_rule_msg(msg: str) -> None:
			try:
				pending = getattr(env, "_ui_pending_info_messages", None)
				if not isinstance(pending, list):
					pending = []
					setattr(env, "_ui_pending_info_messages", pending)
				pending.append(str(msg))
			except Exception:
				return

		ensure_test_mock_gameplay_installed(env, logger=_queue_house_rule_msg)
	except Exception:
		try:
			ensure_test_mock_gameplay_installed(env)
		except Exception:
			pass


def _get_action_settings_snapshot(main_ui: Any, env: Any) -> dict[str, Any]:
	"""读取“行动设置（本局）”快照。

	优先级：
	1) runtime env 上的 `env._ui_action_settings_snapshot`
	2) MainUI 上的 `action_settings_snapshot`
	3) MainUI 的默认值 `_default_action_settings_snapshot()`
	"""
	snapshot = getattr(env, "_ui_action_settings_snapshot", None)
	if not isinstance(snapshot, dict) or not snapshot:
		snapshot = (
			main_ui.action_settings_snapshot
			if isinstance(getattr(main_ui, "action_settings_snapshot", None), dict)
			else main_ui._default_action_settings_snapshot()
		)
	return snapshot if isinstance(snapshot, dict) else {}


def _perform_physical_attack(
	env: Any,
	current_piece: Any,
	target_piece: Any,
	*,
	enable_d20: bool,
	hit_cfg: dict[str, Any],
	fail_on_1: bool,
	crit_on_20: bool,
) -> tuple[int | None, int, bool | None]:
	"""执行“物理攻击”分支。

	返回：
	- attack_roll: d20 结果（若开启 d20），否则 None
	- raw_damage: 后端结算得到的 damage_dealt（用于公式展示）
	- is_hit: 依据行动设置计算的命中结果（可能为 None）
	"""
	attack_context = AttackContext()
	attack_context.attacker = current_piece
	attack_context.target = target_piece

	action = ActionSet()
	action.move = False
	action.attack = True
	action.attack_context = attack_context
	action.spell = False

	setattr(env, "current_piece", current_piece)
	captured_rolls: list[int] = []
	original_roll = getattr(env, "roll_dice", None)
	wrapped_roll = False
	if callable(original_roll):
		def _roll_proxy(n: int, sides: int):
			value = original_roll(n, sides)
			if int(n) == 1 and int(sides) == 20:
				try:
					iv = int(value)
				except Exception:
					iv = 0
				captured_rolls.append(iv)
				# 兼容“死亡检定 UI hook”：其 roll_dice_hook 依赖 _ui_in_deathcheck 才会写入 _ui_last_deathcheck_roll。
				# 但这里临时替换了 env.roll_dice，会绕过那层记录逻辑，导致右侧显示 d20=?。
				if bool(getattr(env, "_ui_in_deathcheck", False)):
					try:
						setattr(env, "_ui_last_deathcheck_roll", int(iv))
					except Exception:
						pass
			return value

		setattr(env, "roll_dice", _roll_proxy)
		wrapped_roll = True
	try:
		env.execute_player_action(action)
	finally:
		if wrapped_roll:
			setattr(env, "roll_dice", original_roll)

	attack_roll = int(captured_rolls[0]) if captured_rolls else None
	raw_damage = int(getattr(attack_context, "damage_dealt", 0))

	is_hit: bool | None = None
	# 说明：伤害可能为 0（例如基础伤害为 0），但仍可能“命中”。命中判定按行动设置公式计算。
	try:
		step_func = getattr(env, "step_modified_func", None)
		advantage_func = getattr(env, "calculate_advantage_value", None)
		if not callable(step_func):
			is_hit = None
		else:
			roll_val = int(attack_roll or 0) if enable_d20 else 0
			bonus_flat = float(hit_cfg.get("bonus_flat", 0.0) or 0.0)
			coeff_strength = float(hit_cfg.get("coeff_strength", 1.0) or 1.0)
			adv_coeff = float(hit_cfg.get("coeff_dexterity", 1.0) or 1.0)
			def_attr = hit_cfg.get("defense_modifier_attr", "dexterity")
			def_base_coeff = float(hit_cfg.get("defense_base_coeff", 1.0) or 1.0)
			def_attr_coeff = float(hit_cfg.get("defense_attr_coeff", 1.0) or 1.0)
			def_flat_bonus = float(hit_cfg.get("defense_flat_bonus", 0.0) or 0.0)
			adv_value = 0.0
			if callable(advantage_func):
				try:
					adv_value = float(advantage_func(current_piece, target_piece))
				except Exception:
					adv_value = 0.0
			if enable_d20 and roll_val == 1 and fail_on_1:
				is_hit = False
			elif enable_d20 and roll_val == 20 and crit_on_20:
				is_hit = True
			else:
				attack_score = (
					float(roll_val)
					+ bonus_flat
					+ coeff_strength * float(step_func(int(getattr(current_piece, "strength", 0))))
					+ adv_coeff * float(adv_value)
				)
				base_def = float(getattr(target_piece, "physical_resist", 0))
				attr_def = 0.0
				if def_attr not in (None, "", "none"):
					attr_def = float(step_func(int(getattr(target_piece, str(def_attr), 0))))
				defense_score = def_base_coeff * base_def + def_attr_coeff * attr_def + def_flat_bonus
				is_hit = bool(attack_score > defense_score)
	except Exception:
		is_hit = None

	return attack_roll, raw_damage, is_hit


def _perform_magic_attack(
	main_ui: Any,
	env: Any,
	current_piece: Any,
	target_piece: Any,
	*,
	enable_d20: bool,
	magic_hit_cfg: dict[str, Any],
	fail_on_1: bool,
	crit_on_20: bool,
	attack_model: dict[str, Any],
) -> tuple[int | None, int, bool | None] | None:
	"""执行“普通法术攻击”分支。

	返回 None 表示已在此函数内写入 UI 失败提示并应直接 return。
	"""
	step_func = getattr(env, "step_modified_func", None)
	if not callable(step_func):
		main_ui._set_action_feedback("行动失败：普通法术攻击缺少规则函数", False)
		return None
	advantage_func = getattr(env, "calculate_advantage_value", None)
	adv_value = 0.0
	if callable(advantage_func):
		try:
			adv_value = float(advantage_func(current_piece, target_piece))
		except Exception:
			adv_value = 0.0

	roll_val = 0
	if enable_d20 and callable(getattr(env, "roll_dice", None)):
		roll_val = int(getattr(env, "roll_dice")(1, 20))
	attack_roll = roll_val if enable_d20 else None

	bonus_flat = float(magic_hit_cfg.get("bonus_flat", 0.0) or 0.0)
	coeff_int = float(magic_hit_cfg.get("coeff_intelligence", 1.0) or 1.0)
	adv_coeff = float(magic_hit_cfg.get("coeff_advantage", 1.0) or 1.0)
	def_attr = magic_hit_cfg.get("defense_modifier_attr", None)
	def_base_coeff = float(magic_hit_cfg.get("defense_base_coeff", 1.0) or 1.0)
	def_attr_coeff = float(magic_hit_cfg.get("defense_attr_coeff", 1.0) or 1.0)
	def_flat_bonus = float(magic_hit_cfg.get("defense_flat_bonus", 0.0) or 0.0)

	is_hit: bool | None = None
	is_critical = False
	if enable_d20 and roll_val == 1 and fail_on_1:
		is_hit = False
	elif enable_d20 and roll_val == 20 and crit_on_20:
		is_hit = True
		is_critical = True
	else:
		attack_score = (
			float(roll_val if enable_d20 else 0)
			+ bonus_flat
			+ coeff_int * float(step_func(int(getattr(current_piece, "intelligence", 0))))
			+ adv_coeff * float(adv_value)
		)
		base_def = float(getattr(target_piece, "magic_resist", 0))
		attr_def = 0.0
		if def_attr not in (None, "", "none"):
			attr_def = float(step_func(int(getattr(target_piece, str(def_attr), 0))))
		defense_score = def_base_coeff * base_def + def_attr_coeff * attr_def + def_flat_bonus
		is_hit = bool(attack_score > defense_score)

	raw_damage = 0
	if is_hit:
		base_from_piece = True
		try:
			base_from_piece = bool(attack_model.get("magic_damage", {}).get("base_from_piece", True))
		except Exception:
			base_from_piece = True
		mag_dmg_cfg = attack_model.get("magic_damage", {}) if isinstance(attack_model.get("magic_damage"), dict) else {}
		base_override = mag_dmg_cfg.get("base_override", None)
		flat_bonus = float(mag_dmg_cfg.get("flat_bonus", 0.0) or 0.0)
		if base_from_piece:
			base = float(getattr(current_piece, "magic_damage", 0))
		else:
			try:
				base = float(base_override) if base_override is not None else 0.0
			except Exception:
				base = 0.0
		damage = max(0.0, base + flat_bonus)
		if is_critical:
			damage *= 2
		int_damage = int(round(damage))
		raw_damage = int_damage
		target_piece.receive_damage(int_damage, "magic")
		new_hp_tmp = int(getattr(target_piece, "health", 0))
		if new_hp_tmp < 0:
			try:
				target_piece.get_accessor().set_health_to(0)
			except Exception:
				setattr(target_piece, "health", 0)
			new_hp_tmp = 0
		if new_hp_tmp == 0:
			env.handle_death_check(target_piece)

	current_piece.get_accessor().change_action_points_by(-1)
	return attack_roll, raw_damage, is_hit


def handle_preview_attack(main_ui: Any) -> None:
	"""提交攻击行动（attack）。

	支持：
	- 物理攻击
	- 普通法术攻击
	- 定制攻击（真实伤害，绕过 AP/范围限制，用于测试）
	"""
	env = main_ui.controller.environment
	if env is None:
		main_ui._set_action_feedback("行动失败：环境未初始化", False)
		return
	_ensure_test_mock_gameplay_installed_best_effort_for_attack(env)

	current_piece = main_ui._get_runtime_current_piece(env)
	if current_piece is None:
		main_ui._set_action_feedback("行动失败：未定位到当前行动棋子", False)
		return
	# 濒死行动限制：按玩法设计配置拦截。
	if main_ui._is_runtime_piece_in_near_death(env, current_piece) and not main_ui._near_death_can_act(env):
		main_ui._set_action_feedback("行动失败：濒死状态下不能攻击或法术", False)
		main_ui.right_info_panel.append_content("\n[UI] 攻击提交失败：濒死状态下不能攻击或法术")
		return

	target_label = main_ui.action_attack_target_var.get().strip()
	target_piece = main_ui._resolve_action_target_piece(target_label)
	if target_piece is None:
		main_ui._set_action_feedback("行动失败：攻击目标无效", False)
		main_ui.right_info_panel.append_content(f"\n[UI] 攻击失败：无法识别目标 {target_label or '目标'}")
		return

	attack_type = main_ui.action_attack_type_var.get().strip() or "物理攻击"
	target_code = main_ui._get_piece_short_code(target_piece)
	old_ap = int(getattr(current_piece, "action_points", 0))
	old_hp = int(getattr(target_piece, "health", 0))

	if attack_type == "定制攻击":
		try:
			custom_damage = int(main_ui.action_custom_damage_var.get().strip())
		except Exception:
			main_ui._set_action_feedback("行动失败：真实伤害必须是整数", False)
			return
		if custom_damage <= 0:
			main_ui._set_action_feedback("行动失败：真实伤害必须大于 0", False)
			return

		target_piece.get_accessor().set_health_to(max(old_hp - custom_damage, 0))
		if int(getattr(target_piece, "health", 0)) == 0:
			env.handle_death_check(target_piece)
		main_ui._append_runtime_action_log(
			actor_code=main_ui._get_piece_short_code(current_piece),
			action_label="定制攻击",
			summary=f"对{target_code}造成{custom_damage}点真实伤害（不受AP/范围限制）",
			targets=[target_code],
			damage_by_target={target_code: custom_damage},
		)
		main_ui._append_runtime_death_and_game_over_info(target_piece, target_code)
		main_ui._set_action_feedback("行动成功", True)
		main_ui._update_cards_from_env()
		main_ui._refresh_piece_cards()
		main_ui._refresh_board_view()
		try:
			main_ui._flush_runtime_pending_messages(env)
		except Exception:
			pass
		return

	if int(getattr(current_piece, "action_points", 0)) <= 0:
		main_ui._set_action_feedback("行动失败：当前棋子行动位不足", False)
		return

	if not bool(env.is_in_attack_range(current_piece, target_piece)):
		main_ui._set_action_feedback("行动失败：本次攻击无法执行，超出攻击范围", False)
		main_ui.right_info_panel.append_content("\n[UI] 攻击失败：本次攻击无法执行，超出攻击范围")
		return

	attack_label = "物理攻击" if attack_type == "物理攻击" else "普通法术攻击"
	attack_roll: int | None
	raw_damage: int
	is_hit: bool | None
	# 读取“行动设置（本局）”快照：若未应用则使用默认。
	snapshot = _get_action_settings_snapshot(main_ui, env)
	attack_model = snapshot.get("attack_model", {}) if isinstance(snapshot, dict) else {}
	enable_d20 = bool(attack_model.get("enable_d20", True))
	hit_cfg = attack_model.get("hit", {}) if isinstance(attack_model.get("hit"), dict) else {}
	magic_hit_cfg = attack_model.get("magic_hit", {}) if isinstance(attack_model.get("magic_hit"), dict) else {}
	fail_on_1 = bool(hit_cfg.get("fail_on_1", True))
	crit_on_20 = bool(hit_cfg.get("crit_on_20", True))

	if attack_type == "物理攻击":
		attack_roll, raw_damage, is_hit = _perform_physical_attack(
			env,
			current_piece,
			target_piece,
			enable_d20=enable_d20,
			hit_cfg=hit_cfg,
			fail_on_1=fail_on_1,
			crit_on_20=crit_on_20,
		)

	else:
		magic_result = _perform_magic_attack(
			main_ui,
			env,
			current_piece,
			target_piece,
			enable_d20=enable_d20,
			magic_hit_cfg=magic_hit_cfg,
			fail_on_1=fail_on_1,
			crit_on_20=crit_on_20,
			attack_model=attack_model,
		)
		if magic_result is None:
			return
		attack_roll, raw_damage, is_hit = magic_result

	new_ap = int(getattr(current_piece, "action_points", 0))
	try:
		new_hp = int(getattr(target_piece, "health", 0))
	except Exception:
		new_hp = 0
	if new_hp < 0:
		try:
			target_piece.get_accessor().set_health_to(0)
		except Exception:
			try:
				setattr(target_piece, "health", 0)
			except Exception:
				pass
		new_hp = 0
	real_damage = max(0, old_hp - new_hp)

	# 命中与否不能用 raw_damage>0 推断（基础伤害可能为 0）。
	resolved_hit = bool(is_hit) if isinstance(is_hit, bool) else bool(raw_damage != 0 or real_damage != 0)
	if resolved_hit:
		summary = f"命中，造成{real_damage}点伤害，AP {old_ap}->{new_ap}"
	else:
		summary = f"未命中，AP {old_ap}->{new_ap}"

	main_ui._append_runtime_action_log(
		actor_code=main_ui._get_piece_short_code(current_piece),
		action_label=attack_label,
		summary=summary,
		targets=[target_code],
		damage_by_target={target_code: real_damage},
	)
	main_ui._append_attack_formula_info(
		attack_label,
		current_piece,
		target_piece,
		attack_roll=attack_roll,
		raw_damage=raw_damage,
		real_damage=real_damage,
		is_hit=resolved_hit,
	)
	main_ui._append_runtime_death_and_game_over_info(target_piece, target_code)
	main_ui._set_action_feedback("行动成功", True)
	main_ui._update_cards_from_env()
	main_ui._refresh_piece_cards()
	main_ui._refresh_board_view()
	try:
		main_ui._flush_runtime_pending_messages(env)
	except Exception:
		pass
	return
