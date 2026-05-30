"""Tile definitions."""

from __future__ import annotations

from dataclasses import dataclass

from core.config import TileType


@dataclass
class Tile:
    type: TileType = TileType.VOID
    walkable: bool = False

    @staticmethod
    def floor() -> "Tile":
        return Tile(TileType.FLOOR, True)

    @staticmethod
    def wall() -> "Tile":
        return Tile(TileType.WALL, False)

    @staticmethod
    def start() -> "Tile":
        return Tile(TileType.START, True)

    @staticmethod
    def exit() -> "Tile":
        return Tile(TileType.EXIT, True)

    @staticmethod
    def stairs_up() -> "Tile":
        return Tile(TileType.STAIRS_UP, True)

    def color(self) -> tuple[int, int, int]:
        return {
            TileType.VOID: (6, 8, 12),
            TileType.FLOOR: (68, 82, 48),
            TileType.WALL: (46, 52, 36),
            TileType.START: (52, 118, 72),
            TileType.EXIT: (168, 88, 48),
            TileType.STAIRS_UP: (72, 108, 168),
        }[self.type]
