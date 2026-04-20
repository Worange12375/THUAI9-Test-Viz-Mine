"""主界面入口。

该文件只负责“界面装配”：
1. 创建主窗口
2. 按 2:1 划分左右区域
3. 调用 components.py 中的可复用组件完成基础布局
"""

from __future__ import annotations

import time
import contextlib
import tkinter as tk
from tkinter import ttk
from typing import Any, Optional
import numpy as np

import os
import sys
import copy
from types import SimpleNamespace

# 避免运行 UI 时生成/更新 __pycache__/*.pyc（本仓库历史上曾跟踪过 .pyc，容易造成 git 噪音）。
sys.dont_write_bytecode = True

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from env import ActionSet, Area, AttackContext, Environment, PieceArg, Player, Point, SpellContext, SpellFactory
from logic.controller import Controller
from logic.test_mock_gameplay import ensure_d20_force_installed, ensure_test_mock_gameplay_installed
from core.events import EventType

from services.runtime.runtime_hooks_service import (
	apply_near_death_config as _apply_near_death_config_service,
	apply_spell_pool_config as _apply_spell_pool_config_service,
	apply_talent_gradient_config as _apply_talent_gradient_config_service,
	reapply_persistent_design_settings as _reapply_persistent_design_settings_service,
)

from services.runtime.runtime_monitor_service import (
	check_and_announce_runtime_game_over as _check_and_announce_runtime_game_over_service,
	flush_runtime_pending_messages as _flush_runtime_pending_messages_service,
	get_runtime_near_death_cfg as _get_runtime_near_death_cfg_service,
	is_runtime_piece_in_near_death as _is_runtime_piece_in_near_death_service,
	is_piece_alive_by_hp as _is_piece_alive_by_hp_service,
	mark_runtime_piece_angel as _mark_runtime_piece_angel_service,
	near_death_can_act as _near_death_can_act_service,
	near_death_can_move as _near_death_can_move_service,
	on_event_game_loaded as _on_event_game_loaded_service,
	on_event_game_over as _on_event_game_over_service,
	on_event_round_finished as _on_event_round_finished_service,
	on_event_round_started as _on_event_round_started_service,
	schedule_runtime_angel_refresh as _schedule_runtime_angel_refresh_service,
)

from services.runtime.runtime_init_service import (
	apply_runtime_piece_config_to_environment as _apply_runtime_piece_config_to_environment_service,
	attach_runtime_input as _attach_runtime_input_service,
	auto_init_handler as _auto_init_handler_service,
	get_runtime_current_piece as _get_runtime_current_piece_service,
	initialize_runtime_environment_with_initiative_capture as _initialize_runtime_environment_with_initiative_capture_service,
	noop_action_handler as _noop_action_handler_service,
	prepare_runtime_piece_init_defaults as _prepare_runtime_piece_init_defaults_service,
	queue_action_for_current_piece as _queue_action_for_current_piece_service,
	set_runtime_board_all_walkable as _set_runtime_board_all_walkable_service,
	ui_action_handler as _ui_action_handler_service,
)

from services.actions.action_submit_service import handle_preview_submit_action as _handle_preview_submit_action_service
from services.actions.action_move_service import build_move_action_from_ui as _build_move_action_from_ui_service
from services.actions.action_panel_service import (
	append_attack_formula_info as _append_attack_formula_info_service,
	append_runtime_action_log as _append_runtime_action_log_service,
	append_runtime_death_and_game_over_info as _append_runtime_death_and_game_over_info_service,
	append_runtime_turn_round_status as _append_runtime_turn_round_status_service,
	apply_custom_teleport_spell as _apply_custom_teleport_spell_service,
	begin_action_move_point_pick as _begin_action_move_point_pick_service,
	begin_action_spell_point_pick as _begin_action_spell_point_pick_service,
	begin_action_spell_target_pick as _begin_action_spell_target_pick_service,
	build_runtime_turn_round_status as _build_runtime_turn_round_status_service,
	clear_action_feedback as _clear_action_feedback_service,
	collapse_action_detail as _collapse_action_detail_service,
	collect_action_target_options as _collect_action_target_options_service,
	collect_area_spell_targets as _collect_area_spell_targets_service,
	collect_available_spell_options as _collect_available_spell_options_service,
	collect_spell_target_options as _collect_spell_target_options_service,
	format_action_target_option as _format_action_target_option_service,
	get_current_actor_text as _get_current_actor_text_service,
	get_piece_short_code as _get_piece_short_code_service,
	handle_death_check_if_possible as _handle_death_check_if_possible_service,
	is_teleport_spell as _is_teleport_spell_service,
	is_trap_spell as _is_trap_spell_service,
	on_action_move_pick_overlay_click as _on_action_move_pick_overlay_click_service,
	on_click_piece_action as _on_click_piece_action_service,
	on_finish_current_piece_turn as _on_finish_current_piece_turn_service,
	on_open_custom_attack_advanced_settings as _on_open_custom_attack_advanced_settings_service,
	place_runtime_trap_spell as _place_runtime_trap_spell_service,
	pop_runtime_trap_at_xy as _pop_runtime_trap_at_xy_service,
	rerender_attack_mode_if_needed as _rerender_attack_mode_if_needed_service,
	rerender_spell_mode_if_needed as _rerender_spell_mode_if_needed_service,
	refresh_custom_attack_preview as _refresh_custom_attack_preview_service,
	render_action_mode_body as _render_action_mode_body_service,
	resolve_action_target_piece as _resolve_action_target_piece_service,
	resolve_piece_at_board_xy as _resolve_piece_at_board_xy_service,
	resolve_selected_spell as _resolve_selected_spell_service,
	resolve_spell_target_piece as _resolve_spell_target_piece_service,
	set_action_feedback as _set_action_feedback_service,
	spell_display_name as _spell_display_name_service,
	spell_effect_key as _spell_effect_key_service,
	stop_action_move_point_pick as _stop_action_move_point_pick_service,
	switch_action_mode as _switch_action_mode_service,
	tick_runtime_traps as _tick_runtime_traps_service,
	try_trigger_runtime_trap_on_piece as _try_trigger_runtime_trap_on_piece_service,
)
from services.attribute_settings.attribute_settings_window_service import (
	open_attribute_settings_window as _open_attribute_settings_window_service,
)

