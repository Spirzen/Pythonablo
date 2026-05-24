"""Definitions for passive skill slots (+1% per rank, stackable)."""

from __future__ import annotations

from dataclasses import dataclass

PASSIVE_VALUE = 0.01  # +1% per rank
MAX_RANK_PER_SLOT = 10

STAT_POOL: list[tuple[str, str]] = [
    ("max_hp_pct", "Макс. HP"),
    ("max_mana_pct", "Макс. мана"),
    ("damage_pct", "Урон атаки"),
    ("armor_pct", "Броня"),
    ("regen_pct", "Реген HP"),
    ("skill_damage_pct", "Урон умений"),
    ("move_speed_pct", "Скорость бега"),
    ("attack_speed_pct", "Скорость атаки"),
    ("mana_regen_pct", "Реген маны"),
    ("crit_pct", "Крит. урон"),
]


@dataclass
class PassiveSlot:
    stat_key: str
    label: str
    rank: int = 0

    @property
    def description(self) -> str:
        return f"+{self.rank}% к {self.label.lower()}"

    @property
    def bonus(self) -> float:
        return self.rank * PASSIVE_VALUE


def build_passive_slots() -> dict[str, PassiveSlot]:
    return {
        stat_key: PassiveSlot(stat_key=stat_key, label=label)
        for stat_key, label in STAT_POOL
    }
