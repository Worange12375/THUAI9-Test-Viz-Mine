"""Game data loading service.

搬迁自 main_ui.py：
- _startup_load_with_source_dialog
- _load_data_with_selected_source
- _on_click_load_data（模式选择按钮逻辑）
- _install_runtime_env_deathcheck_hook

约束：不改变 UX/行为，仅做代码搬家。
"""

from __future__ import annotations

from typing import Any, Optional

from logic.test_mock_gameplay import ensure_d20_force_installed

from services.data_loading.mode_selection_dialog_service import (
	show_mock_dataset_dialog,
	show_source_selection_dialog,
)


def startup_load_with_source_dialog(main_ui: object) -> None:
	choice = show_source_selection_dialog(main_ui, "进入测试：选择数据源")
	if choice is None:
		getattr(main_ui, "right_info_panel").append_content("\n[UI] 未选择数据源，默认使用后端玩法环境")
		setattr(main_ui, "selected_source", "runtime_custom")
	else:
		setattr(main_ui, "selected_source", choice)
	if getattr(main_ui, "selected_source") == "mock":
		selected_dataset = show_mock_dataset_dialog(main_ui, "进入测试：选择 mock 数据集")
		if selected_dataset is not None:
			setattr(main_ui, "selected_mock_dataset", selected_dataset)
		else:
			getattr(main_ui, "right_info_panel").append_content("\n[UI] 未选择 mock 数据集，保留当前未加载状态")
			return
	getattr(main_ui, "_load_data_with_selected_source")()


def on_click_load_data(main_ui: object) -> None:
	"""模式选择按钮点击事件。"""
	try:
		selected_source = show_source_selection_dialog(main_ui, "模式选择")
		if selected_source is None:
			getattr(main_ui, "right_info_panel").append_content("\n[UI] 模式选择已取消，无任何改变")
			return

		next_dataset: Optional[str] = getattr(main_ui, "selected_mock_dataset", None)
		if selected_source == "mock":
			selected_dataset = show_mock_dataset_dialog(main_ui, "模式选择 - 选择数据集")
			if selected_dataset is None:
				getattr(main_ui, "right_info_panel").append_content("\n[UI] 数据集选择已取消，无任何改变")
				return
			next_dataset = selected_dataset

		# 用户完整确认后才提交变更
		setattr(main_ui, "selected_source", selected_source)
		setattr(main_ui, "selected_mock_dataset", next_dataset)
		getattr(main_ui, "_load_data_with_selected_source")()
	except Exception as e:
		getattr(main_ui, "right_info_panel").append_content(f"\n[UI] 模式选择出错: {e}")


def on_click_mode_selection(main_ui: object) -> None:
	"""'模式选择'按钮的回调（新命名）。"""
	getattr(main_ui, "_close_replay_mode_ui")()
	getattr(main_ui, "_on_click_load_data")()


