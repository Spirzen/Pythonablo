"""Procedural dungeon generation."""

from __future__ import annotations

import random
from dataclasses import dataclass

from core.config import MAP_HEIGHT, MAP_WIDTH, TileType
from world.tile import Tile

CORRIDOR_WIDTH = 5


@dataclass
class Room:
    x: int
    y: int
    w: int
    h: int

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.w // 2, self.y + self.h // 2


class LevelGenerator:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def generate(self, floor: int) -> tuple[list[list[Tile]], tuple[int, int], tuple[int, int], tuple[int, int] | None]:
        """Returns grid, start_pos, exit_pos, stairs_up_pos."""
        grid = [[Tile() for _ in range(MAP_WIDTH)] for _ in range(MAP_HEIGHT)]
        rooms: list[Room] = []
        attempts = 0
        while len(rooms) < 8 and attempts < 120:
            attempts += 1
            w = self.rng.randint(6, 10)
            h = self.rng.randint(6, 9)
            x = self.rng.randint(1, MAP_WIDTH - w - 2)
            y = self.rng.randint(1, MAP_HEIGHT - h - 2)
            room = Room(x, y, w, h)
            if any(self._intersects(room, r) for r in rooms):
                continue
            rooms.append(room)
            self._carve_room(grid, room)

        if len(rooms) < 2:
            rooms = [Room(2, 2, 10, 8), Room(MAP_WIDTH - 14, MAP_HEIGHT - 12, 10, 8)]
            for r in rooms:
                self._carve_room(grid, r)

        for i in range(1, len(rooms)):
            self._connect(grid, rooms[i - 1].center, rooms[i].center)

        self._widen_chokepoints(grid)

        start_room = rooms[0]
        exit_room = max(rooms, key=lambda r: abs(r.center[0] - start_room.center[0]) + abs(r.center[1] - start_room.center[1]))
        sx, sy = start_room.center
        ex, ey = exit_room.center
        grid[sy][sx] = Tile.start()
        grid[ey][ex] = Tile.exit()

        stairs_up = None
        if floor > 1:
            # Place stairs in the room farthest from start (excluding exit room)
            candidates = [r for r in rooms if r is not exit_room]
            if not candidates:
                candidates = rooms
            stairs_room = max(
                candidates,
                key=lambda r: abs(r.center[0] - start_room.center[0]) + abs(r.center[1] - start_room.center[1]),
            )
            ux, uy = stairs_room.center
            if (ux, uy) != (sx, sy) and (ux, uy) != (ex, ey):
                grid[uy][ux] = Tile.stairs_up()
                stairs_up = (ux, uy)
            else:
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = ux + dx, uy + dy
                    if 0 <= nx < MAP_WIDTH and 0 <= ny < MAP_HEIGHT and grid[ny][nx].walkable:
                        if (nx, ny) not in ((sx, sy), (ex, ey)):
                            grid[ny][nx] = Tile.stairs_up()
                            stairs_up = (nx, ny)
                            break

        return grid, (sx, sy), (ex, ey), stairs_up

    def _intersects(self, a: Room, b: Room) -> bool:
        return not (a.x + a.w + 2 < b.x or b.x + b.w + 2 < a.x or a.y + a.h + 2 < b.y or b.y + b.h + 2 < a.y)

    def _carve_room(self, grid: list[list[Tile]], room: Room) -> None:
        for y in range(room.y, room.y + room.h):
            for x in range(room.x, room.x + room.w):
                if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
                    grid[y][x] = Tile.floor()

    def _set_floor(self, grid: list[list[Tile]], x: int, y: int) -> None:
        if 0 <= x < MAP_WIDTH and 0 <= y < MAP_HEIGHT:
            if grid[y][x].type not in (TileType.START, TileType.EXIT, TileType.STAIRS_UP):
                grid[y][x] = Tile.floor()

    def _carve_thick_point(self, grid: list[list[Tile]], cx: int, cy: int, half: int) -> None:
        for dy in range(-half, half + 1):
            for dx in range(-half, half + 1):
                self._set_floor(grid, cx + dx, cy + dy)

    def _carve_h_tunnel(self, grid: list[list[Tile]], x1: int, x2: int, y: int, half: int) -> None:
        for x in range(min(x1, x2), max(x1, x2) + 1):
            self._carve_thick_point(grid, x, y, half)

    def _carve_v_tunnel(self, grid: list[list[Tile]], y1: int, y2: int, x: int, half: int) -> None:
        for y in range(min(y1, y2), max(y1, y2) + 1):
            self._carve_thick_point(grid, x, y, half)

    def _connect(self, grid: list[list[Tile]], a: tuple[int, int], b: tuple[int, int]) -> None:
        x, y = a
        bx, by = b
        half = CORRIDOR_WIDTH // 2

        if self.rng.random() < 0.5:
            self._carve_h_tunnel(grid, x, bx, y, half)
            self._carve_v_tunnel(grid, y, by, bx, half)
        else:
            self._carve_v_tunnel(grid, y, by, x, half)
            self._carve_h_tunnel(grid, x, bx, by, half)

        self._carve_thick_point(grid, bx, by, half)

    def _widen_chokepoints(self, grid: list[list[Tile]]) -> None:
        """Expand 1-tile-wide floor gaps so entities can pass."""
        for y in range(1, MAP_HEIGHT - 1):
            for x in range(1, MAP_WIDTH - 1):
                if not grid[y][x].walkable:
                    continue
                if grid[y][x].type in (TileType.START, TileType.EXIT, TileType.STAIRS_UP):
                    continue
                # Horizontal 1-wide choke: wall-floor-wall on N/S
                if not grid[y - 1][x].walkable and not grid[y + 1][x].walkable:
                    self._set_floor(grid, x, y - 1)
                    self._set_floor(grid, x, y + 1)
                # Vertical 1-wide choke
                if not grid[y][x - 1].walkable and not grid[y][x + 1].walkable:
                    self._set_floor(grid, x - 1, y)
                    self._set_floor(grid, x + 1, y)
