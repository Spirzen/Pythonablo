"""Player entity."""

from __future__ import annotations

from dataclasses import dataclass, field

from core.config import ATTACK_COOLDOWN, DASH_COOLDOWN, DASH_DURATION, PLAYER_SPEED
from entities.entity import Entity
from player.equipment import Equipment
from player.experience import Experience
from player.inventory import Inventory
from player.stats import Stats


@dataclass
class PlayerEntity(Entity):
    stats: Stats = field(default_factory=Stats)
    inventory: Inventory = field(default_factory=Inventory)
    equipment: Equipment = field(default_factory=Equipment)
    experience: Experience = field(default_factory=Experience)
    move_speed: float = PLAYER_SPEED
    attack_cooldown: float = ATTACK_COOLDOWN
    attack_timer: float = 0.0
    facing_angle: float = 0.0
    is_dashing: bool = False
    dash_timer: float = 0.0
    dash_cooldown_timer: float = 0.0
    hit_flash: float = 0.0

    @property
    def max_hp(self) -> float:
        return self.stats.max_hp + self.equipment.bonus("max_hp")

    @property
    def max_mana(self) -> float:
        return self.stats.max_mana + self.equipment.bonus("max_mana")

    @property
    def hp(self) -> float:
        return self.stats.hp

    @hp.setter
    def hp(self, value: float) -> None:
        self.stats.hp = value

    @property
    def mana(self) -> float:
        return self.stats.mana

    @property
    def damage(self) -> float:
        return self.stats.damage + self.equipment.bonus("damage")

    @property
    def armor(self) -> float:
        return self.stats.armor + self.equipment.bonus("armor")

    def take_damage(self, amount: float) -> float:
        reduced = max(1.0, amount * (1.0 - min(0.75, self.armor * 0.01)))
        self.stats.hp -= reduced
        self.hit_flash = 0.15
        return reduced

    def heal_over_time(self, dt: float) -> None:
        if self.hit_flash > 0:
            self.hit_flash -= dt
        regen = self.stats.regen + self.equipment.bonus("regen")
        self.stats.hp = min(self.max_hp, self.stats.hp + regen * dt)
        mana_regen = 2.0 + self.equipment.bonus("mana_regen")
        self.stats.mana = min(self.max_mana, self.stats.mana + mana_regen * dt)