def load_data_with_selected_source(main_ui: object) -> None:
	"""按当前 selected_source / selected_mock_dataset 直接加载，不弹模式选择框。"""
	if bool(getattr(main_ui, "running", False)):
		getattr(main_ui, "_on_click_pause")()
	# 进入新对局：清空行动面板的选点/预览状态，避免重开后目标框或火球 AOE 残留。
	getattr(main_ui, "_stop_action_move_point_pick")()
	getattr(main_ui, "action_ui_mode").set("move")
	getattr(main_ui, "action_move_x_var").set("")
	getattr(main_ui, "action_move_y_var").set("")
	getattr(main_ui, "action_spell_type_var").set("")
	getattr(main_ui, "action_spell_target_var").set("")
	getattr(main_ui, "action_spell_point_x_var").set("")
	getattr(main_ui, "action_spell_point_y_var").set("")
	setattr(main_ui, "action_spell_option_map", {})
	setattr(main_ui, "action_spell_target_option_map", {})
	setattr(main_ui, "runtime_card_slots", [])
	setattr(main_ui, "mock_card_slots", [])
	setattr(main_ui, "runtime_initiative_snapshot", [])
	setattr(main_ui, "pending_actions_by_piece_id", {})
	setattr(main_ui, "runtime_cycle_done_piece_ids", set())
	setattr(main_ui, "runtime_completed_turns", 0)
	setattr(main_ui, "runtime_last_round_info_line", "")
	setattr(main_ui, "game_over_dialog_shown", False)
	setattr(main_ui, "game_over_message_shown", False)
	setattr(main_ui, "action_panel_status_label", None)
	try:
		controller = getattr(main_ui, "controller")
		controller.select_mode("manual")
		if bool(getattr(main_ui, "_is_runtime_selected_source")()):
			setattr(main_ui, "mock_map_height_overrides", {})
			controller.load_game_data(prefer_runtime=True)
			getattr(main_ui, "_attach_runtime_input")()
			env = getattr(controller, "environment", None)
			if env is not None:
				getattr(main_ui, "_initialize_runtime_environment_with_initiative_capture")(env, controller.runtime_board_file)
				try:
					setattr(env, "_ui_force_d20_flags", dict(getattr(main_ui, "system_force_d20_flags", {})))
					values: dict[str, int] = {}
					for k, v in getattr(main_ui, "system_force_d20_value_vars", {}).items():
						try:
							val = int(str(v.get()).strip())
						except Exception:
							val = 20
						if val < 1 or val > 20:
							val = 20
						values[str(k)] = int(val)
					setattr(env, "_ui_force_d20_values", values)
					ensure_d20_force_installed(env)
				except Exception:
					pass
			getattr(main_ui, "_set_runtime_board_all_walkable")()
			getattr(main_ui, "_refresh_board_view")()
			setattr(main_ui, "runtime_init_config_ready", False)
			setattr(main_ui, "runtime_piece_init_config", {})
			setattr(main_ui, "runtime_piece_slot_binding", {})
			getattr(main_ui, "_prepare_runtime_piece_init_defaults")()
			getattr(main_ui, "_on_click_attribute_settings")(force_runtime_init=True)
			if not bool(getattr(main_ui, "runtime_init_config_ready", False)):
				getattr(main_ui, "right_info_panel").append_content("\n[UI] 后端模式初始化配置未完成，取消加载")
				return

			if env is not None:
				getattr(main_ui, "_initialize_runtime_environment_with_initiative_capture")(env, controller.runtime_board_file)
				getattr(main_ui, "_set_runtime_board_all_walkable")()
				getattr(main_ui, "_apply_runtime_piece_config_to_environment")()
				getattr(main_ui, "_initialize_runtime_card_slots")()
				install_runtime_env_deathcheck_hook(main_ui, env)
				# 跨局保持：新对局加载后自动重应用“玩法设计”中已应用过的配置。
				getattr(main_ui, "_reapply_persistent_design_settings_to_runtime_environment")(env)
				getattr(main_ui, "_check_and_announce_runtime_game_over")(env, show_dialog=True)
				getattr(main_ui, "_show_initiative_summary_popup")()
			setattr(main_ui, "loaded", True)
			getattr(main_ui, "left_board_panel").reset_board_state()
			getattr(main_ui, "_initialize_mock_positions")()
			getattr(main_ui, "_refresh_piece_cards")()
			getattr(main_ui, "root").update_idletasks()
			getattr(main_ui, "_refresh_board_view")()
			getattr(main_ui, "_sync_replay_round_var")()
			mode_desc = "后端模式（职业）" if bool(getattr(main_ui, "_is_profession_mode")()) else "后端模式（自定义）"
			getattr(main_ui, "right_info_panel").append_content(f"\n[UI] 已加载{mode_desc}")
			return

		if not getattr(main_ui, "selected_mock_dataset", None):
			getattr(main_ui, "right_info_panel").append_content("\n[UI] 缺少 mock 数据集，无法加载")
			return
		setattr(main_ui, "mock_map_height_overrides", {})
		controller.load_game_data(prefer_runtime=False, mock_dataset=getattr(main_ui, "selected_mock_dataset"))
		env = getattr(controller, "environment", None)
		if env is not None:
			try:
				setattr(env, "_ui_force_d20_flags", dict(getattr(main_ui, "system_force_d20_flags", {})))
				values: dict[str, int] = {}
				for k, v in getattr(main_ui, "system_force_d20_value_vars", {}).items():
					try:
						val = int(str(v.get()).strip())
					except Exception:
						val = 20
					if val < 1 or val > 20:
						val = 20
					values[str(k)] = int(val)
				setattr(env, "_ui_force_d20_values", values)
				ensure_d20_force_installed(env)
			except Exception:
				pass
		setattr(main_ui, "runtime_card_slots", [])
		setattr(main_ui, "mock_card_slots", [])
		setattr(main_ui, "runtime_piece_slot_binding", {})
		setattr(main_ui, "loaded", True)
		getattr(main_ui, "left_board_panel").reset_board_state()
		getattr(main_ui, "_initialize_mock_positions")()
		getattr(main_ui, "_initialize_mock_card_slots")()
		getattr(main_ui, "_refresh_piece_cards")()
		getattr(main_ui, "_refresh_board_view")()
		getattr(main_ui, "_sync_replay_round_var")()
		getattr(main_ui, "right_info_panel").append_content(
			f"\n[UI] 已加载 mock 模式: {getattr(main_ui, 'selected_mock_dataset')}"
		)
	except Exception as e:
		getattr(main_ui, "right_info_panel").append_content(f"\n[UI] 加载失败: {e}")


