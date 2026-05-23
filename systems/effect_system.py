"""Status effects."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class EffectType(Enum):
    BURN = auto()
    POISON = auto()
    SLOW = auto()
    REGEN = auto()


@dataclass
class Effect:
    type: EffectType
    duration: float
    power: float
    tick_timer: float = 0.5


class EffectSystem:
    def __init__(self) -> None:
        self.effects: list[Effect] = []

    def update(self, dt: float) -> None:
        alive = []
        for e in self.effects:
            e.duration -= dt
            if e.duration > 0:
                alive.append(e)
        self.effects = alive
