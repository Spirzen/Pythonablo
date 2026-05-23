"""Summoned minion."""

from __future__ import annotations

from dataclasses import dataclass

from entities.entity import Entity


@dataclass
class MinionEntity(Entity):
    hp: float = 40.0
    max_hp: float = 40.0
    damage: float = 8.0
    speed: float = 95.0
    life: float = 18.0
    attack_timer: float = 0.0
    attack_cooldown: float = 0.9
    hit_flash: float = 0.0

    def take_damage(self, amount: float) -> None:
        self.hp -= amount
        self.hit_flash = 0.1
