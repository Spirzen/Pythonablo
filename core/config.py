"""Game constants and settings."""

from __future__ import annotations

from enum import Enum, auto
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = BASE_DIR / "data"
SAVE_DIR = BASE_DIR / "save_data"

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 120
TITLE = "Pythonablo — Diabloid ARPG"

TILE_SIZE = 48
MAP_WIDTH = 61
MAP_HEIGHT = 46

ISO_TILE_W = 64
ISO_TILE_H = 32

PORTAL_INTERACT_RADIUS = 1.85
PLAYER_SPEED = 310.0
DASH_SPEED_MULTIPLIER = 4.5
DASH_DURATION = 0.15
DASH_COOLDOWN = 1.5

ATTACK_COOLDOWN = 0.42
ATTACK_RANGE = 72.0
ATTACK_ARC = 3.14159  # semicircle slash
ATTACK_DAMAGE_BASE = 18.0

ENEMY_BASE_HP = 40.0
ENEMY_BASE_DAMAGE = 8.0
ENEMY_BASE_SPEED = 85.0
ENEMIES_PER_FLOOR = 38

XP_BASE = 18
XP_LEVEL_MULT = 1.19
XP_LEVEL_ADD = 5
# Extra XP gate for early levels (fades out by level XP_EARLY_CAP)
XP_EARLY_CAP = 8
XP_EARLY_STEP = 0.045

# UI palette — refined dark fantasy
UI_MARGIN = 20
UI_ACCENT = (255, 204, 96)
UI_ACCENT_DIM = (190, 150, 70)
UI_TEXT = (245, 247, 252)
UI_TEXT_DIM = (145, 155, 175)
UI_PANEL = (12, 14, 26)
UI_PANEL_BORDER = (62, 78, 128)
UI_HP_FILL = (88, 228, 112)
UI_HP_BG = (48, 22, 28)
UI_MP_FILL = (110, 185, 255)
UI_MP_BG = (22, 28, 52)
UI_CARD = (32, 36, 58)
UI_CARD_HOVER = (48, 54, 88)

# Loot rarity colors
RARITY_COLORS = {
    "normal": (200, 200, 200),
    "magic": (80, 120, 255),
    "rare": (255, 215, 60),
    "legendary": (255, 140, 40),
    "set": (0, 220, 200),
}

# Legendary affix definitions — see core/legendary_defs.py
from core.legendary_defs import LEGENDARY_AFFIXES  # noqa: E402, F401


class GameState(Enum):
    MENU = auto()
    PLAYING = auto()
    INVENTORY = auto()
    PAUSED = auto()
    SKILLS = auto()
    SKILL_UPGRADE = auto()
    MERCHANT = auto()
    GAME_OVER = auto()


class TileType(Enum):
    VOID = auto()
    FLOOR = auto()
    WALL = auto()
    START = auto()
    EXIT = auto()
    STAIRS_UP = auto()


class ItemCategory(Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    JEWELRY = "jewelry"
    CONSUMABLE = "consumable"


class ItemQuality(Enum):
    NORMAL = "normal"
    MAGIC = "magic"
    RARE = "rare"
    LEGENDARY = "legendary"
    SET = "set"


class EquipmentSlot(Enum):
    HELMET = "helmet"
    CHEST = "chest"
    SHOULDERS = "shoulders"
    GLOVES = "gloves"
    BELT = "belt"
    PANTS = "pants"
    BOOTS = "boots"
    AMULET = "amulet"
    RING_LEFT = "ring_left"
    RING_RIGHT = "ring_right"
    TALISMAN = "talisman"
    WEAPON_MAIN = "weapon_main"
    WEAPON_OFF = "weapon_off"
    SET_PRIMARY = "set_primary"
    SET_SECONDARY = "set_secondary"
    SET_THIRD = "set_third"
    SET_FOURTH = "set_fourth"
    SET_FIFTH = "set_fifth"


class GameMode(Enum):
    CLASSIC = "classic"
    ARENA = "arena"
    ARENA_BOSSES = "arena_bosses"
    SPEED = "speed"


GAME_MODE_LABELS = {
    GameMode.CLASSIC: "Классика",
    GameMode.ARENA: "Арена",
    GameMode.ARENA_BOSSES: "Арена с боссами",
    GameMode.SPEED: "Скорость",
}

GAME_MODE_DESCRIPTIONS = {
    GameMode.CLASSIC: "Подземелья, этажи, лут и наставник",
    GameMode.ARENA: "Выживание: каждые 30 сек — новый раунд",
    GameMode.ARENA_BOSSES: "Арена, но все враги — боссы",
    GameMode.SPEED: "×2 скорость, только бонусы, автоподбор",
}


class Difficulty(Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"


DIFFICULTY_LABELS = {
    Difficulty.EASY: "Лёгкий",
    Difficulty.NORMAL: "Средний",
    Difficulty.HARD: "Сложный",
}

ENEMY_DAMAGE_GLOBAL_MULT = 1.05
SPEED_MODE_MULT = 2.0
ARENA_ROUND_DURATION = 30.0
ARENA_ROUND_DIFFICULTY_STEP = 0.15

DIFFICULTY_MULT = {
    Difficulty.EASY: {"player_hp": 1.35, "player_dmg": 1.15, "enemy_hp": 0.72, "enemy_dmg": 0.65, "enemy_count": 0.85},
    Difficulty.NORMAL: {"player_hp": 1.0, "player_dmg": 1.0, "enemy_hp": 1.0, "enemy_dmg": 1.0, "enemy_count": 1.0},
    Difficulty.HARD: {"player_hp": 0.88, "player_dmg": 0.92, "enemy_hp": 1.4, "enemy_dmg": 1.35, "enemy_count": 1.2},
}

ARCANE_SET_ID = "arcane"
ARCANE_SET_SLOTS = [
    EquipmentSlot.SET_PRIMARY,
    EquipmentSlot.SET_SECONDARY,
    EquipmentSlot.SET_THIRD,
    EquipmentSlot.SET_FOURTH,
    EquipmentSlot.SET_FIFTH,
]

DUST_BY_QUALITY = {
    "normal": 1,
    "magic": 2,
    "rare": 3,
    "legendary": 4,
    "set": 5,
}
