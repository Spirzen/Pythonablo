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
            TileType.VOID: (8, 8, 14),
            TileType.FLOOR: (48, 54, 72),
            TileType.WALL: (22, 26, 38),
            TileType.START: (52, 128, 88),
            TileType.EXIT: (168, 72, 52),
            TileType.STAIRS_UP: (82, 118, 178),
        }[self.type]
