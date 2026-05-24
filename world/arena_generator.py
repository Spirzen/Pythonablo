"""Open arena map — Vampire Survivors style survival room."""

from __future__ import annotations

import random

from core.config import MAP_HEIGHT, MAP_WIDTH, TileType
from world.tile import Tile


class ArenaGenerator:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def generate(self, floor: int) -> tuple[list[list], tuple[int, int], tuple[int, int], tuple[int, int] | None]:
        grid = [[Tile.wall() for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
        margin = 3
        for y in range(margin, MAP_HEIGHT - margin):
            for x in range(margin, MAP_WIDTH - margin):
                grid[y][x] = Tile.floor()

        cx, cy = MAP_WIDTH // 2, MAP_HEIGHT // 2
        grid[cy][cx] = Tile.start()
        sx, sy = cx, cy
        # Exit hidden until survival ends — place at center as marker
        grid[cy][cx] = Tile.start()
        ex, ey = cx, cy
        stairs = None
        if floor > 1:
            ux, uy = cx - 4, cy
            if grid[uy][ux].walkable:
                grid[uy][ux] = Tile.stairs_up()
                stairs = (ux, uy)
        return grid, (sx, sy), (ex, ey), stairs
