"""Walkability checks and sliding movement on the tile grid."""

from __future__ import annotations

import math

from world.map import GameMap

# Footprint in world (tile) coordinates — keeps entities inside walkable floor.
ENTITY_RADIUS = 0.34


def _sample_points(x: float, y: float, radius: float) -> list[tuple[float, float]]:
    return [
        (x, y),
        (x - radius, y),
        (x + radius, y),
        (x, y - radius),
        (x, y + radius),
        (x - radius * 0.7, y - radius * 0.7),
        (x + radius * 0.7, y - radius * 0.7),
        (x - radius * 0.7, y + radius * 0.7),
        (x + radius * 0.7, y + radius * 0.7),
    ]


def can_occupy(game_map: GameMap, x: float, y: float, radius: float = ENTITY_RADIUS) -> bool:
    for px, py in _sample_points(x, y, radius):
        if not game_map.is_walkable(int(px), int(py)):
            return False
    return True


def clamp_to_walkable(game_map: GameMap, x: float, y: float, *, radius: float = ENTITY_RADIUS) -> tuple[float, float]:
    """Snap entity back onto the nearest walkable tile."""
    if can_occupy(game_map, x, y, radius):
        return x, y
    tx, ty = int(x), int(y)
    best: tuple[float, float] | None = None
    best_dist = 10**9
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            cx, cy = tx + dx, ty + dy
            if not game_map.is_walkable(cx, cy):
                continue
            wx, wy = cx + 0.5, cy + 0.5
            if not can_occupy(game_map, wx, wy, radius):
                continue
            dist = (wx - x) ** 2 + (wy - y) ** 2
            if dist < best_dist:
                best_dist = dist
                best = (wx, wy)
    return best if best is not None else (x, y)


def move_slide(
    game_map: GameMap,
    x: float,
    y: float,
    dx: float,
    dy: float,
    *,
    radius: float = ENTITY_RADIUS,
) -> tuple[float, float]:
    """Move by (dx, dy) with sub-step collision — stops at walls, no void teleport."""
    dist = math.hypot(dx, dy)
    if dist < 1e-6:
        return x, y

    steps = max(4, int(dist * 28))
    step_x = dx / steps
    step_y = dy / steps

    for _ in range(steps):
        nx, ny = x + step_x, y + step_y
        if can_occupy(game_map, nx, ny, radius):
            x, y = nx, ny
            continue
        # Wall slide: try each axis separately
        if can_occupy(game_map, x + step_x, y, radius):
            x += step_x
        if can_occupy(game_map, x, y + step_y, radius):
            y += step_y

    return x, y
