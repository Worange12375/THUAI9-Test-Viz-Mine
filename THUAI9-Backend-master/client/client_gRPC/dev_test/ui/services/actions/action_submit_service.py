"""行动提交分发器（Phase 2 拆分产物）。

本文件负责：
- 作为 Phase 2 的稳定入口：根据行动模式（move/attack/spell）分发到对应 service。

不负责：
- move/attack/spell 的具体提交逻辑（已拆分到同目录下的 action_*_service.py）。

设计说明：
- 保持对外 API 不变：MainUI 仍只需要 import 并调用 `handle_preview_submit_action`。
"""

from __future__ import annotations

from typing import Any

from .action_attack_service import handle_preview_attack
from .action_move_service import handle_preview_move
from .action_spell_service import handle_preview_spell


def handle_preview_submit_action(main_ui: Any) -> None:
	"""处理“预览模式：确认行动”按钮。

	说明：
	- 这是 Phase 2 的 service 入口函数。
	- 只做 mode 分发：move/attack/spell 的实际逻辑在各自的 `handle_preview_*` 中。
	"""
	mode = main_ui.action_ui_mode.get().strip().lower()
	if mode not in ("move", "attack", "spell"):
		main_ui._set_action_feedback("请先选择行动类型", False)
		return

	if mode == "move":
		handle_preview_move(main_ui)
		return

	elif mode == "attack":
		handle_preview_attack(main_ui)
		return

	handle_preview_spell(main_ui)
	return
