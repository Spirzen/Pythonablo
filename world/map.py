"""Game map wrapper."""

from __future__ import annotations

import random

from core.config import MAP_HEIGHT, MAP_WIDTH, TileType
from world.arena_generator import ArenaGenerator
from world.level_generator import LevelGenerator
from world.tile import Tile

ARENA_CHANCE = 0.14


class GameMap:
    def __init__(
        self,
        floor: int = 1,
        seed: int | None = None,
        *,
        force_arena: bool = False,
        allow_random_arena: bool = True,
    ) -> None:
        self.floor = floor
        self.area_level = floor
        rng = random.Random(seed)
        use_arena = force_arena or (
            allow_random_arena and floor > 1 and floor % 3 != 0 and rng.random() < ARENA_CHANCE
        )
        self.map_type = "arena" if use_arena else "dungeon"

        if self.map_type == "arena":
            gen = ArenaGenerator(seed)
            self.grid, self.start_tile, self.exit_tile, self.stairs_up_tile = gen.generate(floor)
        else:
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

    def edge_spawn_points(self, count: int = 8) -> list[tuple[float, float]]:
        """World positions along arena edges for enemy spawn."""
        points: list[tuple[float, float]] = []
        margin = 4
        edges = []
        for x in range(margin, MAP_WIDTH - margin):
            edges.append((x + 0.5, margin + 0.5))
            edges.append((x + 0.5, MAP_HEIGHT - margin - 0.5))
        for y in range(margin + 1, MAP_HEIGHT - margin - 1):
            edges.append((margin + 0.5, y + 0.5))
            edges.append((MAP_WIDTH - margin - 0.5, y + 0.5))
        rng = random.Random()
        rng.shuffle(edges)
        return edges[:count]