from services.attribute_settings.attribute_derived_stats_service import (
	armor_id_to_armor_label as _armor_id_to_armor_label_service,
	armor_label_to_armor_id as _armor_label_to_armor_id_service,
	compute_custom_mode_stats_via_backend as _compute_custom_mode_stats_via_backend_service,
	compute_equipment_only_stats as _compute_equipment_only_stats_service,
	compute_profession_mode_stats as _compute_profession_mode_stats_service,
	custom_init_hp_hint_value as _custom_init_hp_hint_value_service,
	get_talent_total_cap as _get_talent_total_cap_service,
	is_profession_slot_active_from_cfg as _is_profession_slot_active_from_cfg_service,
	is_profession_slot_active_from_vars as _is_profession_slot_active_from_vars_service,
	normalize_weapon_label as _normalize_weapon_label_service,
	one_click_fill_custom_init as _one_click_fill_custom_init_service,
	parse_talent_int as _parse_talent_int_service,
	refresh_custom_init_hp_hint as _refresh_custom_init_hp_hint_service,
	sync_profession_equipment as _sync_profession_equipment_service,
	update_custom_mode_equipment_presets as _update_custom_mode_equipment_presets_service,
	update_equipment_dependent_fields as _update_equipment_dependent_fields_service,
	update_profession_display_and_presets as _update_profession_display_and_presets_service,
	weapon_id_to_piece_type as _weapon_id_to_piece_type_service,
	weapon_id_to_profession_display as _weapon_id_to_profession_display_service,
	weapon_id_to_profession_label_simple as _weapon_id_to_profession_label_simple_service,
	weapon_id_to_weapon_label as _weapon_id_to_weapon_label_service,
	weapon_label_to_weapon_id as _weapon_label_to_weapon_id_service,
)

from services.design.design_attribute_page_service import (
	apply_design_attribute_talent_gradients as _apply_design_attribute_talent_gradients_service,
	apply_design_attribute_talent_gradient_snapshot_to_vars as _apply_design_attribute_talent_gradient_snapshot_to_vars_service,
	build_design_attribute_page as _build_design_attribute_page_service,
	clear_design_attribute_gradient_error_highlight as _clear_design_attribute_gradient_error_highlight_service,
	ensure_one_talent_gradient_initialized as _ensure_one_talent_gradient_initialized_service,
	rebuild_talent_gradient_rows as _rebuild_talent_gradient_rows_service,
	reset_design_attribute_talent_gradients as _reset_design_attribute_talent_gradients_service,
	reset_one_talent_gradient_to_default as _reset_one_talent_gradient_to_default_service,
)
from services.design.design_global_page_service import (
	apply_design_global_near_death_settings as _apply_design_global_near_death_settings_service,
	build_design_global_page as _build_design_global_page_service,
)
from services.design.design_spell_pool_page_service import (
	build_design_spell_pool_page as _build_design_spell_pool_page_service,
)

from services.design.design_page_service import (
	build_system_settings_design_page as _build_system_settings_design_page_service,
	parse_int_or_none as _parse_int_or_none_service,
)

from services.system_settings.system_general_page_service import (
	apply_system_general_settings as _apply_system_general_settings_service,
	apply_system_general_settings_snapshot_to_vars as _apply_system_general_settings_snapshot_to_vars_service,
	build_system_settings_general_page as _build_system_settings_general_page_service,
	collect_system_general_settings_snapshot_from_vars as _collect_system_general_settings_snapshot_from_vars_service,
)

from services.system_settings.system_settings_dirty_service import (
	discard_unapplied_system_settings_changes as _discard_unapplied_system_settings_changes_service,
	has_any_system_settings_dirty as _has_any_system_settings_dirty_service,
	set_system_settings_dirty as _set_system_settings_dirty_service,
	suppress_system_settings_dirty as _suppress_system_settings_dirty_service,
	suppress_system_settings_dirty_until_idle as _suppress_system_settings_dirty_until_idle_service,
)
from services.system_settings.system_settings_window_service import (
	open_system_settings_window as _open_system_settings_window_service,
	switch_system_settings_page as _switch_system_settings_page_service,
)
from services.system_settings.system_text_pages_service import (
	build_system_settings_dev_page as _build_system_settings_dev_page_service,
	build_system_settings_tutorial_page as _build_system_settings_tutorial_page_service,
)

from services.dialogs.popup_service import (
	center_popup_window as _center_popup_window_service,
	show_confirm_dialog as _show_confirm_dialog_service,
	show_game_over_reset_dialog as _show_game_over_reset_dialog_service,
	show_initiative_summary_popup as _show_initiative_summary_popup_service,
	show_notice_popup as _show_notice_popup_service,
)

from services.board.board_view_service import (
	build_runtime_trap_markers as _build_runtime_trap_markers_for_board_service,
	build_spell_aoe_overlay as _build_spell_aoe_overlay_for_board_service,
	build_target_markers_for_board as _build_target_markers_for_board_service,
	get_move_target_highlight as _get_move_target_highlight_for_board_service,
	refresh_board_view as _refresh_board_view_service,
	spell_preview_color as _spell_preview_color_for_board_service,
)

from services.board.board_data_service import (
	extract_mock_visual_rows as _extract_mock_visual_rows_service,
	extract_runtime_map_rows as _extract_runtime_map_rows_service,
	extract_runtime_pieces as _extract_runtime_pieces_service,
)

from services.cards.piece_cards_service import (
	build_team_piece_view_data_mock as _build_team_piece_view_data_mock_service,
	build_team_piece_view_data_runtime as _build_team_piece_view_data_runtime_service,
	get_mock_last_actor_id as _get_mock_last_actor_id_service,
	get_piece_action_status_text as _get_piece_action_status_text_service,
	initialize_mock_card_slots as _initialize_mock_card_slots_service,
	initialize_runtime_card_slots as _initialize_runtime_card_slots_service,
	refresh_piece_action_status_line as _refresh_piece_action_status_line_service,
	refresh_piece_cards as _refresh_piece_cards_service,
	slot_code as _slot_code_service,
	update_cards_from_env as _update_cards_from_env_service,
)

from services.replay.replay_service import (
	append_mock_round_details as _append_mock_round_details_service,
	append_round_details_after_step as _append_round_details_after_step_service,
	append_runtime_round_details as _append_runtime_round_details_service,
	apply_replay_speed_from_input as _apply_replay_speed_from_input_service,
	apply_round_for_replay as _apply_round_for_replay_service,
	build_mock_pieces_for_current_round as _build_mock_pieces_for_current_round_service,
	close_replay_mode_ui as _close_replay_mode_ui_service,
	event_loop_tick as _event_loop_tick_service,
	extract_mock_round_stats_health as _extract_mock_round_stats_health_service,
	camp_to_team as _camp_to_team_service,
	format_team_piece_name as _format_team_piece_name_service,
	get_mock_total_rounds as _get_mock_total_rounds_service,
	initialize_mock_positions as _initialize_mock_positions_service,
	on_click_pause as _on_click_pause_service,
	on_click_replay_mode as _on_click_replay_mode_service,
	on_click_start as _on_click_start_service,
	on_click_step as _on_click_step_service,
	on_replay_back as _on_replay_back_service,
	on_replay_forward as _on_replay_forward_service,
	on_replay_jump_to_round as _on_replay_jump_to_round_service,
	on_replay_restart as _on_replay_restart_service,
	on_replay_toggle_play_pause as _on_replay_toggle_play_pause_service,
	rebuild_mock_state_to_round as _rebuild_mock_state_to_round_service,
	run_single_round_once as _run_single_round_once_service,
	show_interval_range_warning as _show_interval_range_warning_service,
	snapshot_runtime_piece_states as _snapshot_runtime_piece_states_service,
	sync_replay_round_var as _sync_replay_round_var_service,
	update_replay_play_pause_button_text as _update_replay_play_pause_button_text_service,
)