def install_runtime_env_deathcheck_hook(main_ui: object, env: Any) -> None:
	"""在不改 env.py 的前提下，为死亡检定增加 UI 可见的提示与掷骰结果。

	实现方式：运行时 monkeypatch env.roll_dice 与 env.handle_death_check，
	仅记录/展示信息，不改变任何判定分支。
	"""
	if env is None:
		return
	if bool(getattr(env, "_ui_deathcheck_hook_installed", False)):
		return

	setattr(env, "_ui_deathcheck_hook_installed", True)
	setattr(env, "_ui_in_deathcheck", False)
	setattr(env, "_ui_last_deathcheck_roll", None)

	orig_roll_dice = getattr(env, "roll_dice", None)
	orig_handle = getattr(env, "handle_death_check", None)
	if not callable(orig_roll_dice) or not callable(orig_handle):
		return

	# 防止与 ForceD20 hook 形成递归环
	try:
		if bool(getattr(orig_roll_dice, "_ui_force_d20_marker", False)):
			force_base = getattr(env, "_ui_orig_roll_dice_force_d20", None)
			if callable(force_base) and force_base is not orig_roll_dice:
				orig_roll_dice = force_base
			else:
				force_base2 = getattr(orig_roll_dice, "_ui_force_d20_orig", None)
				if callable(force_base2) and force_base2 is not orig_roll_dice:
					orig_roll_dice = force_base2
	except Exception:
		pass

	# 统一入口：UI hook 负责记录/展示；实际判定逻辑通过 _ui_handle_death_check_impl 注入。
	try:
		setattr(env, "_ui_handle_death_check_backend", orig_handle)
		impl = getattr(env, "_ui_handle_death_check_impl", None)
		if not callable(impl):
			setattr(env, "_ui_handle_death_check_impl", orig_handle)
	except Exception:
		pass

	def roll_dice_hook(n: int, sides: int):
		result = orig_roll_dice(n, sides)
		if bool(getattr(env, "_ui_in_deathcheck", False)) and int(n) == 1 and int(sides) == 20:
			try:
				setattr(env, "_ui_last_deathcheck_roll", int(result))
			except Exception:
				setattr(env, "_ui_last_deathcheck_roll", result)
		return result

	# 供其它 hook（如 ForceD20）识别/解包，避免形成递归环。
	try:
		setattr(roll_dice_hook, "_ui_deathcheck_roll_marker", True)
		setattr(roll_dice_hook, "_ui_deathcheck_roll_orig", orig_roll_dice)
	except Exception:
		pass

	def _queue_runtime_message(message: str) -> None:
		try:
			pending = getattr(env, "_ui_pending_info_messages", None)
			if not isinstance(pending, list):
				pending = []
				setattr(env, "_ui_pending_info_messages", pending)
			pending.append(str(message))
		except Exception:
			return

	def handle_death_check_hook(target: Any):
		setattr(env, "_ui_in_deathcheck", True)
		setattr(env, "_ui_last_deathcheck_roll", None)
		try:
			impl = getattr(env, "_ui_handle_death_check_impl", None)
			if not callable(impl):
				impl = orig_handle
			return impl(target)
		finally:
			setattr(env, "_ui_in_deathcheck", False)
			roll_value = getattr(env, "_ui_last_deathcheck_roll", None)
			piece_code = getattr(main_ui, "_get_piece_short_code")(target)
			if roll_value is None:
				# 某些路径（例如法术/陷阱结算）可能在同一次动作内重复调用死亡检定，
				# 或由后端逻辑提前 return 导致没有掷 d20。
				# 这里避免输出“d20=?”这种误导性提示。
				_queue_runtime_message(f"[死亡检定] {piece_code} 触发死亡检定")
				return
			try:
				roll_int = int(roll_value)
			except Exception:
				roll_int = None

			if roll_int == 20:
				try:
					getattr(main_ui, "_mark_runtime_piece_angel")(env, target, seconds=10.0)
				except Exception:
					pass
				_queue_runtime_message(f"[死亡检定] {piece_code} 掷 d20=20：恢复至 1HP")
			else:
				near_cfg = getattr(env, "_ui_near_death_config", None)
				near_enabled = bool(near_cfg.get("enabled", False)) if isinstance(near_cfg, dict) else False
				extra = "（当前实现：非20直接死亡）" if (roll_int is not None and not near_enabled) else ""
				_queue_runtime_message(f"[死亡检定] {piece_code} 掷 d20={roll_value}{extra}")

	setattr(env, "roll_dice", roll_dice_hook)
	setattr(env, "handle_death_check", handle_death_check_hook)
	# 注意：此处覆盖了 env.roll_dice；若系统设置启用了“投掷必定命中”，需要把覆盖再包一层。
	try:
		ensure_d20_force_installed(env)
	except Exception:
		pass
