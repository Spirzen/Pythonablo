"""Game map wrapper."""

from __future__ import annotations

from core.config import MAP_HEIGHT, MAP_WIDTH, TileType
from world.level_generator import LevelGenerator
from world.tile import Tile


class GameMap:
    def __init__(self, floor: int = 1, seed: int | None = None) -> None:
        self.floor = floor
        self.area_level = floor
        gen = LevelGenerator(seed)
        self.grid, self.start_tile, self.exit_tile, self.stairs_up_tile = gen.generate(floor)
        self.spawn_x, self.spawn_y = self.start_tile
        self.enemies_spawned = False

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT

    def tile_at(self, x: int, y: int) -> Tile:
        if not self.in_bounds(x, y):
            return Tile.wall()
        return self.grid[y][x]

    def is_walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.grid[y][x].walkable

    def is_walkable_world(self, wx: float, wy: float, radius: float = 0.0) -> bool:
        if radius <= 0:
            return self.is_walkable(int(wx), int(wy))
        from world.collision import can_occupy

        return can_occupy(self, wx, wy, radius)

    def tile_type_at(self, x: int, y: int) -> TileType:
        return self.tile_at(x, y).type

    def neighbors(self, x: int, y: int) -> list[tuple[int, int]]:
        result = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self.is_walkable(nx, ny):
                result.append((nx, ny))
        return result

    def world_to_tile(self, wx: float, wy: float) -> tuple[int, int]:
        return int(wx), int(wy)

    def tile_center_world(self, tx: int, ty: int) -> tuple[float, float]:
        return tx + 0.5, ty + 0.5

    def respawn_enemies_flag(self) -> None:
        self.enemies_spawned = False
