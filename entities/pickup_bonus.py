"""Temporary pickup bonuses on the ground."""

from __future__ import annotations

from dataclasses import dataclass

from entities.entity import Entity
from player.buffs import BONUS_COLORS, BONUS_LABELS


BONUS_TYPES = ("explosion", "armor", "speed", "damage", "pain_aura", "skill_boost")


@dataclass
class PickupBonus(Entity):
    bonus_type: str = "armor"
    bob_phase: float = 0.0

    @property
    def label(self) -> str:
        return BONUS_LABELS.get(self.bonus_type, "Бонус!")

    def color(self) -> tuple[int, int, int]:
        return BONUS_COLORS.get(self.bonus_type, (255, 220, 80))
