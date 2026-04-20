"""System settings -> Design page builder.

职责：构建“系统设置窗口 -> 玩法设计”页的 Notebook 与各 tab 的装配。
- 仅负责 UI 结构（Notebook/tab/frame/文案）。
- 具体每个子页（全局/属性/法术池）的内容由 MainUI 现有方法负责（这些方法本身已薄委托到对应 service）。

边界：
- 不负责具体玩法规则注入逻辑（由各子页 service + runtime hook 完成）。
- 不修改 UX，仅做代码搬家与组织。

对外接口：
- build_system_settings_design_page(main_ui, parent)
"""

from __future__ import annotations

from typing import Any
from tkinter import ttk


def parse_int_or_none(raw: Any) -> int | None:
	try:
		s = str(raw).strip()
		if s == "":
			return None
		return int(s)
	except Exception:
		return None


def build_system_settings_design_page(main_ui: object, parent: ttk.LabelFrame) -> None:
	wrapper = ttk.Frame(parent)
	wrapper.grid(row=0, column=0, sticky="nsew")
	wrapper.columnconfigure(0, weight=1)
	wrapper.rowconfigure(2, weight=1)

	intro = (
		"这里将用于设计全局玩法规则/行动规则，并支持扩展新的行动、职业、法术等。\n"
		"实现方式：不改后端文件，通过测试端覆盖实现。"
	)
	ttk.Label(wrapper, text="玩法设计", font=("Microsoft YaHei UI", 12, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)
	ttk.Label(wrapper, text=intro, justify="left", foreground="#4b5563").grid(row=1, column=0, sticky="nw")

	nb = ttk.Notebook(wrapper)
	nb.grid(row=2, column=0, sticky="nsew", pady=(10, 0))

	# 全局
	tab_global = ttk.Frame(nb, padding=10)
	tab_global.columnconfigure(0, weight=1)
	tab_global.rowconfigure(0, weight=1)
	getattr(main_ui, "_build_design_global_page")(tab_global)
	nb.add(tab_global, text="全局")

	# 属性（天赋梯度）
	tab_attr = ttk.Frame(nb, padding=10)
	tab_attr.columnconfigure(0, weight=1)
	tab_attr.rowconfigure(0, weight=1)
	getattr(main_ui, "_build_design_attribute_page")(tab_attr)
	nb.add(tab_attr, text="属性")

	# 法术
	tab_spell = ttk.Frame(nb, padding=10)
	tab_spell.columnconfigure(0, weight=1)
	tab_spell.rowconfigure(0, weight=1)
	getattr(main_ui, "_build_design_spell_pool_page")(tab_spell)
	nb.add(tab_spell, text="法术")

	# 攻击（占位）
	tab_attack = ttk.Frame(nb, padding=10)
	tab_attack.columnconfigure(0, weight=1)
	tab_attack.rowconfigure(0, weight=1)
	ttk.Label(tab_attack, text="（占位）攻击相关全局设置区域", justify="left", foreground="#6b7280").grid(
		row=0, column=0, sticky="nw"
	)
	nb.add(tab_attack, text="攻击")

	# 职业（占位）
	tab_prof = ttk.Frame(nb, padding=10)
	tab_prof.columnconfigure(0, weight=1)
	tab_prof.rowconfigure(0, weight=1)
	ttk.Label(tab_prof, text="（占位）职业相关全局设置区域", justify="left", foreground="#6b7280").grid(
		row=0, column=0, sticky="nw"
	)
	nb.add(tab_prof, text="职业")
