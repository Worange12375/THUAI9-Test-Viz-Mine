"""玩法设计-法术页 Service（Phase 4 拆分产物）。

本文件负责：
- 构建“系统设置 → 玩法设计 → 法术”页面（法术池优先级表格）。
- 管理测试端/后端实现切换、优先级解析、应用到 runtime env（跨局保持）。

不负责：
- runtime hook 的具体实现（由 `runtime_hooks_service` 完成，本 service 只调用 MainUI 的薄封装）。
- 行动页法术 UI 的渲染（由 action_spell_service 等负责）。

设计原则：搬家不改逻辑。
"""

from __future__ import annotations

import copy
from types import SimpleNamespace
from typing import Any

import tkinter as tk
from tkinter import ttk

from env import SpellFactory


def build_design_spell_pool_page(main_ui: Any, parent: ttk.Frame) -> None:
	"""玩法设计 -> 法术：法术池配置（职业×法术优先级）。"""
	# 部分控件会在创建后的 idle 阶段写回 Variable；抑制该阶段的“写入即脏”。
	main_ui._suppress_system_settings_dirty_until_idle()
	parent.columnconfigure(0, weight=1)
	# header 固定；滚动区占剩余空间；按钮行固定。
	parent.rowconfigure(0, weight=0)
	parent.rowconfigure(1, weight=1)
	parent.rowconfigure(2, weight=0)

	header = ttk.Frame(parent)
	header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
	header.columnconfigure(0, weight=1)
	ttk.Label(header, text="法术池配置", font=("Microsoft YaHei UI", 11, "bold")).grid(row=0, column=0, sticky="w")
	ttk.Checkbutton(
		header,
		text="启用测试端法术默认实现（实时生效）",
		variable=main_ui.design_spell_use_test_impl_var,
	).grid(row=0, column=1, sticky="e")

	# 内容可能随未来法术扩展而变高：使用自适应高度滚动容器。
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

	note_var = tk.StringVar(value="")
	note_label = ttk.Label(body, textvariable=note_var, justify="left", foreground="#4b5563")
	note_label.grid(row=0, column=0, sticky="nw")

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

	def _fit_body_width(event: Any) -> None:
		try:
			w = int(event.width)
		except Exception:
			w = 0
		try:
			canvas.itemconfigure(canvas_window, width=max(w, 1))
		except Exception:
			pass
		wrap = max(240, w - 40)
		try:
			note_label.configure(wraplength=wrap)
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
		if main_ui._design_spell_mousewheel_bind_id is None:
			try:
				main_ui._design_spell_mousewheel_bind_id = main_ui.root.bind_all("<MouseWheel>", _on_mousewheel, add="+")
			except Exception:
				main_ui._design_spell_mousewheel_bind_id = None

	def _unbind_wheel_global() -> None:
		if main_ui._design_spell_mousewheel_bind_id is not None:
			try:
				main_ui.root.unbind_all("<MouseWheel>", main_ui._design_spell_mousewheel_bind_id)
			except Exception:
				pass
			main_ui._design_spell_mousewheel_bind_id = None

	body.bind("<Configure>", _sync_scroll_region)
	canvas.bind("<Configure>", _fit_body_width)
	scroll_host.bind("<Enter>", lambda _e: _bind_wheel_global())
	scroll_host.bind("<Leave>", lambda _e: _unbind_wheel_global())

	def _normalize_spell_key(name: str) -> str:
		key = str(name or "").strip().lower()
		key = key.replace(" ", "")
		if key in ("arrowhit", "arrow_hit"):
			return "arrow_hit"
		if key == "fireball":
			return "fireball"
		if key == "trap":
			return "trap"
		if key == "heal":
			return "heal"
		if key in ("teleport", "move"):
			return "teleport"
		return key

	# 纵轴法术顺序按产品定义固定（从上到下）：
	# 箭击、陷阱、治愈、瞬移、火球。
	# 未来若加入新法术：在此处追加到 SPELL_ROWS（暂不在 UI 中显示，先保留代码注释入口）。
	SPELL_ROWS: list[tuple[str, str]] = [
		("arrow_hit", "箭击"),
		("trap", "陷阱"),
		("heal", "治愈"),
		("teleport", "瞬移"),
		("fireball", "火球"),
	]
	# 横轴职业：战士拆分长/短。
	PROF_COLS: list[tuple[str, str]] = [
		("WarriorLong", "战士(长)"),
		("WarriorShort", "战士(短)"),
		("Archer", "弓箭手"),
		("Mage", "法师"),
	]

	def _get_test_default_priority_map() -> dict[str, dict[str, int]]:
		base: dict[str, dict[str, int]] = {k: {sk: 0 for sk, _t in SPELL_ROWS} for k, _t2 in PROF_COLS}
		# 数字越小优先级越高：越先进入法术池。
		base["WarriorLong"]["arrow_hit"] = 1
		base["WarriorLong"]["heal"] = 2
		base["WarriorShort"]["trap"] = 1
		base["WarriorShort"]["heal"] = 2
		base["Archer"]["arrow_hit"] = 1
		base["Archer"]["trap"] = 2
		base["Mage"]["arrow_hit"] = 1
		base["Mage"]["trap"] = 2
		base["Mage"]["heal"] = 3
		base["Mage"]["teleport"] = 4
		base["Mage"]["fireball"] = 5
		return base

	def _get_backend_default_priority_map() -> dict[str, dict[str, int]]:
		base: dict[str, dict[str, int]] = {k: {sk: 0 for sk, _t in SPELL_ROWS} for k, _t2 in PROF_COLS}
		# 后端实现目前不区分战士长/短：两者都用 Warrior 的默认池展示。
		prof_type_map = {
			"WarriorLong": "Warrior",
			"WarriorShort": "Warrior",
			"Archer": "Archer",
			"Mage": "Mage",
		}
		for prof_key, piece_type in prof_type_map.items():
			selected: list[str] = []
			try:
				dummy = SimpleNamespace(type=piece_type, intelligence=999)
				for sp in SpellFactory.get_available_spells(dummy):
					selected.append(_normalize_spell_key(str(getattr(sp, "name", ""))))
			except Exception:
				selected = []
			# 展示用优先级：按固定纵轴顺序从 1 开始依次编号。
			chosen = {k for k in selected if k}
			pri = 1
			for sk, _t in SPELL_ROWS:
				if sk in chosen:
					base[prof_key][sk] = pri
					pri += 1
				else:
					base[prof_key][sk] = 0
		return base

	def _ensure_priority_vars_structure() -> None:
		if not isinstance(getattr(main_ui, "design_spell_priority_vars", None), dict):
			main_ui.design_spell_priority_vars = {}
		for prof_key, _pt in PROF_COLS:
			row = main_ui.design_spell_priority_vars.setdefault(prof_key, {})
			if not isinstance(row, dict):
				main_ui.design_spell_priority_vars[prof_key] = {}
				row = main_ui.design_spell_priority_vars[prof_key]
			for spell_key, _st in SPELL_ROWS:
				if spell_key not in row or not isinstance(row.get(spell_key), tk.StringVar):
					row[spell_key] = tk.StringVar(value="0")

	def _set_priority_vars_from_map(m: dict[str, dict[str, int]]) -> None:
		with main_ui._suppress_system_settings_dirty():
			for prof_key, _pt in PROF_COLS:
				row_vars = main_ui.design_spell_priority_vars.setdefault(prof_key, {})
				for spell_key, _st in SPELL_ROWS:
					val = 0
					try:
						val = int(m.get(prof_key, {}).get(spell_key, 0))
					except Exception:
						val = 0
					try:
						row_vars[spell_key].set(str(val))
					except Exception:
						pass

	def _collect_priority_cache_from_vars() -> dict[str, dict[str, str]]:
		out: dict[str, dict[str, str]] = {}
		for prof_key, _pt in PROF_COLS:
			row_out: dict[str, str] = {}
			row_vars = main_ui.design_spell_priority_vars.get(prof_key, {})
			for spell_key, _st in SPELL_ROWS:
				try:
					row_out[spell_key] = str(row_vars.get(spell_key).get()).strip()
				except Exception:
					row_out[spell_key] = "0"
			out[prof_key] = row_out
		return out

	def _restore_priority_vars_from_cache(cache: dict[str, dict[str, str]] | None) -> None:
		if not isinstance(cache, dict):
			return
		with main_ui._suppress_system_settings_dirty():
			for prof_key, _pt in PROF_COLS:
				row_vars = main_ui.design_spell_priority_vars.setdefault(prof_key, {})
				cached_row = cache.get(prof_key, {}) if isinstance(cache.get(prof_key, {}), dict) else {}
				for spell_key, _st in SPELL_ROWS:
					val = str(cached_row.get(spell_key, "0")).strip()
					try:
						row_vars[spell_key].set(val)
					except Exception:
						pass

	# 应用“持久配置”的 use_test 标志（该标志是实时生效的，不绑定应用按钮）。
	cfg = getattr(main_ui, "_persistent_spell_pool_design_config", None)
	if isinstance(cfg, dict) and "use_test_spell_impl" in cfg:
		try:
			main_ui.design_spell_use_test_impl_var.set(bool(cfg.get("use_test_spell_impl", True)))
		except Exception:
			pass

	_ensure_priority_vars_structure()
	# 初始化：优先从持久配置恢复（上次“应用”的测试端优先级）；否则走测试端默认。
	if not main_ui.design_spell_priority_vars or all(not v for v in main_ui.design_spell_priority_vars.values()):
		main_ui.design_spell_priority_vars = {}
		_ensure_priority_vars_structure()
	try:
		stored = cfg.get("spell_priorities", None) if isinstance(cfg, dict) else None
	except Exception:
		stored = None
	if isinstance(stored, dict) and stored:
		# 仅按已存 key 写入，其余补 0。
		with main_ui._suppress_system_settings_dirty():
			for prof_key, _pt in PROF_COLS:
				row_vars = main_ui.design_spell_priority_vars.setdefault(prof_key, {})
				mrow = stored.get(prof_key, {}) if isinstance(stored.get(prof_key, {}), dict) else {}
				for spell_key, _st in SPELL_ROWS:
					val = str(mrow.get(spell_key, "0")).strip()
					try:
						row_vars[spell_key].set(val)
					except Exception:
						pass
	else:
		_set_priority_vars_from_map(_get_test_default_priority_map())

	# 初始化测试端缓存：用于在“走后端实现”与“测试端实现”之间来回切换。
	if main_ui._spell_priority_cache_when_test_impl_enabled is None:
		main_ui._spell_priority_cache_when_test_impl_enabled = _collect_priority_cache_from_vars()

	# 依据当前模式决定表格显示内容。
	if not bool(main_ui.design_spell_use_test_impl_var.get()):
		# 走后端实现：展示后端默认配置（组件禁用）
		_set_priority_vars_from_map(_get_backend_default_priority_map())
	else:
		# 测试端实现：展示缓存的优先级表
		_restore_priority_vars_from_cache(main_ui._spell_priority_cache_when_test_impl_enabled)

	table = ttk.LabelFrame(body, text="法术池配置（优先级 0 / 1~5，数字越小越优先）", padding=10)
	table.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
	table.columnconfigure(0, weight=0)
	for cidx in range(1, len(PROF_COLS) + 1):
		table.columnconfigure(cidx, weight=1)

	ttk.Label(table, text="法术", width=10).grid(row=0, column=0, sticky="w")
	for cidx, (_prof_key, title) in enumerate(PROF_COLS, start=1):
		ttk.Label(table, text=title, width=10).grid(row=0, column=cidx, sticky="w")

	def _mark_dirty(*_args: Any) -> None:
		main_ui._set_system_settings_dirty("design_spell_pool", True)

	entries: list[ttk.Entry] = []
	for ridx, (spell_key, spell_title) in enumerate(SPELL_ROWS, start=1):
		ttk.Label(table, text=spell_title, width=10).grid(row=ridx, column=0, sticky="w")
		for cidx, (prof_key, _prof_title) in enumerate(PROF_COLS, start=1):
			row_vars = main_ui.design_spell_priority_vars.setdefault(prof_key, {})
			var = row_vars.get(spell_key)
			if var is None or not isinstance(var, tk.StringVar):
				var = tk.StringVar(value="0")
				row_vars[spell_key] = var
			entry = ttk.Entry(table, textvariable=var, width=4)
			entry.grid(row=ridx, column=cidx, sticky="w")
			entries.append(entry)
			try:
				entry.bind("<KeyRelease>", lambda _e, _md=_mark_dirty: _md())
				entry.bind("<FocusOut>", lambda _e, _md=_mark_dirty: _md())
			except Exception:
				pass
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass

	# 固定按钮行：不随滚动移动
	btn_row = ttk.Frame(parent)
	btn_row.grid(row=2, column=0, sticky="ew", pady=(10, 0))
	btn_row.columnconfigure(0, weight=1)
	status_var = tk.StringVar(value="")
	ttk.Label(btn_row, textvariable=status_var, foreground="#6b7280").grid(row=0, column=0, sticky="w")
	dirty_var = tk.StringVar(value="")
	try:
		main_ui._system_settings_dirty_label_vars["design_spell_pool"] = dirty_var
		dirty_var.set("（未应用）" if bool(main_ui._system_settings_dirty_flags.get("design_spell_pool", False)) else "")
	except Exception:
		pass
	ttk.Label(btn_row, textvariable=dirty_var, foreground="#b45309").grid(row=0, column=1, sticky="e", padx=(0, 8))

	def _parse_priorities_from_vars() -> dict[str, dict[str, int]] | None:
		out: dict[str, dict[str, int]] = {}
		for prof_key, _pt in PROF_COLS:
			row_out: dict[str, int] = {}
			row_vars = main_ui.design_spell_priority_vars.get(prof_key, {})
			for spell_key, _st in SPELL_ROWS:
				raw = ""
				try:
					raw = str(row_vars.get(spell_key).get()).strip()
				except Exception:
					raw = ""
				if raw == "":
					val = 0
				else:
					try:
						val = int(raw)
					except Exception:
						status_var.set("非法：优先级只能填写 0 或 1~5（数字越小越优先）")
						main_ui.root.after(1800, lambda: status_var.set(""))
						return None
				if val < 0 or val > 5:
					status_var.set("非法：优先级范围为 0 或 1~5")
					main_ui.root.after(1800, lambda: status_var.set(""))
					return None
				row_out[spell_key] = int(val)
			out[prof_key] = row_out
		return out

	def _apply() -> None:
		if not bool(main_ui.design_spell_use_test_impl_var.get()):
			status_var.set("当前走后端实现：无法应用测试端配置")
			main_ui.root.after(1800, lambda: status_var.set(""))
			return
		priorities = _parse_priorities_from_vars()
		if priorities is None:
			return
		config = getattr(main_ui, "_persistent_spell_pool_design_config", None)
		if not isinstance(config, dict):
			config = {}
		config["use_test_spell_impl"] = True
		config["spell_priorities"] = copy.deepcopy(priorities)
		try:
			main_ui._persistent_spell_pool_design_config = copy.deepcopy(config)
		except Exception:
			main_ui._persistent_spell_pool_design_config = dict(config)
		ok = main_ui._apply_spell_pool_config_to_runtime_environment(config)
		if ok:
			status_var.set("应用成功：测试端法术池已注入（跨局保持）")
			main_ui.right_info_panel.append_content("\n[UI] 玩法设计-法术：测试端法术池配置已应用（跨局保持）")
		else:
			status_var.set("已保存：将在后续加载 runtime env 时自动生效")
			main_ui.right_info_panel.append_content("\n[UI] 玩法设计-法术：测试端法术池配置已保存（将对后续对局生效）")
		# 更新缓存为“已应用”表格值（便于来回切换）。
		try:
			main_ui._spell_priority_cache_when_test_impl_enabled = _collect_priority_cache_from_vars()
		except Exception:
			pass
		main_ui.root.after(1800, lambda: status_var.set(""))
		main_ui._set_system_settings_dirty("design_spell_pool", False)

	def _reset_to_test_default() -> None:
		# 恢复默认：测试端独立默认法术池（不跟随后端实现）
		_set_priority_vars_from_map(_get_test_default_priority_map())
		# 更新缓存（但不落地应用）
		try:
			main_ui._spell_priority_cache_when_test_impl_enabled = _collect_priority_cache_from_vars()
		except Exception:
			pass
		main_ui._set_system_settings_dirty("design_spell_pool", True)
		status_var.set("已恢复默认（未应用）")
		main_ui.root.after(1800, lambda: status_var.set(""))

	apply_btn = ttk.Button(btn_row, text="应用", command=_apply)
	apply_btn.grid(row=0, column=2, sticky="e")
	reset_btn = ttk.Button(btn_row, text="恢复默认", command=_reset_to_test_default)
	reset_btn.grid(row=0, column=3, sticky="e", padx=(8, 0))

	def _set_widgets_enabled(enabled: bool) -> None:
		state = "normal" if enabled else "disabled"
		try:
			for e in entries:
				e.configure(state=state)
		except Exception:
			pass
		try:
			apply_btn.configure(state=state)
		except Exception:
			pass
		try:
			reset_btn.configure(state=state)
		except Exception:
			pass

	def _update_note_text() -> None:
		if bool(main_ui.design_spell_use_test_impl_var.get()):
			note_var.set(
				"说明：这里用于配置各职业可用的法术池（测试端独立实现，不改后端文件）。\n"
				"- 表格填优先级：0=不选；1~5=优先级（数字越小优先级越高）。\n"
				"- 点击“应用”后：本局与后续对局生效。\n"
				"- 行动中法术下拉框可选：按优先级选出前 N 个法术。\n"
				"  N 的计算：非法师 N=intelligence//4 + 1；法师 N=2*(intelligence//4)+1。"
			)
		else:
			note_var.set(
				"当前未启用测试端法术实现：将走后端 SpellFactory.get_available_spells。\n"
				"- 本页表格仅展示后端默认职业-法术池配置，且不可编辑。\n"
				"- 后端当前规则（供对照）：可用法术数 = intelligence//5 + 1。"
			)

	def _apply_toggle_immediately() -> None:
		enabled = bool(main_ui.design_spell_use_test_impl_var.get())
		# 更新持久配置中的开关（实时生效，不走 apply 按钮）
		config = getattr(main_ui, "_persistent_spell_pool_design_config", None)
		if not isinstance(config, dict):
			config = {}
		config["use_test_spell_impl"] = bool(enabled)
		# 切换显示/可交互性
		if enabled:
			# 恢复测试端表格值
			_restore_priority_vars_from_cache(main_ui._spell_priority_cache_when_test_impl_enabled)
		else:
			# 保存当前测试端表格值到缓存，并展示后端默认
			try:
				main_ui._spell_priority_cache_when_test_impl_enabled = _collect_priority_cache_from_vars()
			except Exception:
				pass
			_set_priority_vars_from_map(_get_backend_default_priority_map())
		try:
			main_ui._persistent_spell_pool_design_config = copy.deepcopy(config)
		except Exception:
			main_ui._persistent_spell_pool_design_config = dict(config)
		_set_widgets_enabled(bool(enabled))
		_update_note_text()
		# 立即对当前 runtime env 生效（若未加载则只保存，后续自动重应用）。
		ok = main_ui._apply_spell_pool_config_to_runtime_environment(config)
		if enabled:
			status_var.set("已启用：测试端法术实现（即时生效）" if ok else "已启用：将在后续加载 runtime env 时生效")
		else:
			status_var.set("已关闭：走后端法术实现（即时生效）" if ok else "已关闭：将在后续加载 runtime env 时生效")
		main_ui.root.after(1800, lambda: status_var.set(""))

	# 初次渲染时同步一次 UI 状态。
	_update_note_text()
	_set_widgets_enabled(bool(main_ui.design_spell_use_test_impl_var.get()))
	# 绑定实时开关（仅一次，避免切页重复 trace 导致回调叠加）
	if not bool(getattr(main_ui, "_design_spell_use_test_impl_trace_bound", False)):
		try:
			main_ui.design_spell_use_test_impl_var.trace_add("write", lambda *_a: _apply_toggle_immediately())
			main_ui._design_spell_use_test_impl_trace_bound = True
		except Exception:
			pass
