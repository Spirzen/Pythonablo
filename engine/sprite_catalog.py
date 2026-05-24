"""Load and cache game sprites from assets/."""

from __future__ import annotations

from typing import Optional

import pygame

from core.config import ASSETS_DIR


class SpriteCatalog:
    def __init__(self) -> None:
        self._cache: dict[str, pygame.Surface | None] = {}
        self.fireball: pygame.Surface | None = None
        self.whirlwind: pygame.Surface | None = None
        self.hit: pygame.Surface | None = None
        self.inventory: pygame.Surface | None = None
        self.player: pygame.Surface | None = None
        self.enemy_default: pygame.Surface | None = None
        self.enemy_brute: pygame.Surface | None = None
        self.npc_smith: pygame.Surface | None = None
        self.npc_mentor: pygame.Surface | None = None
        self.npc_villager: pygame.Surface | None = None
        self.pillar: pygame.Surface | None = None
        self.ghost2: pygame.Surface | None = None
        self.bg: pygame.Surface | None = None
        self.logo: pygame.Surface | None = None
        self.logo_menu: pygame.Surface | None = None
        self._load_all()

    def _load(self, name: str) -> pygame.Surface | None:
        if name in self._cache:
            return self._cache[name]
        path = ASSETS_DIR / name
        surf: pygame.Surface | None = None
        if path.exists():
            try:
                surf = pygame.image.load(str(path)).convert_alpha()
            except pygame.error:
                surf = None
        self._cache[name] = surf
        return surf

    def _load_all(self) -> None:
        self.player = self._load("player.png")
        self.enemy_default = self._load("enemy_normal.png")
        self.enemy_brute = self._load("enemy_tank.png")
        self.npc_smith = self._load("npc1.png")
        self.npc_mentor = self._load("npc2.png")
        self.npc_villager = self._load("npc3.png")
        self.pillar = self._load("column.png")
        self.ghost2 = self._load("ghost2.png")
        self.fireball = self._load("fire.png")
        self.whirlwind = self._load("whirlwind.png")
        self.hit = self._load("b.png")
        self.inventory = self._load("item.png")
        bg_path = ASSETS_DIR / "background.jpg"
        if bg_path.exists():
            try:
                self.bg = pygame.image.load(str(bg_path)).convert()
            except pygame.error:
                self.bg = None
        self.logo = self._load("logo.png")
        if self.logo:
            lw, lh = self.logo.get_size()
            max_w, max_h = 480, 150
            scale = min(max_w / lw, max_h / lh)
            self.logo_menu = pygame.transform.smoothscale(
                self.logo, (max(1, int(lw * scale)), max(1, int(lh * scale)))
            )

    def enemy(self, sprite_name: str, *, kind: str = "GRUNT", is_boss: bool = False) -> pygame.Surface | None:
        if is_boss:
            demon = self._load("demon.png")
            if demon:
                return demon
        if sprite_name:
            s = self._load(sprite_name)
            if s:
                return s
        if kind == "BRUTE":
            return self.enemy_brute or self.enemy_default
        return self.enemy_default

    def npc(self, dialog_id: str) -> pygame.Surface | None:
        if dialog_id == "smith":
            return self.npc_smith
        if dialog_id == "mentor":
            return self.npc_mentor
        if dialog_id == "villager":
            return self.npc_villager
        return self.npc_smith or self.npc_mentor

    def get(self, name: str) -> pygame.Surface | None:
        return self._load(name)
