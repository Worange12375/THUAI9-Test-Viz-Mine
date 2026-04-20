"""玩法设计-属性页 Service（Phase 4 拆分产物）。

本文件负责：
- 构建“系统设置 → 玩法设计 → 属性”页面（派生上限梯度 UI）。
- 管理梯度行的重建、默认值回填、错误高亮、应用到 runtime env。

不负责：
- 系统设置窗口的外层框架/导航；
- runtime hook 的具体实现（由 `runtime_hooks_service` 完成，本 service 只调用 MainUI 的薄封装）。

设计原则：搬家不改逻辑。
- 继续以 `main_ui` 实例作为上下文（访问其 vars、logger、helper）。
"""

from __future__ import annotations

import copy
from typing import Any

import tkinter as tk
from tkinter import ttk


def build_design_attribute_page(main_ui: Any, parent: ttk.Frame) -> None:
	"""玩法设计 -> 属性页面：属性派生上限梯度（最大行动位/最大法术位）。"""
	# 部分控件会在创建后的 idle 阶段写回 Variable；抑制该阶段的“写入即脏”。
	main_ui._suppress_system_settings_dirty_until_idle()
	# 该页内容可能较高（梯度数=7 时），因此只对“属性页”做有限高度滚动。
	parent.columnconfigure(0, weight=1)
	parent.rowconfigure(0, weight=1)
	parent.rowconfigure(1, weight=0)

	scroll_host = ttk.Frame(parent)
	scroll_host.grid(row=0, column=0, sticky="nsew")
	scroll_host.columnconfigure(0, weight=1)
	scroll_host.rowconfigure(0, weight=1)

	canvas = tk.Canvas(scroll_host, highlightthickness=0, borderwidth=0)
	v_scroll = ttk.Scrollbar(scroll_host, orient="vertical", command=canvas.yview)
	canvas.configure(yscrollcommand=v_scroll.set)
	canvas.grid(row=0, column=0, sticky="nsew")
	v_scroll.grid(row=0, column=1, sticky="ns")
	# 限制可视高度：约为原本“无滚动”体验的 1.5 倍（取一个稳定的固定值）。
	canvas.configure(height=520)

	body = ttk.Frame(canvas)
	canvas_window = canvas.create_window((0, 0), window=body, anchor="nw")
	body.columnconfigure(0, weight=1)

	def _sync_scroll_region(_event: Any = None) -> None:
		try:
			body.update_idletasks()
			req_w = int(body.winfo_reqwidth())
			req_h = int(body.winfo_reqheight())
			canvas.configure(scrollregion=(0, 0, max(req_w, 1), max(req_h, 1)))
		except Exception:
			canvas.configure(scrollregion=canvas.bbox("all"))

	def _fit_body_width(event: Any) -> None:
		try:
			canvas.itemconfigure(canvas_window, width=int(event.width))
		except Exception:
			pass

	def _on_mousewheel(event: Any) -> None:
		# 内容不足一屏时，不滚动；同时夹紧到顶/底，避免“无限滑动到空白”。
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
		if main_ui._design_attribute_mousewheel_bind_id is None:
			try:
				main_ui._design_attribute_mousewheel_bind_id = main_ui.root.bind_all(
					"<MouseWheel>", _on_mousewheel, add="+"
				)
			except Exception:
				main_ui._design_attribute_mousewheel_bind_id = None

	def _unbind_wheel_global() -> None:
		if main_ui._design_attribute_mousewheel_bind_id is not None:
			try:
				main_ui.root.unbind_all("<MouseWheel>", main_ui._design_attribute_mousewheel_bind_id)
			except Exception:
				pass
			main_ui._design_attribute_mousewheel_bind_id = None

	body.bind("<Configure>", _sync_scroll_region)
	canvas.bind("<Configure>", _fit_body_width)
	scroll_host.bind("<Enter>", lambda _e: _bind_wheel_global())
	scroll_host.bind("<Leave>", lambda _e: _unbind_wheel_global())

	ttk.Label(body, text="属性派生上限梯度", font=("Microsoft YaHei UI", 11, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)

	note = (
		"说明：这里编辑的是后端已实现的‘派生上限梯度’，默认值来自 dev_test 文档 talent_attributes.md。\n"
		"- 力量：最大行动位上限（<=13/21 → 1/2 else 3）\n"
		"- 智力：最大法术位上限（<=3/7/12/16/21 → 1/2/3/5/8 else 9）\n"
		"应用后仅本局生效：通过运行时 hook 覆写计算方式，不改后端文件。"
	)
	ttk.Label(body, text=note, justify="left", foreground="#4b5563").grid(row=1, column=0, sticky="nw", pady=(0, 8))

	block = ttk.LabelFrame(body, text="调整派生上限梯度", padding=10)
	block.grid(row=2, column=0, sticky="nsew")
	block.columnconfigure(0, weight=1)
	block.rowconfigure(0, weight=1)

	cols = ttk.Frame(block)
	cols.grid(row=0, column=0, sticky="nsew")
	for c in range(3):
		cols.columnconfigure(c, weight=1)

	def _build_one(stat_key: str, title: str, col_idx: int) -> None:
		frame = ttk.LabelFrame(cols, text=title, padding=8)
		frame.grid(row=0, column=col_idx, sticky="nsew", padx=(0, 10) if col_idx < 2 else 0)
		frame.columnconfigure(0, weight=1)

		row0 = ttk.Frame(frame)
		row0.grid(row=0, column=0, sticky="ew")
		row0.columnconfigure(0, weight=1)
		ttk.Label(row0, text="设置共", width=5).grid(row=0, column=0, sticky="w")
		spin = tk.Spinbox(
			row0,
			from_=1,
			to=7,
			width=3,
			textvariable=main_ui.design_talent_gradient_count_vars[stat_key],
		)
		spin.grid(row=0, column=1, sticky="w", padx=(6, 6))
		ttk.Label(row0, text="个梯度").grid(row=0, column=2, sticky="w")
		ttk.Button(
			row0,
			text="确定",
			width=4,
			command=lambda: main_ui._rebuild_talent_gradient_rows(stat_key),
		).grid(row=0, column=3, sticky="e", padx=(8, 0))

		rows = ttk.Frame(frame)
		rows.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
		rows.columnconfigure(0, weight=1)
		main_ui.design_talent_gradient_rows_frame[stat_key] = rows

		# 首次进入：注入默认值，并生成行（若已有残留但为空/不完整，也视为未初始化）。
		main_ui._ensure_one_talent_gradient_initialized(stat_key)

	_build_one("strength", "力量", 0)
	_build_one("dexterity", "敏捷", 1)
	_build_one("intelligence", "智力", 2)

	# 固定按钮行：不随滚动移动
	btn_row = ttk.Frame(parent)
	btn_row.grid(row=1, column=0, sticky="ew", pady=(10, 0))
	btn_row.columnconfigure(0, weight=1)
	if main_ui.design_attribute_status_var is None:
		main_ui.design_attribute_status_var = tk.StringVar(value="")
	ttk.Label(btn_row, textvariable=main_ui.design_attribute_status_var, foreground="#6b7280").grid(row=0, column=0, sticky="w")
	dirty_var = tk.StringVar(value="")
	try:
		main_ui._system_settings_dirty_label_vars["design_attribute"] = dirty_var
		dirty_var.set("（未应用）" if bool(main_ui._system_settings_dirty_flags.get("design_attribute", False)) else "")
	except Exception:
		pass
	ttk.Label(btn_row, textvariable=dirty_var, foreground="#b45309").grid(row=0, column=1, sticky="e", padx=(0, 8))
	apply_btn = ttk.Button(btn_row, text="应用", command=lambda: main_ui._apply_design_attribute_talent_gradients(apply_btn))
	apply_btn.grid(row=0, column=2, sticky="e")
	reset_btn = ttk.Button(btn_row, text="恢复默认", command=lambda: main_ui._reset_design_attribute_talent_gradients(reset_btn))
	reset_btn.grid(row=0, column=3, sticky="e", padx=(8, 0))

	def _mark_dirty(*_args: Any) -> None:
		main_ui._set_system_settings_dirty("design_attribute", True)

	if "design_attribute" not in main_ui._system_settings_dirty_trace_bound_sections:
		for var in main_ui.design_talent_gradient_count_vars.values():
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass
		main_ui._system_settings_dirty_trace_bound_sections.add("design_attribute")


def ensure_one_talent_gradient_initialized(main_ui: Any, stat_key: str) -> None:
	"""确保某个天赋梯度已初始化为合法默认值（首次进入/被格式化清空时兜底）。"""
	try:
		n = int(main_ui.design_talent_gradient_count_vars[stat_key].get())
	except Exception:
		n = 0
	old_th = main_ui.design_talent_gradient_threshold_vars.get(stat_key) or []
	old_val = main_ui.design_talent_gradient_value_vars.get(stat_key) or []
	complete = (
		1 <= n <= 7
		and len(old_val) == n
		and len(old_th) == max(0, n - 1)
		and all(str(v.get()).strip() != "" for v in old_val)
		and (n == 1 or all(str(v.get()).strip() != "" for v in old_th))
	)
	with main_ui._suppress_system_settings_dirty():
		if not complete:
			main_ui._reset_one_talent_gradient_to_default(stat_key)
			return
		main_ui._rebuild_talent_gradient_rows(stat_key, preserve_values=True)


def apply_design_attribute_talent_gradient_snapshot_to_vars(main_ui: Any, snapshot: dict[str, Any]) -> None:
	"""将已应用的派生上限梯度快照回填到 UI 变量（用于“丢弃未应用”回滚）。"""
	if not isinstance(snapshot, dict):
		return
	for stat_key in ("strength", "dexterity", "intelligence"):
		stat = snapshot.get(stat_key)
		if not isinstance(stat, dict):
			continue
		thresholds = stat.get("thresholds", [])
		values = stat.get("values", [])
		if not isinstance(thresholds, list) or not isinstance(values, list) or not values:
			continue
		main_ui.design_talent_gradient_count_vars[stat_key].set(len(values))
		main_ui.design_talent_gradient_threshold_vars[stat_key] = [tk.StringVar(value=str(x)) for x in thresholds]
		main_ui.design_talent_gradient_value_vars[stat_key] = [tk.StringVar(value=str(x)) for x in values]
		main_ui._rebuild_talent_gradient_rows(stat_key, preserve_values=True)


def clear_design_attribute_gradient_error_highlight(main_ui: Any) -> None:
	for stat_key in ("strength", "dexterity", "intelligence"):
		for entry in main_ui.design_talent_gradient_threshold_entries.get(stat_key, []):
			try:
				entry.configure(foreground="#111111")
			except Exception:
				pass
		for entry in main_ui.design_talent_gradient_value_entries.get(stat_key, []):
			try:
				entry.configure(foreground="#111111")
			except Exception:
				pass


def reset_one_talent_gradient_to_default(main_ui: Any, stat_key: str) -> None:
	default_thresholds = main_ui._DEFAULT_DERIVED_CAP_THRESHOLDS.get(stat_key, [])
	default_values = main_ui._DEFAULT_DERIVED_CAP_VALUES.get(stat_key, [0])
	main_ui.design_talent_gradient_count_vars[stat_key].set(len(default_values))
	main_ui.design_talent_gradient_threshold_vars[stat_key] = [tk.StringVar(value=str(x)) for x in default_thresholds]
	main_ui.design_talent_gradient_value_vars[stat_key] = [tk.StringVar(value=str(x)) for x in default_values]
	main_ui._rebuild_talent_gradient_rows(stat_key, preserve_values=True)


def reset_design_attribute_talent_gradients(main_ui: Any, btn: ttk.Button) -> None:
	try:
		btn.configure(state="disabled")
		main_ui._clear_design_attribute_gradient_error_highlight()
		for stat_key in ("strength", "dexterity", "intelligence"):
			main_ui._reset_one_talent_gradient_to_default(stat_key)
		if main_ui.design_attribute_status_var is not None:
			main_ui.design_attribute_status_var.set("已恢复默认（与 talent_attributes.md 一致）")
			main_ui.root.after(1500, lambda: main_ui.design_attribute_status_var.set(""))
		try:
			main_ui.right_info_panel.append_content("\n[UI] 玩法设计-属性：已恢复派生上限梯度默认值")
		except Exception:
			pass
	finally:
		btn.configure(state="normal")


def rebuild_talent_gradient_rows(main_ui: Any, stat_key: str, preserve_values: bool = True) -> None:
	rows = main_ui.design_talent_gradient_rows_frame.get(stat_key)
	if rows is None:
		return
	for w in rows.winfo_children():
		w.destroy()

	try:
		n = int(main_ui.design_talent_gradient_count_vars[stat_key].get())
	except Exception:
		n = 4
	n = max(1, min(7, n))
	main_ui.design_talent_gradient_count_vars[stat_key].set(n)

	old_th_vars = main_ui.design_talent_gradient_threshold_vars.get(stat_key, [])
	old_val_vars = main_ui.design_talent_gradient_value_vars.get(stat_key, [])
	new_th_vars: list[tk.StringVar] = []
	new_val_vars: list[tk.StringVar] = []

	for i in range(max(0, n - 1)):
		v = tk.StringVar(value="")
		if preserve_values and i < len(old_th_vars):
			try:
				v.set(str(old_th_vars[i].get()))
			except Exception:
				pass
		try:
			v.trace_add("write", lambda *_a: main_ui._set_system_settings_dirty("design_attribute", True))
		except Exception:
			pass
		new_th_vars.append(v)
	for i in range(n):
		v = tk.StringVar(value="")
		if preserve_values and i < len(old_val_vars):
			try:
				v.set(str(old_val_vars[i].get()))
			except Exception:
				pass
		try:
			v.trace_add("write", lambda *_a: main_ui._set_system_settings_dirty("design_attribute", True))
		except Exception:
			pass
		new_val_vars.append(v)

	main_ui.design_talent_gradient_threshold_vars[stat_key] = new_th_vars
	main_ui.design_talent_gradient_value_vars[stat_key] = new_val_vars
	main_ui.design_talent_gradient_threshold_entries[stat_key] = []
	main_ui.design_talent_gradient_value_entries[stat_key] = []

	for i in range(n):
		row = ttk.Frame(rows)
		row.grid(row=i, column=0, sticky="ew", pady=(0, 6))
		row.columnconfigure(3, weight=1)
		if i < n - 1:
			ttk.Label(row, text="<=", width=3).grid(row=0, column=0, sticky="w")
			th_entry = ttk.Entry(row, textvariable=new_th_vars[i], width=6)
			th_entry.grid(row=0, column=1, sticky="w")
			main_ui.design_talent_gradient_threshold_entries[stat_key].append(th_entry)
		else:
			ttk.Label(row, text="else", width=4).grid(row=0, column=0, sticky="w")
			ttk.Label(row, text="", width=1).grid(row=0, column=1, sticky="w")
		ttk.Label(row, text=">>>", width=4).grid(row=0, column=2, sticky="w", padx=(8, 8))
		val_entry = ttk.Entry(row, textvariable=new_val_vars[i], width=6)
		val_entry.grid(row=0, column=3, sticky="w")
		main_ui.design_talent_gradient_value_entries[stat_key].append(val_entry)


def apply_design_attribute_talent_gradients(main_ui: Any, btn: ttk.Button) -> None:
	try:
		btn.configure(state="disabled")
		main_ui._clear_design_attribute_gradient_error_highlight()
		config: dict[str, dict[str, list[int]]] = {}

		for stat_key in ("strength", "dexterity", "intelligence"):
			try:
				n = int(main_ui.design_talent_gradient_count_vars[stat_key].get())
			except Exception:
				n = 0
			if n < 1 or n > 7:
				if main_ui.design_attribute_status_var is not None:
					main_ui.design_attribute_status_var.set("非法：梯度数范围应为 1-7")
				return

			thresholds: list[int] = []
			values: list[int] = []
			for i in range(max(0, n - 1)):
				v = main_ui._parse_int_or_none(main_ui.design_talent_gradient_threshold_vars[stat_key][i].get())
				if v is None:
					try:
						main_ui.design_talent_gradient_threshold_entries[stat_key][i].configure(foreground="#dc2626")
					except Exception:
						pass
					if main_ui.design_attribute_status_var is not None:
						main_ui.design_attribute_status_var.set("非法：梯度阈值必须为整数")
					return
				thresholds.append(int(v))
			for i in range(n):
				v = main_ui._parse_int_or_none(main_ui.design_talent_gradient_value_vars[stat_key][i].get())
				if v is None:
					try:
						main_ui.design_talent_gradient_value_entries[stat_key][i].configure(foreground="#dc2626")
					except Exception:
						pass
					if main_ui.design_attribute_status_var is not None:
						main_ui.design_attribute_status_var.set("非法：对应取值必须为整数")
					return
				values.append(int(v))

			if n > 1:
				if thresholds[0] < 1:
					try:
						main_ui.design_talent_gradient_threshold_entries[stat_key][0].configure(foreground="#dc2626")
					except Exception:
						pass
					if main_ui.design_attribute_status_var is not None:
						main_ui.design_attribute_status_var.set("非法：最上方梯度阈值应 >= 1")
					return
				for i in range(1, len(thresholds)):
					if thresholds[i] <= thresholds[i - 1]:
						try:
							main_ui.design_talent_gradient_threshold_entries[stat_key][i].configure(foreground="#dc2626")
						except Exception:
							pass
						if main_ui.design_attribute_status_var is not None:
							main_ui.design_attribute_status_var.set("非法：梯度阈值需自上而下严格递增")
						return
			if values[0] < 0:
				try:
					main_ui.design_talent_gradient_value_entries[stat_key][0].configure(foreground="#dc2626")
				except Exception:
					pass
				if main_ui.design_attribute_status_var is not None:
					main_ui.design_attribute_status_var.set("非法：第一行对应取值应 >= 0")
				return
			for i in range(1, len(values)):
				if values[i] <= values[i - 1]:
					try:
						main_ui.design_talent_gradient_value_entries[stat_key][i].configure(foreground="#dc2626")
					except Exception:
						pass
					if main_ui.design_attribute_status_var is not None:
						main_ui.design_attribute_status_var.set("非法：对应取值需自上而下严格递增")
					return

			config[stat_key] = {"thresholds": thresholds, "values": values}

		ok = main_ui._apply_talent_gradient_config_to_runtime_environment(config)
		if not ok:
			if main_ui.design_attribute_status_var is not None:
				main_ui.design_attribute_status_var.set("未生效：当前未加载 runtime env")
			return
		# 保存“已应用快照”，用于关闭窗口时丢弃未应用修改的 UI 回滚。
		try:
			main_ui._applied_design_attribute_talent_gradients_snapshot = copy.deepcopy(config)
		except Exception:
			main_ui._applied_design_attribute_talent_gradients_snapshot = dict(config)
		if main_ui.design_attribute_status_var is not None:
			main_ui.design_attribute_status_var.set("应用成功：派生上限梯度已注入（本局生效）")
			main_ui.root.after(1800, lambda: main_ui.design_attribute_status_var.set(""))
		main_ui._set_system_settings_dirty("design_attribute", False)
		try:
			main_ui.right_info_panel.append_content("\n[UI] 玩法设计-属性：派生上限梯度已应用（本局临时生效）")
		except Exception:
			pass
	finally:
		btn.configure(state="normal")
