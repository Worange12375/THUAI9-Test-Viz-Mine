"""重置流程（从 MainUI 拆分）。

本文件负责：
- “重置”按钮的 UI 侧流程：关闭回放 UI、暂停、重置 controller/env（必要时）、清空 UI 状态，
  并重新弹出数据源/数据集选择对话框后加载。

不负责：
- 实际数据加载细节（由 MainUI 现有的加载方法完成）。

设计说明：
- 为保持行为不变，本 service 直接接收 `main_ui` 实例并访问其字段/方法。
"""

from __future__ import annotations

from typing import Any


def on_click_reset(main_ui: Any) -> None:
	"""执行重置流程（保持 main_ui 原行为）。"""
	main_ui._close_replay_mode_ui()
	main_ui._on_click_pause()
	try:
		if main_ui.controller.runtime_source == "runtime_env":
			main_ui.controller.reset_environment()
		main_ui.loaded = False
		main_ui.runtime_card_slots = []
		main_ui.mock_card_slots = []
		main_ui.mock_initial_positions = {}
		main_ui.mock_piece_stats_by_id = {}
		main_ui.mock_last_health_by_id = {}
		main_ui.mock_last_positions_by_id = {}
		main_ui.mock_piece_number_by_id = {}
		main_ui.runtime_piece_slot_binding = {}
		main_ui.runtime_trap_effects = []
		# 重置行动选择状态，避免重开后棋盘仍残留目标高亮/施法点。
		main_ui.action_ui_mode.set("move")
		main_ui.action_move_x_var.set("")
		main_ui.action_move_y_var.set("")
		main_ui.action_spell_type_var.set("")
		main_ui.action_spell_target_var.set("")
		main_ui.action_spell_point_x_var.set("")
		main_ui.action_spell_point_y_var.set("")
		main_ui.action_spell_option_map = {}
		main_ui.action_spell_target_option_map = {}
		main_ui.action_panel_status_label = None
		main_ui.game_over_message_shown = False
		main_ui.left_board_panel.reset_board_state()
		main_ui._refresh_piece_cards()
		choice = main_ui._show_source_selection_dialog("重置后：选择数据源")
		if choice is not None:
			main_ui.selected_source = choice
		if main_ui.selected_source == "mock":
			selected = main_ui._show_mock_dataset_dialog("重置后：选择 mock 数据集")
			if selected is not None:
				main_ui.selected_mock_dataset = selected
		main_ui.right_info_panel.append_content("\n[UI] 重置完成，正在按选择加载数据")
		# 这里已完成 source/dataset 选择，直接加载，避免再次弹出“模式选择”弹窗。
		main_ui._load_data_with_selected_source()
	except Exception as e:
		main_ui.right_info_panel.append_content(f"\n[UI] 重置失败: {e}")
