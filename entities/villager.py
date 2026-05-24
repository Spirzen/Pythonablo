"""Vulnerable NPC for protect encounters."""

from __future__ import annotations

from dataclasses import dataclass

from entities.entity import Entity


@dataclass
class VillagerNPC(Entity):
    name: str = "Житель"
    sprite_name: str = "npc3.png"
    max_hp: float = 120.0
    hp: float = 120.0
    alive: bool = True
    hit_flash: float = 0.0

    def take_damage(self, amount: float) -> None:
        if not self.alive:
            return
        self.hp -= amount
        self.hit_flash = 0.15
        if self.hp <= 0:
            self.hp = 0.0
            self.alive = False

    def update(self, dt: float) -> None:
        if self.hit_flash > 0:
            self.hit_flash -= dt
