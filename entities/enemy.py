"""Enemy entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto

from entities.entity import Entity


class EnemyKind(Enum):
    GRUNT = auto()
    RUNNER = auto()
    BRUTE = auto()
    CASTER = auto()


@dataclass
class EnemyEntity(Entity):
    kind: EnemyKind = EnemyKind.GRUNT
    max_hp: float = 40.0
    hp: float = 40.0
    damage: float = 8.0
    speed: float = 85.0
    xp_value: int = 12
    area_level: int = 1
    hit_flash: float = 0.0
    attack_timer: float = 0.0
    attack_cooldown: float = 1.2
    path: list[tuple[int, int]] = field(default_factory=list)
    path_timer: float = 0.0
    size_scale: float = 1.0
    visual_scale: float = 1.0
    is_boss: bool = False
    enemy_id: str = "fallen"
    ability_cooldown: float = 4.0
    ability_timer: float = 2.0
    casting: float = 0.0

    def take_damage(self, amount: float) -> None:
        self.hp -= amount
        self.hit_flash = 0.12
        self.size_scale = 1.2

    def update_anim(self, dt: float) -> None:
        if self.hit_flash > 0:
            self.hit_flash -= dt
        if self.size_scale > 1.0:
            self.size_scale -= dt * 4
            if self.size_scale < 1.0:
                self.size_scale = 1.0

    @property
    def current_radius(self) -> float:
        base = 0.35 if self.kind == EnemyKind.RUNNER else 0.45 if self.kind == EnemyKind.BRUTE else 0.4
        if self.is_boss:
            base *= 1.35
        return base * self.size_scale

    @property
    def draw_scale(self) -> float:
        return self.visual_scale * self.size_scale
