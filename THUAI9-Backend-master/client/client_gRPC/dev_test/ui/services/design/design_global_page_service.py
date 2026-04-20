"""玩法设计-全局页 Service（Phase 4 拆分产物）。

本文件负责：
- 构建“系统设置 → 玩法设计 → 全局”页面（目前：濒死系统 UI）。
- 采集并应用濒死系统配置（跨局保持，runtime env 存在时即时注入）。

不负责：
- 濒死系统结算逻辑本体（由 test_mock_gameplay + runtime hook 负责）。
- 系统设置窗口外层框架/导航。

设计原则：搬家不改逻辑。
"""

from __future__ import annotations

import copy
from typing import Any

import tkinter as tk
from tkinter import ttk


def build_design_global_page(main_ui: Any, parent: ttk.Frame) -> None:
	"""玩法设计 -> 全局页面：目前仅实现濒死系统（测试端独立玩法）。"""
	# 部分控件会在创建后的 idle 阶段写回 Variable；抑制该阶段的“写入即脏”。
	main_ui._suppress_system_settings_dirty_until_idle()
	parent.columnconfigure(0, weight=1)
	# 滚动区占剩余空间；按钮行固定不随滚动。
	parent.rowconfigure(1, weight=1)
	parent.rowconfigure(2, weight=0)

	ttk.Label(parent, text="全局玩法", font=("Microsoft YaHei UI", 11, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)

	# 内容可能较高：用自适应高度滚动容器，避免控件“跑到界面外”。
	scroll_host = ttk.Frame(parent)
	scroll_host.grid(row=1, column=0, sticky="nsew")
	scroll_host.columnconfigure(0, weight=1)
	scroll_host.rowconfigure(0, weight=1)

	canvas = tk.Canvas(scroll_host, highlightthickness=0, borderwidth=0)
	v_scroll = ttk.Scrollbar(scroll_host, orient="vertical", command=canvas.yview)
	canvas.configure(yscrollcommand=v_scroll.set)
	canvas.grid(row=0, column=0, sticky="nsew")
	v_scroll.grid(row=0, column=1, sticky="ns")

	body = ttk.Frame(canvas)
	canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")
	body.columnconfigure(0, weight=1)

	def _sync_scroll_region(_event: Any = None) -> None:
		try:
			body.update_idletasks()
			req_w = int(body.winfo_reqwidth())
			req_h = int(body.winfo_reqheight())
			canvas.configure(scrollregion=(0, 0, max(req_w, 1), max(req_h, 1)))
			# 自适应高度：内容少时贴合；内容多时给上限并允许滚动。
			desired = min(max(req_h + 8, 180), 520)
			canvas.configure(height=int(desired))
		except Exception:
			canvas.configure(scrollregion=canvas.bbox("all"))

	note_label: ttk.Label | None = None
	preview: ttk.Label | None = None

	def _fit_body_width(event: Any) -> None:
		try:
			w = int(event.width)
		except Exception:
			w = 0
		try:
			canvas.itemconfigure(canvas_window, width=max(w, 1))
		except Exception:
			pass
		wrap = max(200, w - 40)
		try:
			if note_label is not None:
				note_label.configure(wraplength=wrap)
		except Exception:
			pass
		try:
			if preview is not None:
				preview.configure(wraplength=wrap)
		except Exception:
			pass

	def _on_mousewheel(event: Any) -> None:
		try:
			sr = str(canvas.cget("scrollregion") or "").strip()
			parts = [float(x) for x in sr.split()] if sr else []
			content_h = float(parts[3] - parts[1]) if len(parts) == 4 else 0.0
			view_h = float(canvas.winfo_height())
			if content_h <= view_h + 2:
				return
		except Exception:
			pass
		try:
			delta = int(getattr(event, "delta", 0))
			if delta == 0:
				return
		except Exception:
			return
		try:
			canvas.yview_scroll(-int(delta / 120), "units")
			first, last = canvas.yview()
			if first < 0:
				canvas.yview_moveto(0)
			elif last > 1:
				span = max(1e-9, last - first)
				canvas.yview_moveto(max(0.0, 1.0 - span))
		except Exception:
			return

	def _bind_wheel_global() -> None:
		if main_ui._design_global_mousewheel_bind_id is None:
			try:
				main_ui._design_global_mousewheel_bind_id = main_ui.root.bind_all(
					"<MouseWheel>", _on_mousewheel, add="+"
				)
			except Exception:
				main_ui._design_global_mousewheel_bind_id = None

	def _unbind_wheel_global() -> None:
		if main_ui._design_global_mousewheel_bind_id is not None:
			try:
				main_ui.root.unbind_all("<MouseWheel>", main_ui._design_global_mousewheel_bind_id)
			except Exception:
				pass
			main_ui._design_global_mousewheel_bind_id = None

	body.bind("<Configure>", _sync_scroll_region)
	canvas.bind("<Configure>", _fit_body_width)
	scroll_host.bind("<Enter>", lambda _e: _bind_wheel_global())
	scroll_host.bind("<Leave>", lambda _e: _unbind_wheel_global())

	box = ttk.LabelFrame(body, text="濒死系统（测试端独立玩法）", padding=10)
	box.grid(row=0, column=0, sticky="nsew")
	box.columnconfigure(0, weight=1)

	note = (
		"设计来源：warchess_plan (1).md（后端当前未实现，故仅在测试端启用）。\n"
		"当棋子生命降为 0 时触发死亡检定；结果可能进入【濒死】。"
	)
	note_label = ttk.Label(box, text=note, justify="left", foreground="#4b5563")
	note_label.grid(row=0, column=0, sticky="w")

	enable_row = ttk.Frame(box)
	enable_row.grid(row=1, column=0, sticky="ew", pady=(10, 0))
	# 避免把 Entry 所在列拉伸导致“【空】HP”间隔过大：把弹性空间放到最后一列。
	enable_row.columnconfigure(4, weight=1)
	ttk.Checkbutton(enable_row, text="启用濒死系统（默认开启）", variable=main_ui.design_near_death_enabled_var).grid(
		row=0, column=0, sticky="w"
	)
	ttk.Label(enable_row, text="死亡检定 d20=20 恢复至").grid(row=0, column=1, sticky="w", padx=(14, 0))
	revive_entry = ttk.Entry(enable_row, textvariable=main_ui.design_near_death_revive_hp_var, width=6)
	revive_entry.grid(row=0, column=2, sticky="w", padx=(6, 6))
	ttk.Label(enable_row, text="HP").grid(row=0, column=3, sticky="w")
	ttk.Label(enable_row, text="").grid(row=0, column=4, sticky="ew")

	param_row = ttk.Frame(box)
	param_row.grid(row=2, column=0, sticky="ew", pady=(8, 0))
	ttk.Label(param_row, text="濒死后，在经过").grid(row=0, column=0, sticky="w")
	turn_spin = tk.Spinbox(param_row, from_=1, to=3, width=3, textvariable=main_ui.design_near_death_turns_to_die_var)
	turn_spin.grid(row=0, column=1, sticky="w", padx=(6, 6))
	turn_hint_var = tk.StringVar(value="轮（即0回合）后直接死亡")
	ttk.Label(param_row, textvariable=turn_hint_var).grid(row=0, column=2, sticky="w")
	ttk.Checkbutton(param_row, text="濒死期间再次受伤直接死亡", variable=main_ui.design_near_death_die_on_damage_var).grid(
		row=0, column=3, sticky="w", padx=(14, 0)
	)

	cap_row = ttk.Frame(box)
	cap_row.grid(row=3, column=0, sticky="ew", pady=(8, 0))
	# 文案口径："濒死状态下，棋子" + 勾选框(能/不能) + "移动，" + 勾选框(能/不能) + "攻击或法术。"
	ttk.Label(cap_row, text="濒死状态下，棋子").grid(row=0, column=0, sticky="w")
	move_text_var = tk.StringVar(value="能")
	act_text_var = tk.StringVar(value="能")
	move_ck = ttk.Checkbutton(cap_row, variable=main_ui.design_near_death_can_move_var, textvariable=move_text_var)
	move_ck.grid(row=0, column=1, sticky="w", padx=(4, 0))
	ttk.Label(cap_row, text="移动，").grid(row=0, column=2, sticky="w")
	act_ck = ttk.Checkbutton(cap_row, variable=main_ui.design_near_death_can_attack_spell_var, textvariable=act_text_var)
	act_ck.grid(row=0, column=3, sticky="w", padx=(4, 0))
	ttk.Label(cap_row, text="攻击或法术。",).grid(row=0, column=4, sticky="w")

	preview_var = tk.StringVar(value="")
	preview = ttk.Label(box, textvariable=preview_var, justify="left", foreground="#374151")
	preview.grid(row=4, column=0, sticky="w", pady=(10, 0))

	def _runtime_alive_piece_count() -> int:
		"""用于 UI 展示的“回合数”估算：按当前场上 is_alive=True 的棋子数计。"""
		try:
			if main_ui.controller.runtime_source != "runtime_env":
				return 0
			env = getattr(main_ui.controller, "environment", None)
			if env is None:
				return 0
			total = 0
			for player_attr in ("player1", "player2"):
				player = getattr(env, player_attr, None)
				pieces = main_ui._coerce_piece_list(getattr(player, "pieces", None) if player is not None else None)
				for p in pieces:
					try:
						if bool(getattr(p, "is_alive", True)):
							total += 1
					except Exception:
						continue
			return max(0, int(total))
		except Exception:
			return 0

	def _refresh_capability_texts(*_args: Any) -> None:
		move_text_var.set("能" if bool(main_ui.design_near_death_can_move_var.get()) else "不能")
		act_text_var.set("能" if bool(main_ui.design_near_death_can_attack_spell_var.get()) else "不能")

	def _refresh_turn_hint(*_args: Any) -> None:
		try:
			rounds = int(main_ui.design_near_death_turns_to_die_var.get())
		except Exception:
			rounds = 1
		rounds = max(1, min(3, rounds))
		alive_cnt = _runtime_alive_piece_count()
		if alive_cnt <= 0:
			turn_hint_var.set("轮（即?回合）后直接死亡")
			return
		turn_hint_var.set(f"轮（即{alive_cnt * rounds}回合）后直接死亡")

	def _refresh_preview(*_args: Any) -> None:
		enabled = bool(main_ui.design_near_death_enabled_var.get())
		revive_hp = str(main_ui.design_near_death_revive_hp_var.get()).strip() or "1"
		try:
			turns = int(main_ui.design_near_death_turns_to_die_var.get())
		except Exception:
			turns = 1
		turns = max(1, min(3, turns))
		die_on_damage = bool(main_ui.design_near_death_die_on_damage_var.get())
		alive_cnt = _runtime_alive_piece_count()
		total_turns = int(alive_cnt * turns) if alive_cnt > 0 else 0
		can_move = bool(main_ui.design_near_death_can_move_var.get())
		can_act = bool(main_ui.design_near_death_can_attack_spell_var.get())
		preview_var.set(
			"\n".join(
				[
					f"当前：{'开启' if enabled else '关闭'}",
					"死亡检定：HP→0 时掷 d20；20 恢复；1 直接死亡；其他进入濒死",
					f"d20=20：恢复至 {revive_hp} HP",
					(
						f"濒死：经过 {turns} 轮（约 {total_turns} 回合）后死亡"
						if alive_cnt > 0
						else f"濒死：经过 {turns} 轮后死亡（未加载 runtime env，无法估算回合数）"
					),
					f"濒死期间再次受伤：{'直接死亡' if die_on_damage else '按死亡检定处理'}",
					f"濒死行动能力：移动={'能' if can_move else '不能'}；攻击/法术={'能' if can_act else '不能'}",
					"被治疗至 >0：解除濒死",
				]
			)
		)

	for var in (
		main_ui.design_near_death_enabled_var,
		main_ui.design_near_death_revive_hp_var,
		main_ui.design_near_death_turns_to_die_var,
		main_ui.design_near_death_die_on_damage_var,
		main_ui.design_near_death_can_move_var,
		main_ui.design_near_death_can_attack_spell_var,
	):
		try:
			var.trace_add("write", _refresh_preview)
		except Exception:
			pass
	try:
		main_ui.design_near_death_can_move_var.trace_add("write", _refresh_capability_texts)
		main_ui.design_near_death_can_attack_spell_var.trace_add("write", _refresh_capability_texts)
	except Exception:
		pass
	try:
		main_ui.design_near_death_turns_to_die_var.trace_add("write", _refresh_turn_hint)
	except Exception:
		pass
	_refresh_capability_texts()
	_refresh_turn_hint()
	_refresh_preview()

	# 固定按钮行：不随滚动移动
	btn_row = ttk.Frame(parent)
	btn_row.grid(row=2, column=0, sticky="ew", pady=(12, 0))
	btn_row.columnconfigure(0, weight=1)
	if main_ui.design_global_status_var is None:
		main_ui.design_global_status_var = tk.StringVar(value="")
	ttk.Label(btn_row, textvariable=main_ui.design_global_status_var, foreground="#6b7280").grid(
		row=0, column=0, sticky="w"
	)
	dirty_var = tk.StringVar(value="")
	try:
		main_ui._system_settings_dirty_label_vars["design_global_near_death"] = dirty_var
		dirty_var.set(
			"（未应用）" if bool(main_ui._system_settings_dirty_flags.get("design_global_near_death", False)) else ""
		)
	except Exception:
		pass
	ttk.Label(btn_row, textvariable=dirty_var, foreground="#b45309").grid(row=0, column=1, sticky="e", padx=(0, 8))
	apply_btn = ttk.Button(btn_row, text="应用", command=lambda: main_ui._apply_design_global_near_death_settings(apply_btn))
	apply_btn.grid(row=0, column=2, sticky="e")

	def _reset_to_default() -> None:
		# 恢复为 UI 侧默认：默认开启；濒死期间默认不能移动/不能攻击或法术。
		try:
			main_ui.design_near_death_enabled_var.set(True)
			main_ui.design_near_death_revive_hp_var.set("1")
			main_ui.design_near_death_turns_to_die_var.set(1)
			main_ui.design_near_death_die_on_damage_var.set(True)
			main_ui.design_near_death_can_move_var.set(False)
			main_ui.design_near_death_can_attack_spell_var.set(False)
		except Exception:
			pass
		main_ui._set_system_settings_dirty("design_global_near_death", True)
		if main_ui.design_global_status_var is not None:
			main_ui.design_global_status_var.set("已恢复默认（未应用）")
			main_ui.root.after(1800, lambda: main_ui.design_global_status_var.set(""))

	reset_btn = ttk.Button(btn_row, text="恢复默认", command=_reset_to_default)
	reset_btn.grid(row=0, column=3, sticky="e", padx=(8, 0))

	def _mark_dirty(*_args: Any) -> None:
		main_ui._set_system_settings_dirty("design_global_near_death", True)

	if "design_global_near_death" not in main_ui._system_settings_dirty_trace_bound_sections:
		for var in (
			main_ui.design_near_death_enabled_var,
			main_ui.design_near_death_revive_hp_var,
			main_ui.design_near_death_turns_to_die_var,
			main_ui.design_near_death_die_on_damage_var,
			main_ui.design_near_death_can_move_var,
			main_ui.design_near_death_can_attack_spell_var,
		):
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass
		main_ui._system_settings_dirty_trace_bound_sections.add("design_global_near_death")


def apply_design_global_near_death_settings(main_ui: Any, btn: ttk.Button) -> None:
	"""应用玩法设计->全局：濒死系统配置（跨局保持，直到手动关闭/再次应用）。"""
	try:
		btn.configure(state="disabled")
		enabled = bool(main_ui.design_near_death_enabled_var.get())
		revive_hp = main_ui._parse_int_or_none(main_ui.design_near_death_revive_hp_var.get())
		if revive_hp is None or revive_hp < 1:
			if main_ui.design_global_status_var is not None:
				main_ui.design_global_status_var.set("非法：恢复 HP 必须为 >=1 的整数")
				main_ui.root.after(1800, lambda: main_ui.design_global_status_var.set(""))
			return
		try:
			turns_to_die = int(main_ui.design_near_death_turns_to_die_var.get())
		except Exception:
			turns_to_die = 1
		turns_to_die = max(1, min(3, turns_to_die))
		die_on_damage = bool(main_ui.design_near_death_die_on_damage_var.get())
		can_move = bool(main_ui.design_near_death_can_move_var.get())
		can_act = bool(main_ui.design_near_death_can_attack_spell_var.get())

		config = {
			"near_death": {
				"enabled": enabled,
				"revive_hp_on_20": int(revive_hp),
				"turns_to_die": int(turns_to_die),
				"die_on_damage_when_dying": bool(die_on_damage),
				"can_move_when_dying": bool(can_move),
				"can_attack_or_spell_when_dying": bool(can_act),
			}
		}
		# 跨局保持：无论当前是否已加载 runtime env，都先保存到 UI 持久快照。
		try:
			main_ui._persistent_near_death_design_config = copy.deepcopy(config)
		except Exception:
			main_ui._persistent_near_death_design_config = dict(config)

		ok = main_ui._apply_near_death_config_to_runtime_environment(config)
		if main_ui.design_global_status_var is not None:
			if ok:
				main_ui.design_global_status_var.set("应用成功：濒死系统已注入（跨局保持）")
			else:
				main_ui.design_global_status_var.set("已保存：将在后续加载 runtime env 时自动生效")
			main_ui.root.after(1800, lambda: main_ui.design_global_status_var.set(""))
		main_ui._set_system_settings_dirty("design_global_near_death", False)
		try:
			if ok:
				main_ui.right_info_panel.append_content("\n[UI] 玩法设计-全局：濒死系统配置已应用（跨局保持）")
			else:
				main_ui.right_info_panel.append_content("\n[UI] 玩法设计-全局：濒死系统配置已保存（将对后续对局生效）")
		except Exception:
			pass
	finally:
		btn.configure(state="normal")