from services.data_loading.game_data_loading_service import (
	install_runtime_env_deathcheck_hook as _install_runtime_env_deathcheck_hook_service,
	load_data_with_selected_source as _load_data_with_selected_source_service,
	on_click_load_data as _on_click_load_data_service,
	on_click_mode_selection as _on_click_mode_selection_service,
	startup_load_with_source_dialog as _startup_load_with_source_dialog_service,
)
from services.data_loading.mode_selection_dialog_service import (
	show_mock_dataset_dialog as _show_mock_dataset_dialog_service,
	show_source_selection_dialog as _show_source_selection_dialog_service,
)
from services.data_loading.source_mode_utils_service import (
	is_profession_mode as _is_profession_mode_service,
	is_runtime_selected_source as _is_runtime_selected_source_service,
	normalize_selected_source_value as _normalize_selected_source_value_service,
)
from services.data_loading.reset_game_service import on_click_reset as _on_click_reset_service

from services.attribute_settings.attribute_settings_page_switch_service import (
	switch_attribute_settings_page as _switch_attribute_settings_page_service,
)
from services.attribute_settings.attribute_settings_action_page_service import (
	apply_action_attribute_changes as _apply_action_attribute_changes_service,
	apply_action_settings_to_runtime_environment as _apply_action_settings_to_runtime_environment_service,
	build_attribute_action_page as _build_attribute_action_page_service,
	collect_action_settings_snapshot_from_vars as _collect_action_settings_snapshot_from_vars_service,
	default_action_settings_snapshot as _default_action_settings_snapshot_service,
	ensure_action_settings_initialized as _ensure_action_settings_initialized_service,
	reset_action_attribute_to_defaults as _reset_action_attribute_to_defaults_service,
	show_action_apply_feedback as _show_action_apply_feedback_service,
	show_action_warning_feedback as _show_action_warning_feedback_service,
	sync_action_settings_vars_from_snapshot as _sync_action_settings_vars_from_snapshot_service,
)
from services.attribute_settings.attribute_settings_map_page_service import (
	apply_map_height_change as _apply_map_height_change_service,
	begin_map_point_pick as _begin_map_point_pick_service,
	build_attribute_map_page as _build_attribute_map_page_service,
	get_current_map_height as _get_current_map_height_service,
	is_map_edit_available as _is_map_edit_available_service,
	map_height_to_color as _map_height_to_color_service,
	on_map_pick_overlay_click as _on_map_pick_overlay_click_service,
	restore_map_attribute_page_after_pick as _restore_map_attribute_page_after_pick_service,
	show_map_apply_feedback as _show_map_apply_feedback_service,
	show_map_pick_invalid_popup as _show_map_pick_invalid_popup_service,
	stop_map_point_pick as _stop_map_point_pick_service,
	update_map_height_preview as _update_map_height_preview_service,
)

from services.attribute_settings.attribute_settings_piece_page_service import (
	apply_piece_attribute_changes as _apply_piece_attribute_changes_service,
	build_attribute_piece_page as _build_attribute_piece_page_service,
)

from services.attribute_settings.attribute_piece_utils_service import (
	capture_runtime_piece_slot_binding_from_init_config as _capture_runtime_piece_slot_binding_from_init_config_service,
	clamp_piece_position as _clamp_piece_position_service,
	clear_attribute_error_highlight as _clear_attribute_error_highlight_service,
	coerce_piece_list as _coerce_piece_list_service,
	get_piece_row_values as _get_piece_row_values_service,
	is_attribute_slot_enabled as _is_attribute_slot_enabled_service,
	is_walkable_for_piece as _is_walkable_for_piece_service,
	on_attribute_var_changed as _on_attribute_var_changed_service,
	mark_attribute_field_error as _mark_attribute_field_error_service,
	mark_hp_placeholder_error as _mark_hp_placeholder_error_service,
	mock_piece_slot_map as _mock_piece_slot_map_service,
	normalize_piece_value as _normalize_piece_value_service,
	piece_attr_range as _piece_attr_range_service,
	piece_slot_keys as _piece_slot_keys_service,
	runtime_border_line as _runtime_border_line_service,
	runtime_init_incomplete_message as _runtime_init_incomplete_message_service,
	runtime_piece_slot_map as _runtime_piece_slot_map_service,
	safe_float as _safe_float_service,
	safe_int as _safe_int_service,
	show_attribute_apply_feedback as _show_attribute_apply_feedback_service,
	show_attribute_warning_feedback as _show_attribute_warning_feedback_service,
)

from services.layout.main_layout_service import (
	build_left_side as _build_left_side_service,
	build_right_side as _build_right_side_service,
	on_right_composite_panel_initialize as _on_right_composite_panel_initialize_service,
)

from services.layout.main_ui_bootstrap_service import (
	bootstrap_main_ui as _bootstrap_main_ui_service,
	on_click_initialize as _on_click_initialize_service,
)

from components import (
	ButtonPanel,
	ChessboardPanel,
	InfoPanel,
	PieceSquareCard,
	PlayerSummaryCard,
	RightTopCompositePanel,
)


