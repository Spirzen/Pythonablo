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
