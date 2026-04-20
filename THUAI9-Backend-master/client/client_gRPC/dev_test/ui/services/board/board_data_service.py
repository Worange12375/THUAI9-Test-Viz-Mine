from __future__ import annotations

import time
from typing import Any


def extract_runtime_map_rows(main_ui: Any) -> list[list[int]]:
	"""Extract height-map rows from runtime env.board.

	Return value matches the board-view expected format: rows[y][x] -> height.
	"""
	env = main_ui.controller.environment
	if env is None or not hasattr(env, "board"):
		return []
	board = env.board
	width = int(getattr(board, "width", 0))
	height = int(getattr(board, "height", 0))
	height_map = getattr(board, "height_map", None)
	if height_map is None or width <= 0 or height <= 0:
		return []

	rows: list[list[int]] = []
	for y in range(height):
		row: list[int] = []
		for x in range(width):
			try:
				row.append(int(height_map[x][y]))
			except Exception:
				row.append(0)
		rows.append(row)
	return rows


def extract_mock_visual_rows(main_ui: Any) -> list[list[int]]:
	"""Extract height rows from mock game_data["map"]["rows"], applying overrides."""
	game_data = main_ui.controller.game_data
	if not isinstance(game_data, dict):
		return []
	board = game_data.get("map", {})
	raws = board.get("rows", []) if isinstance(board, dict) else []
	if not isinstance(raws, list):
		return []

	rows: list[list[int]] = []
	for y, raw_row in enumerate(raws):
		if not isinstance(raw_row, list):
			continue
		row: list[int] = []
		for x, raw_value in enumerate(raw_row):
			base_height = int(raw_value)
			override = main_ui.mock_map_height_overrides.get((x, y))
			row.append(int(override) if override is not None else int(base_height))
		rows.append(row)
	return rows


def extract_runtime_pieces(main_ui: Any) -> list[dict[str, Any]]:
	"""Extract runtime pieces for board rendering.

	This keeps the original UX semantics from main_ui:
	- Only alive pieces are rendered.
	- Label contains piece short-code and a role emoji tag.
	- Corner marker: 😇 (timed) > 💀 (dying & hp<=0).
	- is_current is driven by current action piece.
	"""
	env = main_ui.controller.environment
	if env is None:
		return []

	now = float(time.time())
	angel_until = getattr(env, "_ui_board_angel_until", None)
	angel_map: dict[int, float] = angel_until if isinstance(angel_until, dict) else {}
	current_piece = main_ui._get_runtime_current_piece(env)
	current_id = int(getattr(current_piece, "id", -1)) if current_piece is not None else -1

	def _role_short(piece_obj: Any, role_text: str) -> str:
		role_norm = str(role_text or "").strip().lower()
		if role_norm == "warrior":
			weapon_id = main_ui._safe_int(str(getattr(piece_obj, "weapon", 0)), 0)
			return "🗡" if weapon_id == 2 else "⚔️"
		if role_norm == "mage":
			return "🪄"
		if role_norm == "archer":
			return "🏹"
		if role_norm in ("custom", "自定义"):
			return "📝"
		return str(role_text or "")[:1].upper() if role_text else ""

	team_pieces: dict[int, list[Any]] = {1: [], 2: []}
	for team_id, player_attr in ((1, "player1"), (2, "player2")):
		player = getattr(env, player_attr, None)
		pieces = main_ui._coerce_piece_list(getattr(player, "pieces", None) if player is not None else None)
		if not pieces:
			continue
		for piece in pieces:
			if not bool(getattr(piece, "is_alive", True)):
				continue
			team_pieces[team_id].append(piece)

	render_pieces: list[dict[str, Any]] = []
	for team_id in (1, 2):
		sorted_pieces = sorted(team_pieces[team_id], key=lambda p: int(getattr(p, "id", 0)))
		for piece in sorted_pieces:
			pos = getattr(piece, "position", None)
			x = int(getattr(pos, "x", -1)) if pos is not None else -1
			y = int(getattr(pos, "y", -1)) if pos is not None else -1
			base_label = main_ui._get_piece_short_code(piece)
			role = str(getattr(piece, "type", "") or "").strip()
			dy = bool(getattr(piece, "is_dying", False))
			try:
				hp_now = int(getattr(piece, "health", 0))
			except Exception:
				hp_now = 0
			role_tag = _role_short(piece, role)
			if role_tag:
				base_label = f"{base_label}\n{role_tag}".rstrip()

			corner_marker = ""
			piece_id = int(getattr(piece, "id", -1))
			until = float(angel_map.get(piece_id, 0.0)) if piece_id >= 0 else 0.0
			if until and until > now:
				corner_marker = "😇"
			elif until and until <= now and piece_id >= 0:
				try:
					angel_map.pop(piece_id, None)
				except Exception:
					pass

			if (
				not corner_marker
				and dy
				and hp_now <= 0
				and bool(getattr(piece, "is_alive", True))
			):
				corner_marker = "💀"

			render_pieces.append(
				{
					"team": team_id,
					"x": x,
					"y": y,
					"label": base_label,
					"corner_marker": corner_marker,
					"is_current": int(getattr(piece, "id", -1)) == current_id,
				}
			)

	return render_pieces
