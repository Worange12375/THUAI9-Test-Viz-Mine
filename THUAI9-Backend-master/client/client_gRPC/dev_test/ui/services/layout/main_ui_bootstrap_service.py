"""MainUI 启动/初始化（bootstrap）下沉。

目标：让 main_ui.py 的 MainUI.__init__ 保持“薄委托”，把大量状态字段初始化与事件订阅迁移到此处。

约束：
- 不 import main_ui（避免循环依赖）；
- 通过 duck-typing 操作 main_ui 的字段/方法；
- 保持现有 UX/行为不变（仅搬家，不改逻辑）。
"""

from __future__ import annotations

from typing import Any, Optional

import tkinter as tk
from tkinter import ttk

from logic.controller import Controller
from core.events import EventType


def bootstrap_main_ui(main_ui: Any, root: tk.Tk) -> None:
	main_ui.root = root
	root.title("THUAI9 后端逻辑测试 UI")
	# 折中布局：适度增加默认宽度，给右侧信息区更多范围。
	# 同时配合最小尺寸约束，保证左侧棋盘在较小窗口下也能完整显示。
	root.geometry("1280x900")
	root.minsize(1200, 760)

	# 主容器填满整个窗口，并作为左右分栏的承载层。
	main_container = ttk.Frame(root, padding=12)
	main_container.pack(fill="both", expand=True)

	# 将左右列改为更接近 1:1，整体收窄左侧信息区与棋盘区域宽度。
	main_container.columnconfigure(0, weight=6)
	main_container.columnconfigure(1, weight=6)
	main_container.rowconfigure(0, weight=1)

	left_frame = ttk.Frame(main_container)
	right_frame = ttk.Frame(main_container)
	left_frame.configure(width=620)
	left_frame.grid_propagate(False)

	left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
	right_frame.grid(row=0, column=1, sticky="nsew")

	main_ui.controller = Controller(mode="manual")
	main_ui.loaded = False
	main_ui.running = False
	main_ui.loop_job: Optional[str] = None
	main_ui.replay_speed_ms = 1000
	main_ui.replay_speed_var = tk.IntVar(value=main_ui.replay_speed_ms)
	main_ui.replay_round_var = tk.IntVar(value=0)
	main_ui.replay_controls_visible = False
	main_ui.replay_play_pause_button: ttk.Button | None = None
	main_ui.selected_source = "runtime_custom"
	main_ui.selected_mock_dataset = None
	main_ui.mock_initial_positions = {}
	main_ui.mock_piece_stats_by_id = {}
	main_ui.mock_last_health_by_id = {}
	main_ui.mock_last_positions_by_id = {}
	main_ui.mock_piece_number_by_id = {}
	main_ui.attribute_settings_window = None
	main_ui.attribute_settings_content_frame = None
	main_ui.attribute_settings_nav_buttons = {}
	main_ui.system_settings_window = None
	main_ui.system_settings_content_frame = None
	main_ui.system_settings_nav_buttons = {}
	# 系统设置：右侧信息展示区（InfoPanel）显示类别开关。
	main_ui.right_info_category_visibility_vars = {
		"default": tk.BooleanVar(value=True),
		"system": tk.BooleanVar(value=True),
		"player": tk.BooleanVar(value=True),
		"round": tk.BooleanVar(value=True),
		"important": tk.BooleanVar(value=True),
	}
	# 系统设置：投掷结果设置（仅测试端覆盖 d20 返回值，不修改后端算法）。
	main_ui._D20_FORCE_OPTIONS = [
		("attack_hit", "攻击命中检定（物理/普通法术）"),
		("death_check", "死亡检定（HP→0）"),
		("initiative", "先攻（行动队列）"),
	]
	main_ui.system_force_d20_vars = {key: tk.BooleanVar(value=False) for key, _label in main_ui._D20_FORCE_OPTIONS}
	main_ui.system_force_d20_flags = {key: False for key, _label in main_ui._D20_FORCE_OPTIONS}
	main_ui.system_force_d20_value_vars = {key: tk.StringVar(value="20") for key, _label in main_ui._D20_FORCE_OPTIONS}
	main_ui.system_force_d20_values = {key: 20 for key, _label in main_ui._D20_FORCE_OPTIONS}
	# 颜色下拉框目前仅做 UI 预留（不影响渲染），先保留用户选择。
	main_ui.right_info_category_color_vars = {
		"default": tk.StringVar(value="黑色"),
		"system": tk.StringVar(value="灰色"),
		"player": tk.StringVar(value="黑色"),
		"round": tk.StringVar(value="橙色"),
		"important": tk.StringVar(value="红色"),
	}
	# 玩法设计：属性派生上限梯度（默认值来自 dev_test 文档 talent_attributes.md，并与后端 env.py 一致）。
	# - 力量：最大行动位上限 strength<=13/21 -> 1/2 else 3
	# - 智力：最大法术位上限 intelligence<=3/7/12/16/21 -> 1/2/3/5/8 else 9
	# - 敏捷：后端当前无“分段上限”梯度（移动力为公式），这里默认给 1 段占位（不影响后端）。
	main_ui._DEFAULT_DERIVED_CAP_THRESHOLDS = {
		"strength": [13, 21],
		"dexterity": [],
		"intelligence": [3, 7, 12, 16, 21],
	}
	main_ui._DEFAULT_DERIVED_CAP_VALUES = {
		"strength": [1, 2, 3],
		"dexterity": [0],
		"intelligence": [1, 2, 3, 5, 8, 9],
	}
	main_ui.design_talent_gradient_count_vars = {
		"strength": tk.IntVar(value=len(main_ui._DEFAULT_DERIVED_CAP_VALUES["strength"])),
		"dexterity": tk.IntVar(value=len(main_ui._DEFAULT_DERIVED_CAP_VALUES["dexterity"])),
		"intelligence": tk.IntVar(value=len(main_ui._DEFAULT_DERIVED_CAP_VALUES["intelligence"])),
	}
	main_ui.design_talent_gradient_threshold_vars = {"strength": [], "dexterity": [], "intelligence": []}
	main_ui.design_talent_gradient_value_vars = {"strength": [], "dexterity": [], "intelligence": []}
	main_ui.design_talent_gradient_threshold_entries = {"strength": [], "dexterity": [], "intelligence": []}
	main_ui.design_talent_gradient_value_entries = {"strength": [], "dexterity": [], "intelligence": []}
	main_ui.design_talent_gradient_rows_frame = {"strength": None, "dexterity": None, "intelligence": None}
	main_ui.design_attribute_status_var = None
	# 仅用于“玩法设计-属性/全局”滚动：鼠标位于子控件上时仍能捕获滚轮。
	main_ui._design_attribute_mousewheel_bind_id = None
	main_ui._design_global_mousewheel_bind_id = None
	main_ui._design_spell_mousewheel_bind_id = None
	# 玩法设计：全局 - 濒死系统（测试端独立玩法）
	main_ui.design_near_death_enabled_var = tk.BooleanVar(value=True)
	main_ui.design_near_death_revive_hp_var = tk.StringVar(value="1")
	main_ui.design_near_death_turns_to_die_var = tk.IntVar(value=1)
	main_ui.design_near_death_die_on_damage_var = tk.BooleanVar(value=True)
	# 濒死状态行动能力（先做 UI + 写入配置；具体落地逻辑后续再做，避免引入新复杂 bug）
	# 需求：默认改为“不能移动、不能攻击或法术”，并真正落地限制。
	main_ui.design_near_death_can_move_var = tk.BooleanVar(value=False)
	main_ui.design_near_death_can_attack_spell_var = tk.BooleanVar(value=False)
	# 玩法设计：跨局保持（本次 UI 运行期间）。
	# 现默认启用：濒死系统、测试端法术池（满足“默认开启/默认测试端实现”需求）。
	main_ui._persistent_near_death_design_config = {
		"near_death": {
			"enabled": True,
			"revive_hp_on_20": 1,
			"turns_to_die": 1,
			"die_on_damage_when_dying": True,
			"can_move_when_dying": False,
			"can_attack_or_spell_when_dying": False,
		}
	}
	main_ui._persistent_spell_pool_design_config = {
		"use_test_spell_impl": True,
		"spell_priorities": {
			"WarriorLong": {"arrow_hit": 1, "heal": 2},
			"WarriorShort": {"trap": 1, "heal": 2},
			"Archer": {"arrow_hit": 1, "trap": 2},
			"Mage": {"arrow_hit": 1, "trap": 2, "heal": 3, "teleport": 4, "fireball": 5},
		},
	}
	# 系统设置：已应用快照（用于“关闭并丢弃未应用修改”时回滚）。
	main_ui._applied_system_general_settings_snapshot = None
	# 系统设置：未应用（dirty）提示与关闭确认。
	main_ui._system_settings_dirty_flags = {
		"general": False,
		"design_global_near_death": False,
		"design_attribute": False,
		"design_spell_pool": False,
	}
	main_ui._system_settings_dirty_label_vars = {}
	main_ui._system_settings_dirty_trace_bound_sections = set()
	# 玩法设计：法术池配置（职业×法术优先级）
	# - 优先级取值：0（不选） 或 1~5（优先级，数字越小越优先）
	# - 与“启用测试端法术默认实现”联动：关闭时走后端实现，表格禁用，仅展示后端默认。
	main_ui.design_spell_use_test_impl_var = tk.BooleanVar(value=True)
	main_ui.design_spell_priority_vars = {}
	# 切到“走后端实现”时缓存测试端表格值，避免用户来回切换丢失输入。
	main_ui._spell_priority_cache_when_test_impl_enabled = None
	main_ui._design_spell_use_test_impl_trace_bound = False
	main_ui.design_global_status_var = None
	main_ui.attribute_piece_vars = {}
	main_ui.attribute_piece_entries = {}
	main_ui.attribute_piece_last_edit_tick = {}
	main_ui.attribute_edit_tick_counter = 0
	main_ui.attribute_internal_update = False
	main_ui.attribute_piece_apply_status_label = None
	main_ui.attribute_piece_apply_status_job = None
	main_ui.attribute_piece_warning_label = None
	main_ui.attribute_piece_warning_job = None
	main_ui.attribute_piece_hp_hint_widgets = {}
	main_ui.attribute_action_apply_status_label = None
	main_ui.attribute_action_warning_label = None
	main_ui.attribute_action_attack_vars = {}
	main_ui.attribute_action_attack_defaults = {}
	main_ui.attribute_action_spell_enable_vars = {}
	main_ui.attribute_action_spell_vars = {}
	main_ui.action_settings_snapshot = {}
	main_ui.action_attribute_internal_update = False
	main_ui._action_attribute_dirty_trace_bound = False
	main_ui.attribute_map_x_var = tk.StringVar(value="")
	main_ui.attribute_map_y_var = tk.StringVar(value="")
	main_ui.attribute_map_height_var = tk.StringVar(value="")
	main_ui.attribute_map_height_color_canvas = None
	main_ui.attribute_map_height_var.trace_add("write", lambda *_args: main_ui._update_map_height_preview())
	main_ui.attribute_map_apply_status_label = None
	main_ui.attribute_map_pick_waiting = False
	main_ui.attribute_map_pick_overlay = None
	main_ui.attribute_map_pick_invalid_popup = None
	main_ui.attribute_settings_force_init_mode = False
	main_ui.runtime_init_config_ready = False
	main_ui.runtime_piece_init_config = {}
	main_ui.runtime_piece_slot_binding = {}
	main_ui._profession_derived_cache = {}
	main_ui.mock_map_height_overrides = {}
	main_ui.runtime_card_slots = []
	main_ui.mock_card_slots = []
	main_ui.runtime_initiative_snapshot = []
	main_ui.pending_actions_by_piece_id = {}
	main_ui.action_ui_mode = tk.StringVar(value="move")
	main_ui.action_move_piece_var = tk.StringVar(value="当前棋子")
	main_ui.action_move_x_var = tk.StringVar(value="")
	main_ui.action_move_y_var = tk.StringVar(value="")
	main_ui.action_move_x_var.trace_add("write", lambda *_args: main_ui._refresh_board_view())
	main_ui.action_move_y_var.trace_add("write", lambda *_args: main_ui._refresh_board_view())
	main_ui.action_attack_target_var = tk.StringVar(value="")
	main_ui.action_attack_type_var = tk.StringVar(value="")
	main_ui.action_custom_damage_var = tk.StringVar(value="10")
	main_ui.action_custom_preview_var = tk.StringVar(value="")
	main_ui.action_spell_target_var = tk.StringVar(value="")
	main_ui.action_spell_type_var = tk.StringVar(value="")
	main_ui.action_spell_point_x_var = tk.StringVar(value="")
	main_ui.action_spell_point_y_var = tk.StringVar(value="")
	main_ui.action_spell_option_map = {}
	main_ui.action_spell_target_option_map = {}
	main_ui.action_detail_container = None
	main_ui.action_mode_body_container = None
	main_ui.action_confirm_button = None
	main_ui.action_feedback_label = None
	main_ui.action_feedback_clear_job = None
	main_ui._angel_refresh_job = None
	main_ui._rendering_action_mode_body = False
	main_ui.action_panel_status_label = None
	main_ui.action_attack_target_var.trace_add("write", lambda *_args: main_ui._refresh_custom_attack_preview())
	main_ui.action_attack_target_var.trace_add("write", lambda *_args: main_ui._refresh_board_view())
	main_ui.action_attack_type_var.trace_add("write", lambda *_args: main_ui._refresh_board_view())
	main_ui.action_custom_damage_var.trace_add("write", lambda *_args: main_ui._refresh_custom_attack_preview())
	main_ui.action_spell_type_var.trace_add("write", lambda *_args: main_ui._rerender_spell_mode_if_needed())
	main_ui.action_spell_target_var.trace_add("write", lambda *_args: main_ui._refresh_board_view())
	main_ui.action_spell_point_x_var.trace_add("write", lambda *_args: main_ui._refresh_board_view())
	main_ui.action_spell_point_y_var.trace_add("write", lambda *_args: main_ui._refresh_board_view())
	main_ui.game_over_dialog_shown = False
	main_ui.game_over_message_shown = False
	main_ui.runtime_cycle_done_piece_ids = set()
	main_ui.runtime_completed_turns = 0
	main_ui.runtime_last_round_info_line = ""
	main_ui.action_move_pick_waiting = False
	main_ui.action_move_pick_overlay = None
	main_ui.action_pick_mode = ""
	main_ui.runtime_trap_effects = []

	main_ui.controller.event_bus.subscribe(EventType.GAME_LOADED, main_ui._on_event_game_loaded)
	main_ui.controller.event_bus.subscribe(EventType.ROUND_STARTED, main_ui._on_event_round_started)
	main_ui.controller.event_bus.subscribe(EventType.ROUND_FINISHED, main_ui._on_event_round_finished)
	main_ui.controller.event_bus.subscribe(EventType.GAME_OVER, main_ui._on_event_game_over)

	main_ui._build_left_side(left_frame)
	main_ui._build_right_side(right_frame)
	root.after(100, main_ui._startup_load_with_source_dialog)


def on_click_initialize(main_ui: Any) -> None:
	"""退出测试：打印 UI 日志并退出 Tk 主循环。"""
	main_ui.right_info_panel.append_content("\n[UI] 退出测试...")
	main_ui.root.quit()
