"""移动行动提交（Phase 2 拆分产物）。

本文件负责：
- 处理“行动面板 -> 确认行动 -> move”分支。
- 保持行为不变：复用 MainUI 现有的方法（日志、刷新、兜底等）。

不负责：
- 行动面板控件的创建与渲染（仍在 MainUI / views）。

设计说明：
- 目前为了最小改动，这里接收 `main_ui` 实例并直接访问其字段/方法。
"""

from __future__ import annotations

from typing import Any, Optional

from env import ActionSet, Point


def build_move_action_from_ui(main_ui: Any) -> tuple[Optional[ActionSet], str]:
	"""将移动 UI 输入转换成 ActionSet，并做最小合法性校验。"""
	if main_ui.controller.runtime_source != "runtime_env":
		return None, "当前不是后端运行模式，移动提交仅在 runtime 模式可执行"

	env = main_ui.controller.environment
	if env is None:
		return None, "环境未初始化，请先加载后端模式"

	current_piece = main_ui._get_runtime_current_piece(env)
	if current_piece is None:
		return None, "当前无可行动棋子，请检查对局初始化是否完成"
	# 濒死行动限制：按玩法设计配置拦截。
	if main_ui._is_runtime_piece_in_near_death(env, current_piece) and not main_ui._near_death_can_move(env):
		return None, "濒死状态下不能移动（可在 系统设置→玩法设计→全局 调整）"
	if int(getattr(current_piece, "action_points", 0)) <= 0:
		return None, "当前棋子行动位不足"

	try:
		target_x = int(main_ui.action_move_x_var.get().strip())
		target_y = int(main_ui.action_move_y_var.get().strip())
	except Exception:
		return None, "移动坐标必须是整数"

	board = getattr(env, "board", None)
	width = int(getattr(board, "width", 0)) if board is not None else 0
	height = int(getattr(board, "height", 0)) if board is not None else 0
	if target_x < 0 or target_y < 0 or target_x >= width or target_y >= height:
		return None, "目标坐标超出地图范围"

	if board is not None:
		height_map = getattr(board, "height_map", None)
		if height_map is None:
			return None, "地图高度数据不可用"
		try:
			if int(height_map[target_x][target_y]) == -1:
				return None, "目标为不可通行地块"
		except Exception:
			return None, "目标地块不可访问"

		try:
			cell = board.grid[target_x][target_y]
			if int(getattr(cell, "state", 0)) == 2 and int(getattr(cell, "piece_id", -1)) != int(
				getattr(current_piece, "id", -1)
			):
				return None, "目标格已有其他棋子占据"
		except Exception:
			return None, "目标地块不可访问"

	legal_moves = env.get_legal_moves(current_piece)
	legal_targets = {(int(getattr(p, "x", -1)), int(getattr(p, "y", -1))) for p in legal_moves}
	if (target_x, target_y) not in legal_targets:
		return None, "目标不在当前棋子的可移动范围内"

	action = ActionSet()
	action.move = True
	action.move_target = Point(target_x, target_y)
	action.attack = False
	action.spell = False
	piece_code = main_ui._get_piece_short_code(current_piece)
	return action, f"已提交移动：{piece_code} -> ({target_x}, {target_y})"


def handle_preview_move(main_ui: Any) -> None:
	"""提交移动行动（move）。

	输入来源：MainUI 的行动面板变量。
	输出效果：写日志/刷新 UI/必要时触发陷阱与信息 flush。
	"""
	action, message = build_move_action_from_ui(main_ui)
	if action is None:
		main_ui.right_info_panel.append_content(f"\n[UI] 移动提交失败：{message}")
		main_ui._set_action_feedback(f"行动失败：{message}", False)
		return
	env = main_ui.controller.environment
	if env is None:
		main_ui._set_action_feedback("行动失败：环境未初始化", False)
		return
	current_piece = main_ui._get_runtime_current_piece(env)
	if current_piece is None:
		main_ui._set_action_feedback("行动失败：未定位到当前行动棋子", False)
		return
	# 濒死行动限制：按玩法设计配置拦截。
	if main_ui._is_runtime_piece_in_near_death(env, current_piece) and not main_ui._near_death_can_move(env):
		main_ui._set_action_feedback("行动失败：濒死状态下不能移动", False)
		main_ui.right_info_panel.append_content("\n[UI] 移动提交失败：濒死状态下不能移动")
		return

	old_pos = getattr(current_piece, "position", None)
	old_x = int(getattr(old_pos, "x", -1)) if old_pos is not None else -1
	old_y = int(getattr(old_pos, "y", -1)) if old_pos is not None else -1
	old_ap = int(getattr(current_piece, "action_points", 0))
	setattr(env, "current_piece", current_piece)
	target_x = int(getattr(action.move_target, "x", -1))
	target_y = int(getattr(action.move_target, "y", -1))

	env.execute_player_action(action)

	# 仅在 UI 层兜底：若 env 只更新棋盘占位而未同步 piece.position，则在这里补齐。
	board_after = getattr(env, "board", None)
	try:
		if board_after is not None:
			cell_after = board_after.grid[target_x][target_y]
			if int(getattr(cell_after, "state", 0)) == 2 and int(getattr(cell_after, "piece_id", -1)) == int(
				getattr(current_piece, "id", -2)
			):
				accessor = current_piece.get_accessor()
				accessor.set_position(Point(target_x, target_y))
	except Exception:
		pass

	new_pos = getattr(current_piece, "position", None)
	new_x = int(getattr(new_pos, "x", -1)) if new_pos is not None else -1
	new_y = int(getattr(new_pos, "y", -1)) if new_pos is not None else -1
	new_ap = int(getattr(current_piece, "action_points", 0))

	if (new_x, new_y) != (target_x, target_y):
		main_ui._set_action_feedback("行动失败：移动未生效（非法路径或规则限制）", False)
		main_ui.right_info_panel.append_content(
			f"\n[UI] 移动失败：{main_ui._get_piece_short_code(current_piece)} 仍在 ({new_x}, {new_y})"
		)
		return

	main_ui._append_runtime_action_log(
		actor_code=main_ui._get_piece_short_code(current_piece),
		action_label="移动",
		summary=f"({old_x}, {old_y}) -> ({new_x}, {new_y})，AP {old_ap}->{new_ap}",
	)
	main_ui._try_trigger_runtime_trap_on_piece(env, current_piece, reason="移动完成触发")
	main_ui._set_action_feedback("行动成功", True)
	main_ui._update_cards_from_env()
	main_ui._refresh_piece_cards()
	main_ui._refresh_board_view()
	# 显示本次动作触发的濒死/死亡系统消息（不依赖回合结束 flush）。
	try:
		main_ui._flush_runtime_pending_messages(env)
	except Exception:
		pass
	return
