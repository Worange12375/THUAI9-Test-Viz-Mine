"""System settings -> General page service.

职责：
- 构建“系统设置窗口 -> 综合设置（general）”页面 UI。
- 采集并应用设置：右侧信息展示区（类别显示/颜色）与 d20 投掷结果强制。
- 提供“已应用快照”的采集与回填，用于关闭窗口时丢弃未应用修改。

边界：
- 不负责系统设置窗口的外壳/导航切页（由 main_ui 负责）。
- 不负责 RightInfoPanel 的实现细节；仅调用其公开接口。
- 不引入新 UX，仅做代码搬家与薄委托。

对外接口：
- build_system_settings_general_page(main_ui, parent)
- apply_system_general_settings(main_ui, apply_btn, status_var)
- collect_system_general_settings_snapshot_from_vars(main_ui)
- apply_system_general_settings_snapshot_to_vars(main_ui, snapshot)
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from logic.test_mock_gameplay import ensure_d20_force_installed


def collect_system_general_settings_snapshot_from_vars(main_ui: object) -> dict[str, Any]:
	"""采集综合设置页变量快照（用于回滚/重开窗口保持一致性）。"""
	visibility: dict[str, bool] = {}
	colors: dict[str, str] = {}
	force_flags: dict[str, bool] = {}
	force_values: dict[str, str] = {}
	try:
		for k, v in getattr(main_ui, "right_info_category_visibility_vars", {}).items():
			try:
				visibility[str(k)] = bool(v.get())
			except Exception:
				visibility[str(k)] = False
	except Exception:
		pass
	try:
		for k, v in getattr(main_ui, "right_info_category_color_vars", {}).items():
			try:
				colors[str(k)] = str(v.get())
			except Exception:
				colors[str(k)] = ""
	except Exception:
		pass
	try:
		for k, v in getattr(main_ui, "system_force_d20_vars", {}).items():
			try:
				force_flags[str(k)] = bool(v.get())
			except Exception:
				force_flags[str(k)] = False
	except Exception:
		pass
	try:
		for k, v in getattr(main_ui, "system_force_d20_value_vars", {}).items():
			try:
				force_values[str(k)] = str(v.get())
			except Exception:
				force_values[str(k)] = ""
	except Exception:
		pass
	return {
		"visibility": visibility,
		"colors": colors,
		"force_flags": force_flags,
		"force_values": force_values,
	}


def apply_system_general_settings_snapshot_to_vars(main_ui: object, snapshot: dict[str, Any]) -> None:
	if not isinstance(snapshot, dict):
		return
	vis = snapshot.get("visibility")
	cols = snapshot.get("colors")
	flags = snapshot.get("force_flags")
	vals = snapshot.get("force_values")
	try:
		if isinstance(vis, dict):
			for k, value in vis.items():
				var = getattr(main_ui, "right_info_category_visibility_vars", {}).get(k)
				if var is not None:
					try:
						var.set(bool(value))
					except Exception:
						pass
	except Exception:
		pass
	try:
		if isinstance(cols, dict):
			for k, value in cols.items():
				var = getattr(main_ui, "right_info_category_color_vars", {}).get(k)
				if var is not None:
					try:
						var.set(str(value))
					except Exception:
						pass
	except Exception:
		pass
	try:
		if isinstance(flags, dict):
			for k, value in flags.items():
				var = getattr(main_ui, "system_force_d20_vars", {}).get(k)
				if var is not None:
					try:
						var.set(bool(value))
					except Exception:
						pass
	except Exception:
		pass
	try:
		if isinstance(vals, dict):
			for k, value in vals.items():
				var = getattr(main_ui, "system_force_d20_value_vars", {}).get(k)
				if var is not None:
					try:
						var.set(str(value))
					except Exception:
						pass
	except Exception:
		pass


def build_system_settings_general_page(main_ui: object, parent: ttk.LabelFrame) -> None:
	wrapper = ttk.Frame(parent)
	wrapper.grid(row=0, column=0, sticky="nsew")
	wrapper.columnconfigure(0, weight=1)
	wrapper.rowconfigure(3, weight=1)

	intro = (
		"这里用于配置测试端 UI/显示/调试能力等“仅测试端生效”的设置。\n"
		"当前先落地：右侧信息展示区的“按类别显示/隐藏”。\n\n"
		"提示：后续可能接入权限系统，不同权限可见/可改项不同。"
	)
	ttk.Label(wrapper, text="综合设置", font=("Microsoft YaHei UI", 12, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)
	ttk.Label(wrapper, text=intro, justify="left", foreground="#4b5563").grid(row=1, column=0, sticky="nw")

	boxes = ttk.Frame(wrapper)
	boxes.grid(row=2, column=0, sticky="ew", pady=(12, 0))
	boxes.columnconfigure(0, weight=1)
	boxes.columnconfigure(1, weight=1)

	group = ttk.LabelFrame(boxes, text="右侧信息展示区：文字显示设置", padding=10)
	group.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
	group.columnconfigure(0, weight=1)

	reserve = ttk.LabelFrame(boxes, text="投掷结果设置", padding=10)
	reserve.grid(row=0, column=1, sticky="nsew")
	reserve.columnconfigure(0, weight=1)

	reserve_intro = (
		"用于测试：将特定的 d20 投掷强制为固定点数（1~20）。\n"
		"仅测试端覆盖返回值，不改后端投掷算法。"
	)
	ttk.Label(reserve, text=reserve_intro, justify="left", foreground="#4b5563").grid(row=0, column=0, sticky="nw")

	for idx, (key, label) in enumerate(getattr(main_ui, "_D20_FORCE_OPTIONS"), start=1):
		row = ttk.Frame(reserve)
		row.grid(row=idx, column=0, sticky="ew", pady=(8 if idx == 1 else 6, 0))
		row.columnconfigure(0, weight=1)
		ttk.Label(row, text=label).grid(row=0, column=0, sticky="w")
		entry = ttk.Entry(row, textvariable=getattr(main_ui, "system_force_d20_value_vars")[key], width=4, state="disabled")
		entry.grid(row=0, column=1, padx=(8, 6), sticky="e")
		cb = ttk.Checkbutton(row, variable=getattr(main_ui, "system_force_d20_vars")[key])
		cb.grid(row=0, column=2, sticky="e")

		def _sync_entry_state(*_args: Any, _k: str = key, _e: ttk.Entry = entry) -> None:
			try:
				enabled = bool(getattr(main_ui, "system_force_d20_vars")[_k].get())
			except Exception:
				enabled = False
			try:
				_e.configure(state="normal" if enabled else "disabled")
			except Exception:
				pass

		try:
			getattr(main_ui, "system_force_d20_vars")[key].trace_add("write", _sync_entry_state)
		except Exception:
			pass
		_sync_entry_state()

	header = ttk.Frame(group)
	header.grid(row=0, column=0, sticky="ew")
	header.columnconfigure(0, weight=1)
	header.columnconfigure(1, weight=1)
	header.columnconfigure(2, weight=1)
	ttk.Label(header, text="类别", width=6).grid(row=0, column=0)
	ttk.Label(header, text="是否显示", width=10).grid(row=0, column=1, padx=(10, 0))
	ttk.Label(header, text="颜色（预留）", width=12).grid(row=0, column=2, padx=(10, 0))

	color_options = ["黑色", "灰色", "红色", "橙色", "绿色", "蓝色"]
	rows = [
		("important", "重要"),
		("round", "回合"),
		("player", "玩家"),
		("system", "系统"),
		("default", "默认"),
	]
	for idx, (key, label) in enumerate(rows, start=1):
		row = ttk.Frame(group)
		row.grid(row=idx, column=0, sticky="ew", pady=(6, 0))
		row.columnconfigure(0, weight=1)
		row.columnconfigure(1, weight=1)
		row.columnconfigure(2, weight=1)
		ttk.Label(row, text=label, width=6).grid(row=0, column=0)
		ttk.Checkbutton(row, variable=getattr(main_ui, "right_info_category_visibility_vars")[key]).grid(
			row=0, column=1, padx=(5, 0)
		)
		combo = ttk.Combobox(
			row,
			values=color_options,
			textvariable=getattr(main_ui, "right_info_category_color_vars")[key],
			state="readonly",
			width=12,
		)
		combo.grid(row=0, column=2, padx=(20, 0))

	btn_row = ttk.Frame(wrapper)
	btn_row.grid(row=3, column=0, sticky="ew", pady=(12, 0))
	btn_row.columnconfigure(0, weight=1)
	status_var = tk.StringVar(value="")
	status_label = ttk.Label(btn_row, textvariable=status_var, foreground="#6b7280")
	status_label.grid(row=0, column=0, sticky="w")
	dirty_var = tk.StringVar(value="")
	try:
		getattr(main_ui, "_system_settings_dirty_label_vars")["general"] = dirty_var
		dirty_var.set("（未应用）" if bool(getattr(main_ui, "_system_settings_dirty_flags").get("general", False)) else "")
	except Exception:
		pass
	ttk.Label(btn_row, textvariable=dirty_var, foreground="#b45309").grid(row=0, column=1, sticky="e", padx=(0, 8))

	apply_btn = ttk.Button(
		btn_row, text="应用", command=lambda: getattr(main_ui, "_apply_system_general_settings")(apply_btn, status_var)
	)
	apply_btn.grid(row=0, column=2, sticky="e")

	def _mark_dirty(*_args: Any) -> None:
		getattr(main_ui, "_set_system_settings_dirty")("general", True)

	# 仅绑定一次，避免每次切换页面重复 trace 导致回调叠加。
	if "general" not in getattr(main_ui, "_system_settings_dirty_trace_bound_sections"):
		for var in getattr(main_ui, "right_info_category_visibility_vars").values():
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass
		for var in getattr(main_ui, "right_info_category_color_vars").values():
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass
		for var in getattr(main_ui, "system_force_d20_vars").values():
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass
		for var in getattr(main_ui, "system_force_d20_value_vars").values():
			try:
				var.trace_add("write", _mark_dirty)
			except Exception:
				pass
		getattr(main_ui, "_system_settings_dirty_trace_bound_sections").add("general")


def apply_system_general_settings(main_ui: object, apply_btn: ttk.Button, status_var: tk.StringVar) -> None:
	"""应用综合设置：目前仅落地右侧信息展示区类别开关。"""
	try:
		apply_btn.configure(state="disabled")
		visibility = {key: var.get() for key, var in getattr(main_ui, "right_info_category_visibility_vars").items()}
		color_map = {
			"黑色": "#111111",
			"灰色": "#6b7280",
			"红色": "#dc2626",
			"橙色": "#f97316",
			"绿色": "#22c55e",
			"蓝色": "#2563eb",
		}
		colors = {
			key: color_map.get(str(var.get()).strip() or "黑色", "#111111")
			for key, var in getattr(main_ui, "right_info_category_color_vars").items()
		}
		if getattr(main_ui, "right_info_panel", None) is not None:
			getattr(main_ui, "right_info_panel").set_category_visibility(visibility)
			getattr(main_ui, "right_info_panel").set_category_colors(colors)

		# 投掷结果设置：写入当前 env，并安装测试端覆盖 hook。
		force_flags = {key: bool(var.get()) for key, var in getattr(main_ui, "system_force_d20_vars").items()}
		force_values: dict[str, int] = {}
		for key, enabled in force_flags.items():
			if not enabled:
				continue
			raw = (
				str(getattr(main_ui, "system_force_d20_value_vars").get(key).get()).strip()
				if key in getattr(main_ui, "system_force_d20_value_vars")
				else ""
			)
			try:
				val = int(raw)
			except Exception:
				val = -1
			if val < 1 or val > 20:
				status_var.set("非法：投掷点数必须是 1~20 的整数")
				getattr(main_ui, "root").after(1800, lambda: status_var.set(""))
				return
			force_values[key] = val

		setattr(main_ui, "system_force_d20_flags", dict(force_flags))
		setattr(main_ui, "system_force_d20_values", dict({k: int(v) for k, v in force_values.items()}))
		env = getattr(getattr(main_ui, "controller"), "environment", None)
		if env is not None:
			try:
				setattr(env, "_ui_force_d20_flags", dict(force_flags))
				setattr(env, "_ui_force_d20_values", dict(force_values))
				ensure_d20_force_installed(
					env,
					logger=lambda msg: getattr(main_ui, "right_info_panel").append_content(f"\n{msg}"),
				)
			except Exception:
				try:
					ensure_d20_force_installed(env)
				except Exception:
					pass

		status_var.set("已应用：右侧信息展示区 + 投掷结果设置")
		getattr(main_ui, "root").after(1500, lambda: status_var.set(""))
		# 更新“已应用快照”，用于关闭时回滚。
		try:
			setattr(
				main_ui,
				"_applied_system_general_settings_snapshot",
				collect_system_general_settings_snapshot_from_vars(main_ui),
			)
		except Exception:
			pass
		getattr(main_ui, "_set_system_settings_dirty")("general", False)
		try:
			enabled_keys = [k for k, v in force_flags.items() if v]
			enabled_text = "、".join(f"{k}={force_values.get(k, 20)}" for k in enabled_keys) if enabled_keys else "无"
			getattr(main_ui, "right_info_panel").append_content(
				f"\n[UI] 已应用综合设置：右侧信息展示区类别显示/颜色；投掷结果设置={enabled_text}"
			)
		except Exception:
			pass
	finally:
		apply_btn.configure(state="normal")
