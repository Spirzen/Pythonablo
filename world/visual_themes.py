"""Floor and entity color themes for Ural Batyr visuals."""

from __future__ import annotations

from core.config import TileType


def floor_palette(floor: int, map_type: str) -> dict[str, tuple[int, int, int]]:
    """Return floor/wall/accent colors for a dungeon floor."""
    if map_type == "arena":
        return {
            "floor": (72, 58, 48),
            "floor_alt": (64, 50, 42),
            "wall": (38, 32, 28),
            "wall_top": (52, 44, 36),
        }
    phase = floor % 3
    if phase == 0:  # boss / div lair
        return {
            "floor": (58, 38, 36),
            "floor_alt": (48, 30, 28),
            "wall": (32, 22, 24),
            "wall_top": (78, 42, 38),
        }
    if phase == 2:  # rocky highlands before boss
        return {
            "floor": (62, 72, 52),
            "floor_alt": (54, 64, 46),
            "wall": (42, 48, 38),
            "wall_top": (88, 82, 62),
        }
    # open steppe
    return {
        "floor": (68, 82, 48),
        "floor_alt": (58, 72, 42),
        "wall": (46, 52, 36),
        "wall_top": (92, 88, 58),
    }


def tile_color(tile_type: TileType, floor: int, map_type: str) -> tuple[int, int, int]:
    palette = floor_palette(floor, map_type)
    return {
        TileType.VOID: (6, 8, 12),
        TileType.FLOOR: palette["floor"],
        TileType.WALL: palette["wall"],
        TileType.START: (52, 118, 72),
        TileType.EXIT: (168, 88, 48),
        TileType.STAIRS_UP: (72, 108, 168),
    }[tile_type]


def floor_variation(x: int, y: int, palette: dict) -> tuple[int, int, int]:
    base = palette["floor"]
    alt = palette["floor_alt"]
    if (x + y) % 5 == 0:
        return alt
    if (x * 3 + y * 7) % 11 == 0:
        return tuple(max(0, c - 6) for c in base)
    return base


ENEMY_BODY = {
    "boss": (185, 55, 45),
    "brute": (120, 72, 48),
    "caster": (110, 70, 145),
    "runner": (195, 115, 55),
    "grunt": (165, 78, 58),
    "treasure": (215, 175, 45),
}

ENEMY_GLOW = {
    "boss": (255, 90, 50),
    "brute": (200, 120, 60),
    "caster": (180, 100, 255),
    "runner": (255, 160, 70),
    "grunt": (220, 100, 70),
    "treasure": (255, 220, 80),
}

NPC_BODY = {
    "smith": (165, 120, 65),
    "mentor": (130, 95, 155),
    "villager": (95, 145, 175),
}

NPC_GLOW = {
    "smith": (255, 190, 90),
    "mentor": (200, 160, 255),
    "villager": (140, 210, 255),
}

PLAYER_BODY = (75, 145, 85)
PLAYER_GLOW = (218, 175, 55)
MINION_BODY = (90, 165, 110)
MINION_GLOW = (140, 220, 150)

STATUS_TINTS = {
    "poison": (80, 200, 80),
    "burn": (255, 120, 40),
    "bleed": (200, 50, 50),
    "slow": (100, 160, 255),
}
