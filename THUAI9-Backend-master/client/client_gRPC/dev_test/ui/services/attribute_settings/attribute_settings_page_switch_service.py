"""属性设置窗口：页面切换（piece/map/action）。

本文件负责：
- 在“属性设置”窗口内部切换三页，并清空/重建右侧 content 区域。

不负责：
- 各页具体 UI 构建（由对应 page service 负责）。

阶段说明：
- Phase 3：MainUI 拆分进行中；本文件以“搬家不改逻辑”为原则，接收 `main_ui` 实例并直接调用其字段/方法。
"""

from __future__ import annotations

from typing import Any

from tkinter import ttk


def switch_attribute_settings_page(main_ui: Any, page_key: str) -> None:
	"""切换属性设置窗口的页面。"""
	content = getattr(main_ui, "attribute_settings_content_frame", None)
	if content is None:
		return

	for widget in content.winfo_children():
		widget.destroy()

	titles = {
		"piece": "棋子属性",
		"map": "地图属性",
		"action": "行动属性",
	}

	if page_key == "piece":
		main_ui._build_attribute_piece_page(content)
		main_ui.right_info_panel.append_content("\n[UI] 属性设置页面切换: 棋子属性")
		return
	if page_key == "map":
		main_ui._build_attribute_map_page(content)
		main_ui.right_info_panel.append_content("\n[UI] 属性设置页面切换: 地图属性")
		return
	if page_key == "action":
		main_ui._build_attribute_action_page(content)
		main_ui.right_info_panel.append_content("\n[UI] 属性设置页面切换: 行动属性")
		return

	desc = {
		"map": "这里将用于设置地图属性（重点：高度/可通行性）。",
		"action": "这里将用于设置行动属性（如攻击、法术、技能数值）。",
	}

	wrapper = ttk.Frame(content)
	wrapper.grid(row=0, column=0, sticky="nsew")
	wrapper.columnconfigure(0, weight=1)
	wrapper.rowconfigure(2, weight=1)

	ttk.Label(wrapper, text=titles.get(page_key, "属性设置"), font=("Microsoft YaHei UI", 12, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)
	ttk.Label(
		wrapper,
		text=desc.get(page_key, "待实现"),
		justify="left",
		foreground="#4b5563",
	).grid(row=1, column=0, sticky="nw")

	main_ui.right_info_panel.append_content(f"\n[UI] 属性设置页面切换: {titles.get(page_key, page_key)}")
