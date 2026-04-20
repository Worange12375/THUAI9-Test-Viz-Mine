"""System settings -> static text pages (tutorial/dev).

职责：构建系统设置窗口里的“使用教程/开发信息”页面。
实现方式：读取 ui/assets 下的文本文件并展示到只读 Text 控件。

约束：不改变现有 UX，仅做代码搬家。
"""

from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk


def build_system_settings_tutorial_page(main_ui: object, parent: ttk.LabelFrame) -> None:
	wrapper = ttk.Frame(parent)
	wrapper.grid(row=0, column=0, sticky="nsew")
	wrapper.columnconfigure(0, weight=1)
	wrapper.rowconfigure(1, weight=1)

	ttk.Label(wrapper, text="使用教程", font=("Microsoft YaHei UI", 12, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)

	path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "tutorial.txt")
	path = os.path.abspath(path)
	path_var = tk.StringVar(value=f"文件：{path}")
	top = ttk.Frame(wrapper)
	top.grid(row=0, column=1, sticky="e")

	text = tk.Text(wrapper, wrap="word", font=("Microsoft YaHei UI", 10), relief="flat")
	sb = ttk.Scrollbar(wrapper, orient="vertical", command=text.yview)
	text.configure(yscrollcommand=sb.set)
	text.grid(row=1, column=0, sticky="nsew")
	sb.grid(row=1, column=1, sticky="ns")
	footer = ttk.Label(wrapper, textvariable=path_var, foreground="#6b7280")
	footer.grid(row=2, column=0, sticky="w", pady=(6, 0))

	def _reload() -> None:
		text.configure(state="normal")
		text.delete("1.0", "end")
		try:
			with open(path, "r", encoding="utf-8") as f:
				content = f.read()
		except FileNotFoundError:
			content = "未找到教程文件。\n\n请在 ui/assets/tutorial.txt 中编写教程内容，然后点击“刷新”。\n"
		except Exception as e:
			content = f"读取教程文件失败：{e}"
		text.insert("end", content)
		text.configure(state="disabled")

	ttk.Button(top, text="刷新", command=_reload).grid(row=0, column=0, sticky="e")
	_reload()


def build_system_settings_dev_page(main_ui: object, parent: ttk.LabelFrame) -> None:
	wrapper = ttk.Frame(parent)
	wrapper.grid(row=0, column=0, sticky="nsew")
	wrapper.columnconfigure(0, weight=1)
	wrapper.rowconfigure(1, weight=1)

	ttk.Label(wrapper, text="开发信息", font=("Microsoft YaHei UI", 12, "bold")).grid(
		row=0, column=0, sticky="w", pady=(0, 8)
	)

	path = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "dev_info.txt")
	path = os.path.abspath(path)
	path_var = tk.StringVar(value=f"文件：{path}")
	top = ttk.Frame(wrapper)
	top.grid(row=0, column=1, sticky="e")

	text = tk.Text(wrapper, wrap="word", font=("Microsoft YaHei UI", 10), relief="flat")
	sb = ttk.Scrollbar(wrapper, orient="vertical", command=text.yview)
	text.configure(yscrollcommand=sb.set)
	text.grid(row=1, column=0, sticky="nsew")
	sb.grid(row=1, column=1, sticky="ns")
	footer = ttk.Label(wrapper, textvariable=path_var, foreground="#6b7280")
	footer.grid(row=2, column=0, sticky="w", pady=(6, 0))

	def _reload() -> None:
		text.configure(state="normal")
		text.delete("1.0", "end")
		try:
			with open(path, "r", encoding="utf-8") as f:
				content = f.read()
		except FileNotFoundError:
			content = "未找到开发信息文件。\n\n请在 ui/assets/dev_info.txt 中编写内容，然后点击“刷新”。\n"
		except Exception as e:
			content = f"读取开发信息失败：{e}"
		text.insert("end", content)
		text.configure(state="disabled")

	ttk.Button(top, text="刷新", command=_reload).grid(row=0, column=0, sticky="e")
	_reload()