class MainUI:
	"""测试后端逻辑用的基础界面。

	当前阶段目标：
	- 完成窗口基础骨架
	- 预留左上信息展示区域
	- 预留右侧按键区与信息展示区
	"""

	def __init__(self, root: tk.Tk) -> None:
		_bootstrap_main_ui_service(self, root)

	def _normalize_selected_source_value(self, value: str) -> str:
		"""兼容旧值：将 runtime 归一到 runtime_custom。"""
		return _normalize_selected_source_value_service(value)

	def _is_runtime_selected_source(self) -> bool:
		return _is_runtime_selected_source_service(self.selected_source)

	def _is_profession_mode(self) -> bool:
		return _is_profession_mode_service(self.selected_source)

	def _weapon_label_to_weapon_id(self, weapon_label: str) -> int:
		return _weapon_label_to_weapon_id_service(self, weapon_label)

	def _armor_label_to_armor_id(self, armor_label: str) -> int:
		return _armor_label_to_armor_id_service(self, armor_label)

	def _weapon_id_to_weapon_label(self, weapon_id: int) -> str:
		return _weapon_id_to_weapon_label_service(self, weapon_id)

	def _armor_id_to_armor_label(self, armor_id: int) -> str:
		return _armor_id_to_armor_label_service(self, armor_id)

	def _normalize_weapon_label(self, weapon_label: str) -> str:
		return _normalize_weapon_label_service(self, weapon_label)

	def _weapon_id_to_profession_display(self, weapon_id: int) -> str:
		return _weapon_id_to_profession_display_service(self, weapon_id)

	def _weapon_id_to_profession_label_simple(self, weapon_id: int) -> str:
		return _weapon_id_to_profession_label_simple_service(self, weapon_id)

	def _get_talent_total_cap(self) -> int:
		return _get_talent_total_cap_service(self)

	def _parse_talent_int(self, raw: Any) -> int | None:
		return _parse_talent_int_service(self, raw)

	def _is_profession_slot_active_from_vars(self, vars_dict: dict[str, tk.StringVar] | None) -> bool:
		return _is_profession_slot_active_from_vars_service(self, vars_dict)

	def _is_profession_slot_active_from_cfg(self, cfg: dict[str, Any] | None) -> bool:
		return _is_profession_slot_active_from_cfg_service(self, cfg)

	def _compute_equipment_only_stats(
		self,
		*,
		weapon_id: int,
		armor_id: int,
		strength: int | None = None,
		dexterity: int | None = None,
	) -> dict[str, str]:
		return _compute_equipment_only_stats_service(
			self,
			weapon_id=weapon_id,
			armor_id=armor_id,
			strength=strength,
			dexterity=dexterity,
		)

	def _update_custom_mode_equipment_presets(self, slot_key: str, *, update_stats: bool) -> None:
		_update_custom_mode_equipment_presets_service(self, slot_key, update_stats=update_stats)

	def _update_equipment_dependent_fields(self, slot_key: str) -> None:
		_update_equipment_dependent_fields_service(self, slot_key)

	def _compute_custom_mode_stats_via_backend(
		self,
		*,
		strength: int,
		dexterity: int,
		intelligence: int,
		weapon_label: str,
		armor_label: str,
	) -> dict[str, str]:
		return _compute_custom_mode_stats_via_backend_service(
			self,
			strength=strength,
			dexterity=dexterity,
			intelligence=intelligence,
			weapon_label=weapon_label,
			armor_label=armor_label,
		)

	def _custom_init_hp_hint_value(self, slot_key: str) -> int:
		return _custom_init_hp_hint_value_service(self, slot_key)

	def _refresh_custom_init_hp_hint(self, slot_key: str) -> None:
		_refresh_custom_init_hp_hint_service(self, slot_key)

	def _one_click_fill_custom_init(self) -> None:
		_one_click_fill_custom_init_service(self)

	def _weapon_id_to_piece_type(self, weapon_id: int) -> str:
		return _weapon_id_to_piece_type_service(self, weapon_id)

	def _compute_profession_mode_stats(
		self,
		*,
		strength: int,
		dexterity: int,
		intelligence: int,
		weapon_id: int,
		armor_id: int,
	) -> dict[str, str]:
		return _compute_profession_mode_stats_service(
			self,
			strength=strength,
			dexterity=dexterity,
			intelligence=intelligence,
			weapon_id=weapon_id,
			armor_id=armor_id,
		)

	def _update_profession_display_and_presets(self, slot_key: str) -> None:
		_update_profession_display_and_presets_service(self, slot_key)

	def _sync_profession_equipment(self, slot_key: str, changed_field: str) -> None:
		_sync_profession_equipment_service(self, slot_key, changed_field)

	def _show_source_selection_dialog(self, title: str = "选择数据源") -> Optional[str]:
		"""弹窗选择数据源：后端玩法环境或 mock 回放。"""
		return _show_source_selection_dialog_service(self, title=title)

	def _show_mock_dataset_dialog(self, title: str = "选择 mock 数据集") -> Optional[str]:
		"""弹窗选择 mock 数据集：用于回放不同测试样例。"""
		return _show_mock_dataset_dialog_service(self, title=title)

	def _startup_load_with_source_dialog(self) -> None:
		_startup_load_with_source_dialog_service(self)

	def _load_data_with_selected_source(self) -> None:
		"""按当前 selected_source / selected_mock_dataset 直接加载，不弹模式选择框。"""
		_load_data_with_selected_source_service(self)

	def _install_runtime_env_deathcheck_hook(self, env: Any) -> None:
		_install_runtime_env_deathcheck_hook_service(self, env)

	def _is_piece_alive_by_hp(self, piece: Any) -> bool:
		return _is_piece_alive_by_hp_service(self, piece)

	def _flush_runtime_pending_messages(self, env: Any) -> None:
		_flush_runtime_pending_messages_service(self, env)

	def _mark_runtime_piece_angel(self, env: Any, piece: Any, *, seconds: float) -> None:
		_mark_runtime_piece_angel_service(self, env, piece, seconds=seconds)

	def _schedule_runtime_angel_refresh(self, env: Any) -> None:
		_schedule_runtime_angel_refresh_service(self, env)

	def _check_and_announce_runtime_game_over(self, env: Any, *, show_dialog: bool) -> None:
		_check_and_announce_runtime_game_over_service(self, env, show_dialog=show_dialog)

	def _prepare_runtime_piece_init_defaults(self) -> None:
		"""准备后端模式初始化阶段的 6 槽位默认配置。"""
		_prepare_runtime_piece_init_defaults_service(self)

	def _set_runtime_board_all_walkable(self) -> None:
		"""后端模式初始化前，将地图默认设置为全盘可走。"""
		_set_runtime_board_all_walkable_service(self)

	def _clear_attribute_error_highlight(self) -> None:
		_clear_attribute_error_highlight_service(self)

	def _mark_hp_placeholder_error(self, slot_key: str) -> None:
		_mark_hp_placeholder_error_service(self, slot_key)

	def _mark_attribute_field_error(self, slot_key: str, field: str) -> None:
		_mark_attribute_field_error_service(self, slot_key, field)

	def _is_attribute_slot_enabled(self, slot_key: str) -> bool:
		return _is_attribute_slot_enabled_service(self, slot_key)

	def _on_attribute_var_changed(self, slot_key: str, field: str) -> None:
		_on_attribute_var_changed_service(self, slot_key, field)

	def _apply_runtime_piece_config_to_environment(self) -> None:
		"""将初始化配置应用到已初始化的后端环境。"""
		_apply_runtime_piece_config_to_environment_service(self)

	def _auto_init_handler(self, init_message: Any):
		return _auto_init_handler_service(self, init_message)

	def _noop_action_handler(self, _env: Any) -> ActionSet:
		return _noop_action_handler_service(_env)

	def _get_runtime_current_piece(self, env: Any) -> Any:
		return _get_runtime_current_piece_service(self, env)

	def _ui_action_handler(self, env: Any) -> ActionSet:
		return _ui_action_handler_service(self, env)

	def _queue_action_for_current_piece(self, action: ActionSet) -> bool:
		return _queue_action_for_current_piece_service(self, action)

	def _build_move_action_from_ui(self) -> tuple[Optional[ActionSet], str]:
		"""将移动 UI 输入转换成 ActionSet，并做最小合法性校验。"""
		return _build_move_action_from_ui_service(self)

	def _attach_runtime_input(self) -> None:
		_attach_runtime_input_service(self)

	def _initialize_runtime_environment_with_initiative_capture(self, env: Any, board_file: Optional[str]) -> None:
		_initialize_runtime_environment_with_initiative_capture_service(self, env, board_file)

	def _update_cards_from_env(self) -> None:
		_update_cards_from_env_service(self)

	def _get_piece_action_status_text(self) -> str:
		return _get_piece_action_status_text_service(self)

	def _refresh_piece_action_status_line(self) -> None:
		_refresh_piece_action_status_line_service(self)

	def _build_team_piece_view_data_runtime(self) -> dict[int, list[dict[str, Any]]]:
		return _build_team_piece_view_data_runtime_service(self)

	def _get_mock_last_actor_id(self) -> int:
		return _get_mock_last_actor_id_service(self)

	def _build_team_piece_view_data_mock(self) -> dict[int, list[dict[str, Any]]]:
		return _build_team_piece_view_data_mock_service(self)

	def _slot_code(self, team: int, piece_no: int) -> str:
		return _slot_code_service(team, piece_no)

	def _initialize_runtime_card_slots(self) -> None:
		"""按开局行动队列固定 6 个卡槽顺序；缺失棋子补到末尾。"""
		_initialize_runtime_card_slots_service(self)

	def _initialize_mock_card_slots(self) -> None:
		"""mock 模式下固定 6 卡槽顺序：按回放首次行动顺序，缺失棋子补尾。"""
		_initialize_mock_card_slots_service(self)

	def _refresh_piece_cards(self) -> None:
		_refresh_piece_cards_service(self)

	def _camp_to_team(self, camp: str, players: dict[str, Any]) -> int:
		return _camp_to_team_service(camp, players)

	def _extract_runtime_map_rows(self) -> list[list[int]]:
		return _extract_runtime_map_rows_service(self)

	def _extract_mock_visual_rows(self) -> list[list[int]]:
		return _extract_mock_visual_rows_service(self)

	def _extract_runtime_pieces(self) -> list[dict[str, Any]]:
		return _extract_runtime_pieces_service(self)

	def _initialize_mock_positions(self) -> None:
		_initialize_mock_positions_service(self)

	def _format_team_piece_name(self, team: int, piece_no: int) -> str:
		return _format_team_piece_name_service(self, team, piece_no)

	def _extract_mock_round_stats_health(self, round_info: Any) -> dict[int, int]:
		return _extract_mock_round_stats_health_service(self, round_info)

	def _append_mock_round_details(self, round_number: int) -> None:
		_append_mock_round_details_service(self, round_number)

	def _snapshot_runtime_piece_states(self) -> dict[int, dict[str, Any]]:
		return _snapshot_runtime_piece_states_service(self)

	def _append_runtime_round_details(
		self,
		round_number: int,
		before_states: dict[int, dict[str, Any]],
		after_states: dict[int, dict[str, Any]],
	) -> None:
		_append_runtime_round_details_service(self, round_number, before_states, after_states)

	def _append_round_details_after_step(self, runtime_before_states: Optional[dict[int, dict[str, Any]]] = None) -> None:
		_append_round_details_after_step_service(self, runtime_before_states=runtime_before_states)

	def _build_mock_pieces_for_current_round(self) -> list[dict[str, Any]]:
		return _build_mock_pieces_for_current_round_service(self)

	def _refresh_board_view(self) -> None:
		"""刷新棋盘底图和棋子位置。"""
		_refresh_board_view_service(self)

	def _build_target_markers_for_board(self) -> list[dict[str, Any]]:
		"""根据当前行动面板状态，判断是否应对目标棋子绘制🎯。"""
		return _build_target_markers_for_board_service(self)

	def _build_runtime_trap_markers(self) -> list[dict[str, Any]]:
		return _build_runtime_trap_markers_for_board_service(self)

	def _spell_preview_color(self, spell: Any) -> str:
		return _spell_preview_color_for_board_service(self, spell)

	def _build_spell_aoe_overlay(self) -> tuple[list[tuple[int, int]], str]:
		return _build_spell_aoe_overlay_for_board_service(self)

	def _get_move_target_highlight(self) -> tuple[int, int] | None:
		"""返回需要在棋盘高亮的目标格（移动或法术）。"""
		return _get_move_target_highlight_for_board_service(self)

	def _event_loop_tick(self) -> None:
		_event_loop_tick_service(self)

	def _run_single_round_once(self, source_tag: str = "UI") -> None:
		_run_single_round_once_service(self, source_tag)

	def _build_left_side(self, parent: ttk.Frame) -> None:
		"""构建左侧区域。"""
		_build_left_side_service(self, parent)

	def _build_right_side(self, parent: ttk.Frame) -> None:
		"""构建右侧区域。"""
		_build_right_side_service(self, parent)

	def _sync_replay_round_var(self) -> None:
		_sync_replay_round_var_service(self)

	def _get_mock_total_rounds(self) -> int:
		return _get_mock_total_rounds_service(self)

	def _show_interval_range_warning(self) -> None:
		_show_interval_range_warning_service(self)

	def _apply_replay_speed_from_input(self, *, from_text_input: bool = False) -> None:
		_apply_replay_speed_from_input_service(self, from_text_input=from_text_input)

	def _rebuild_mock_state_to_round(self, target_round: int) -> None:
		_rebuild_mock_state_to_round_service(self, target_round)

	def _apply_round_for_replay(self, target_round: int) -> None:
		_apply_round_for_replay_service(self, target_round)

	def _update_replay_play_pause_button_text(self) -> None:
		_update_replay_play_pause_button_text_service(self)

	def _on_replay_back(self) -> None:
		_on_replay_back_service(self)

	def _on_replay_forward(self) -> None:
		_on_replay_forward_service(self)

	def _on_replay_restart(self) -> None:
		_on_replay_restart_service(self)

	def _on_replay_jump_to_round(self) -> None:
		_on_replay_jump_to_round_service(self)

	def _on_replay_toggle_play_pause(self) -> None:
		_on_replay_toggle_play_pause_service(self)

	def _collect_action_target_options(self) -> list[str]:
		"""收集可用于攻击/法术下拉框的目标候选。"""
		return _collect_action_target_options_service(self)

	def _format_action_target_option(self, piece: Any) -> str:
		return _format_action_target_option_service(self, piece)

	def _resolve_action_target_piece(self, selected_text: str) -> Any:
		return _resolve_action_target_piece_service(self, selected_text)

	def _get_piece_short_code(self, piece: Any) -> str:
		"""返回棋子简称（如 1A、2C），找不到时回退为 ?。"""
		return _get_piece_short_code_service(self, piece)

	def _get_current_actor_text(self) -> str:
		return _get_current_actor_text_service(self)

	def _stop_action_move_point_pick(self) -> None:
		_stop_action_move_point_pick_service(self)

	def _resolve_piece_at_board_xy(self, x: int, y: int) -> Any:
		return _resolve_piece_at_board_xy_service(self, x, y)

	def _on_action_move_pick_overlay_click(self, event: tk.Event) -> str:
		return _on_action_move_pick_overlay_click_service(self, event)

	def _begin_action_move_point_pick(self) -> None:
		_begin_action_move_point_pick_service(self)

	def _begin_action_spell_point_pick(self) -> None:
		_begin_action_spell_point_pick_service(self)

	def _begin_action_spell_target_pick(self) -> None:
		_begin_action_spell_target_pick_service(self)

	def _build_runtime_turn_round_status(self) -> str:
		"""构造 runtime 模式下简洁回合信息文本。"""
		return _build_runtime_turn_round_status_service(self)

	def _append_runtime_turn_round_status(self) -> None:
		"""将 runtime 回合信息追加到右下区（去重，避免刷屏）。"""
		_append_runtime_turn_round_status_service(self)

	def _append_runtime_action_log(
		self,
		actor_code: str,
		action_label: str,
		summary: str,
		targets: Optional[list[str]] = None,
		damage_by_target: Optional[dict[str, int]] = None,
	) -> None:
		"""输出简洁行动记录（黑色默认文本），并预留多目标伤害展示。"""
		_append_runtime_action_log_service(self, actor_code, action_label, summary, targets, damage_by_target)

	def _set_action_feedback(self, message: str, success: bool) -> None:
		_set_action_feedback_service(self, message, success)

	def _clear_action_feedback(self) -> None:
		_clear_action_feedback_service(self)

	def _collapse_action_detail(self) -> None:
		_collapse_action_detail_service(self)

	def _switch_action_mode(self, mode: str, body_container: ttk.Frame) -> None:
		_switch_action_mode_service(self, mode, body_container)

	def _rerender_attack_mode_if_needed(self) -> None:
		_rerender_attack_mode_if_needed_service(self)

	def _refresh_custom_attack_preview(self) -> None:
		_refresh_custom_attack_preview_service(self)

	def _on_open_custom_attack_advanced_settings(self) -> None:
		_on_open_custom_attack_advanced_settings_service(self)

	def _rerender_spell_mode_if_needed(self) -> None:
		_rerender_spell_mode_if_needed_service(self)

	def _spell_display_name(self, spell: Any) -> str:
		return _spell_display_name_service(self, spell)

	def _spell_effect_key(self, spell: Any) -> str:
		return _spell_effect_key_service(self, spell)

	def _collect_available_spell_options(self, caster: Any) -> tuple[list[str], dict[str, Any]]:
		return _collect_available_spell_options_service(self, caster)

	def _resolve_selected_spell(self) -> Any:
		return _resolve_selected_spell_service(self)

	def _collect_spell_target_options(self, spell: Any, caster: Any) -> list[str]:
		return _collect_spell_target_options_service(self, spell, caster)

	def _resolve_spell_target_piece(self, selected_text: str, spell: Any, caster: Any) -> Any:
		return _resolve_spell_target_piece_service(self, selected_text, spell, caster)

	def _collect_area_spell_targets(self, env: Any, caster: Any, spell: Any, area: Any) -> list[Any]:
		return _collect_area_spell_targets_service(self, env, caster, spell, area)

	def _is_teleport_spell(self, spell: Any) -> bool:
		return _is_teleport_spell_service(self, spell)

	def _is_trap_spell(self, spell: Any) -> bool:
		return _is_trap_spell_service(self, spell)

	def _apply_custom_teleport_spell(self, env: Any, caster: Any, spell: Any, spell_cost: int) -> tuple[bool, str, list[str], dict[str, int]]:
		return _apply_custom_teleport_spell_service(self, env, caster, spell, spell_cost)

	def _place_runtime_trap_spell(self, env: Any, caster: Any, spell: Any, spell_cost: int) -> tuple[bool, str, list[str], dict[str, int]]:
		return _place_runtime_trap_spell_service(self, env, caster, spell, spell_cost)

	def _pop_runtime_trap_at_xy(self, x: int, y: int) -> dict[str, Any] | None:
		return _pop_runtime_trap_at_xy_service(self, x, y)

	def _handle_death_check_if_possible(self, env: Any, piece: Any) -> None:
		_handle_death_check_if_possible_service(self, env, piece)

	def _try_trigger_runtime_trap_on_piece(self, env: Any, piece: Any, *, reason: str) -> int | None:
		return _try_trigger_runtime_trap_on_piece_service(self, env, piece, reason=reason)

	def _tick_runtime_traps(self, env: Any, *, round_advanced: bool) -> None:
		"""按“回合”更新陷阱寿命。

		- 每进入新一轮(所有存活棋子行动时段结束一次)才递减 remaining
		- remaining 归零的陷阱自动消散
		- 触发伤害由动作执行后/行动时段结束时单独判定
		"""
		_tick_runtime_traps_service(self, env, round_advanced=round_advanced)

	def _append_attack_formula_info(
		self,
		attack_type: str,
		attacker: Any,
		target: Any,
		*,
		attack_roll: int | None,
		raw_damage: int,
		real_damage: int,
		is_hit: bool,
	) -> None:
		_append_attack_formula_info_service(
			self,
			attack_type,
			attacker,
			target,
			attack_roll=attack_roll,
			raw_damage=raw_damage,
			real_damage=real_damage,
			is_hit=is_hit,
		)

	def _append_runtime_death_and_game_over_info(self, target_piece: Any, target_code: str) -> None:
		_append_runtime_death_and_game_over_info_service(self, target_piece, target_code)

	def _render_action_mode_body(self, body_container: ttk.Frame) -> None:
		_render_action_mode_body_service(self, body_container)

	def _on_preview_submit_action(self) -> None:
		_handle_preview_submit_action_service(self)

	def _on_finish_current_piece_turn(self) -> None:
		"""结束当前棋子行动时段：若未提交动作，则按空行动推进到下一棋子。"""
		_on_finish_current_piece_turn_service(self)

	def _on_click_piece_action(self) -> None:
		"""点击“棋子行动”后，在可变区显示行动编辑面板。"""
		_on_click_piece_action_service(self)

	def _close_replay_mode_ui(self) -> None:
		_close_replay_mode_ui_service(self)

	def _on_click_replay_mode(self) -> None:
		_on_click_replay_mode_service(self)

	# 以下按钮回调先提供最小可用行为，后续在 logic/controller.py 中接入真实逻辑。
	def _on_click_load_data(self) -> None:
		"""模式选择按钮点击事件。
		
		逻辑流程：
		1. 弹出源选择对话框（后端 or mock）
		2. 如果用户取消或关闭，返回不做任何改变
		3. 如果选择后端，直接加载后端数据
		4. 如果选择 mock，继续弹出数据集选择对话框
		   - 如果用户取消或关闭，返回不做任何改变
		   - 如果用户确定，加载该数据集
		5. 成功加载后，重置棋盘并显示新数据
		"""
		_on_click_load_data_service(self)

	def _on_click_mode_selection(self) -> None:
		"""'模式选择'按钮的回调（新命名）。"""
		_on_click_mode_selection_service(self)

	def _on_click_attribute_settings(self, force_runtime_init: bool = False) -> None:
		"""打开属性设置窗口。"""
		_open_attribute_settings_window_service(self, force_runtime_init=force_runtime_init)

	def _set_system_settings_dirty(self, section: str, dirty: bool) -> None:
		_set_system_settings_dirty_service(self, section, dirty)

	def _suppress_system_settings_dirty(self) -> Any:
		"""暂时抑制 system_settings 的 dirty 标记（用于内部同步/回滚/初始化）。"""
		return _suppress_system_settings_dirty_service(self)

	def _suppress_system_settings_dirty_until_idle(self) -> None:
		"""抑制 dirty 直到下一次 Tk idle。

		用于解决“页面构建/控件创建时，控件内部会延迟写回 Variable 导致 trace 误触发”问题。
		"""
		_suppress_system_settings_dirty_until_idle_service(self)

	def _has_any_system_settings_dirty(self) -> bool:
		return _has_any_system_settings_dirty_service(self)

	def _show_confirm_dialog(self, title: str, message: str, yes_text: str = "确定", no_text: str = "取消") -> bool:
		"""显示一个简单的“是/否”确认弹窗，返回是否选择 yes。"""
		return _show_confirm_dialog_service(self, title, message, yes_text=yes_text, no_text=no_text)

	def _get_runtime_near_death_cfg(self, env: Any) -> dict[str, Any]:
		return _get_runtime_near_death_cfg_service(env)

	def _is_runtime_piece_in_near_death(self, env: Any, piece: Any) -> bool:
		return _is_runtime_piece_in_near_death_service(env, piece)

	def _near_death_can_move(self, env: Any) -> bool:
		return _near_death_can_move_service(env)

	def _near_death_can_act(self, env: Any) -> bool:
		return _near_death_can_act_service(env)

	def _reapply_persistent_design_settings_to_runtime_environment(self, env: Any) -> None:
		"""新对局加载后自动重应用（跨局保持）的玩法设计配置。"""
		return _reapply_persistent_design_settings_service(self, env)

	def _apply_spell_pool_config_to_runtime_environment(self, config: dict[str, Any]) -> bool:
		return _apply_spell_pool_config_service(self, config)

	def _on_click_system_settings(self) -> None:
		"""打开系统设置窗口（框架）。

		该窗口用于补充测试端功能与后端暂未实现的能力：
		- 测试端显示/调试能力开关（综合设置）
		- 全局玩法与行动规则的设计入口（玩法设计）
		- 使用教程（长文本、可滚动，未来可改为读取独立文档）
		- 开发信息与状态快照（开发信息）

		注意：后续可能引入权限系统（基础/开发/最高权限），这里先搭 UI 框架。
		"""
		_open_system_settings_window_service(self)

	def _collect_system_general_settings_snapshot_from_vars(self) -> dict[str, Any]:
		return _collect_system_general_settings_snapshot_from_vars_service(self)

	def _apply_system_general_settings_snapshot_to_vars(self, snapshot: dict[str, Any]) -> None:
		_apply_system_general_settings_snapshot_to_vars_service(self, snapshot)

	def _discard_unapplied_system_settings_changes(self) -> None:
		_discard_unapplied_system_settings_changes_service(self)

	def _switch_system_settings_page(self, page_key: str) -> None:
		"""切换系统设置窗口的一级页面（框架）。"""
		_switch_system_settings_page_service(self, page_key)

	def _build_system_settings_general_page(self, parent: ttk.LabelFrame) -> None:
		_build_system_settings_general_page_service(self, parent)

	def _apply_system_general_settings(self, apply_btn: ttk.Button, status_var: tk.StringVar) -> None:
		_apply_system_general_settings_service(self, apply_btn, status_var)

	def _build_system_settings_design_page(self, parent: ttk.LabelFrame) -> None:
		_build_system_settings_design_page_service(self, parent)

	def _build_design_attribute_page(self, parent: ttk.Frame) -> None:
		_build_design_attribute_page_service(self, parent)

	def _ensure_one_talent_gradient_initialized(self, stat_key: str) -> None:
		_ensure_one_talent_gradient_initialized_service(self, stat_key)

	def _apply_design_attribute_talent_gradient_snapshot_to_vars(self, snapshot: dict[str, Any]) -> None:
		_apply_design_attribute_talent_gradient_snapshot_to_vars_service(self, snapshot)

	def _clear_design_attribute_gradient_error_highlight(self) -> None:
		_clear_design_attribute_gradient_error_highlight_service(self)

	def _reset_one_talent_gradient_to_default(self, stat_key: str) -> None:
		_reset_one_talent_gradient_to_default_service(self, stat_key)

	def _reset_design_attribute_talent_gradients(self, btn: ttk.Button) -> None:
		_reset_design_attribute_talent_gradients_service(self, btn)

	def _rebuild_talent_gradient_rows(self, stat_key: str, preserve_values: bool = True) -> None:
		_rebuild_talent_gradient_rows_service(self, stat_key, preserve_values)

	def _build_design_global_page(self, parent: ttk.Frame) -> None:
		_build_design_global_page_service(self, parent)

	def _apply_design_global_near_death_settings(self, btn: ttk.Button) -> None:
		_apply_design_global_near_death_settings_service(self, btn)

	def _build_design_spell_pool_page(self, parent: ttk.Frame) -> None:
		_build_design_spell_pool_page_service(self, parent)

	def _apply_near_death_config_to_runtime_environment(self, config: dict[str, Any]) -> bool:
		return _apply_near_death_config_service(self, config)

	def _parse_int_or_none(self, raw: Any) -> int | None:
		return _parse_int_or_none_service(raw)

	def _apply_design_attribute_talent_gradients(self, btn: ttk.Button) -> None:
		_apply_design_attribute_talent_gradients_service(self, btn)

	def _apply_talent_gradient_config_to_runtime_environment(self, config: dict[str, Any]) -> bool:
		return _apply_talent_gradient_config_service(self, config)

	def _build_system_settings_tutorial_page(self, parent: ttk.LabelFrame) -> None:
		_build_system_settings_tutorial_page_service(self, parent)

	def _build_system_settings_dev_page(self, parent: ttk.LabelFrame) -> None:
		_build_system_settings_dev_page_service(self, parent)

	def _center_popup_window(self, window: tk.Toplevel) -> None:
		"""将弹窗居中到主窗口。"""
		_center_popup_window_service(self, window)

	def _show_notice_popup(self, title: str, message: str, modal: bool = True) -> None:
		"""显示仅可关闭（右上角叉）的提示弹窗。"""
		_show_notice_popup_service(self, title, message, modal=modal)

	def _show_game_over_reset_dialog(self) -> None:
		"""游戏结束后弹窗确认：是否重置游戏。"""
		_show_game_over_reset_dialog_service(self)

	def _show_initiative_summary_popup(self) -> None:
		"""显示开局先攻详情：属性值、随机值、总值、序号与最终顺序。"""
		_show_initiative_summary_popup_service(self)

	def _show_attribute_warning_feedback(self, message: str) -> None:
		"""在属性窗口下方显示 5 秒范围提示。"""
		_show_attribute_warning_feedback_service(self, message)

	def _runtime_init_incomplete_message(self) -> str:
		"""返回后端初始化未完成时的具体提示。"""
		return _runtime_init_incomplete_message_service(self)

	def _switch_attribute_settings_page(self, page_key: str) -> None:
		"""切换属性设置窗口的页面。"""
		_switch_attribute_settings_page_service(self, page_key)

	def _default_action_settings_snapshot(self) -> dict[str, Any]:
		return _default_action_settings_snapshot_service(self)

	def _ensure_action_settings_initialized(self) -> None:
		_ensure_action_settings_initialized_service(self)

	def _sync_action_settings_vars_from_snapshot(self) -> None:
		"""将 snapshot 同步到界面变量（仅用于属性设置-行动页）。"""
		_sync_action_settings_vars_from_snapshot_service(self)

	def _collect_action_settings_snapshot_from_vars(self) -> dict[str, Any]:
		"""从界面变量读取配置，生成 snapshot（不接入后端，仅测试端内存保存）。"""
		return _collect_action_settings_snapshot_from_vars_service(self)

	def _show_action_apply_feedback(self, message: str) -> None:
		_show_action_apply_feedback_service(self, message)

	def _show_action_warning_feedback(self, message: str) -> None:
		_show_action_warning_feedback_service(self, message)

	def _apply_action_attribute_changes(self) -> None:
		"""应用行动属性（本局临时生效）：运行时猴子补丁覆写 env 公式，不改后端文件。"""
		_apply_action_attribute_changes_service(self)

	def _reset_action_attribute_to_defaults(self) -> None:
		_reset_action_attribute_to_defaults_service(self)

	def _apply_action_settings_to_runtime_environment(self, snapshot: dict[str, Any]) -> None:
		"""将行动属性设置注入到 runtime env（仅本局内存生效）。"""
		_apply_action_settings_to_runtime_environment_service(self, snapshot)

	def _build_attribute_action_page(self, content: ttk.LabelFrame) -> None:
		_build_attribute_action_page_service(self, content)

	def _is_map_edit_available(self) -> bool:
		return _is_map_edit_available_service(self)

	def _get_current_map_height(self, x: int, y: int) -> int | None:
		return _get_current_map_height_service(self, x, y)

	def _show_map_apply_feedback(self, message: str) -> None:
		_show_map_apply_feedback_service(self, message)

	def _map_height_to_color(self, height_value: int) -> str:
		return _map_height_to_color_service(self, height_value)

	def _update_map_height_preview(self) -> None:
		_update_map_height_preview_service(self)

	def _apply_map_height_change(self) -> None:
		_apply_map_height_change_service(self)

	def _stop_map_point_pick(self) -> None:
		_stop_map_point_pick_service(self)

	def _restore_map_attribute_page_after_pick(self) -> None:
		"""结束选点并回到地图属性页，不修改本次坐标。"""
		_restore_map_attribute_page_after_pick_service(self)

	def _show_map_pick_invalid_popup(self) -> None:
		"""地图选点时点击非法区域后的引导弹窗。"""
		_show_map_pick_invalid_popup_service(self)

	def _on_map_pick_overlay_click(self, event: tk.Event) -> str:
		return _on_map_pick_overlay_click_service(self, event)

	def _begin_map_point_pick(self) -> None:
		_begin_map_point_pick_service(self)

	def _build_attribute_map_page(self, content: ttk.LabelFrame) -> None:
		_build_attribute_map_page_service(self, content)

	def _piece_slot_keys(self) -> list[str]:
		return _piece_slot_keys_service(self)

	def _coerce_piece_list(self, pieces_obj: Any) -> list[Any]:
		return _coerce_piece_list_service(self, pieces_obj)

	def _runtime_piece_slot_map(self) -> dict[str, Any]:
		return _runtime_piece_slot_map_service(self)

	def _capture_runtime_piece_slot_binding_from_init_config(self) -> None:
		"""按初始化配置建立棋子与槽位的一次性绑定，避免非连续槽位被重排。"""
		_capture_runtime_piece_slot_binding_from_init_config_service(self)

	def _mock_piece_slot_map(self) -> dict[str, int]:
		return _mock_piece_slot_map_service(self)

	def _get_piece_row_values(self, slot_key: str, runtime_map: dict[str, Any], mock_map: dict[str, int]) -> dict[str, str]:
		return _get_piece_row_values_service(self, slot_key, runtime_map, mock_map)

	def _piece_attr_range(self, field: str) -> tuple[float, float]:
		return _piece_attr_range_service(self, field)

	def _normalize_piece_value(
		self,
		*,
		slot_display_name: str,
		field: str,
		raw_value: str,
		allow_unset_hp: bool,
	) -> tuple[str, str | None]:
		return _normalize_piece_value_service(
			self,
			slot_display_name=slot_display_name,
			field=field,
			raw_value=raw_value,
			allow_unset_hp=allow_unset_hp,
		)

	def _is_walkable_for_piece(self, x: int, y: int) -> bool:
		return _is_walkable_for_piece_service(self, x, y)

	def _runtime_border_line(self) -> int:
		return _runtime_border_line_service(self)

	def _clamp_piece_position(self, x: int, y: int) -> tuple[int, int]:
		"""将坐标限制在当前地图范围内。"""
		return _clamp_piece_position_service(self, x, y)

	def _show_attribute_apply_feedback(self, message: str) -> None:
		_show_attribute_apply_feedback_service(self, message)

	def _safe_int(self, value: str, default: int = 0) -> int:
		return _safe_int_service(self, value, default)

	def _safe_float(self, value: str, default: float = 0.0) -> float:
		return _safe_float_service(self, value, default)

	def _apply_piece_attribute_changes(self) -> None:
		_apply_piece_attribute_changes_service(self)

	def _build_attribute_piece_page(self, content: ttk.LabelFrame) -> None:
		"""构建棋子属性页：固定 6 槽位，矩阵化布局并支持纵向滚动。"""
		_build_attribute_piece_page_service(self, content)

	def _on_click_start(self) -> None:
		_on_click_start_service(self)

	def _on_click_pause(self) -> None:
		_on_click_pause_service(self)

	def _on_click_step(self) -> None:
		_on_click_step_service(self)

	def _on_click_reset(self) -> None:
		_on_click_reset_service(self)

	def _on_event_game_loaded(self, event) -> None:
		_on_event_game_loaded_service(self, event)

	def _on_event_round_started(self, event) -> None:
		_on_event_round_started_service(self, event)

	def _on_event_round_finished(self, event) -> None:
		_on_event_round_finished_service(self, event)

	def _on_event_game_over(self, _event) -> None:
		_on_event_game_over_service(self, _event)

	def _on_click_initialize(self) -> None:
		_on_click_initialize_service(self)

	def _on_click_exit(self) -> None:
		_on_click_initialize_service(self)

	def _on_right_composite_panel_initialize(self) -> None:
		_on_right_composite_panel_initialize_service(self)


def launch() -> None:
	"""单独提供启动函数，便于 main.py 调用。"""
	root = tk.Tk()
	MainUI(root)
	root.mainloop()


if __name__ == "__main__":
	launch()