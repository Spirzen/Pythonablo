"""Random floor encounters."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum, auto


class EncounterType(Enum):
    NONE = auto()
    PROTECT_NPC = auto()
    KILL_ALL_ELITE = auto()
    TREASURE_GOBLINS = auto()
    RANDOM_DEBUFF = auto()
    RANDOM_BUFF = auto()
    HORDE = auto()


ENCOUNTER_LABELS = {
    EncounterType.PROTECT_NPC: "Защитите жителя!",
    EncounterType.KILL_ALL_ELITE: "Убейте всех — появится элита!",
    EncounterType.TREASURE_GOBLINS: "Сокровищники на этаже!",
    EncounterType.RANDOM_DEBUFF: "Проклятие этажа…",
    EncounterType.RANDOM_BUFF: "Благословение этажа!",
    EncounterType.HORDE: "Орда! Врагов втрое больше!",
}


@dataclass
class FloorEncounter:
    kind: EncounterType = EncounterType.NONE
    active: bool = False
    elite_spawned: bool = False
    goblins_spawned: bool = False
    horde_mult: float = 1.0

    def label(self) -> str:
        return ENCOUNTER_LABELS.get(self.kind, "")


class EncounterSystem:
    """Rolls and tracks one random encounter per dungeon floor."""

    ENCOUNTER_POOL = (
        EncounterType.PROTECT_NPC,
        EncounterType.KILL_ALL_ELITE,
        EncounterType.TREASURE_GOBLINS,
        EncounterType.RANDOM_DEBUFF,
        EncounterType.RANDOM_BUFF,
        EncounterType.HORDE,
    )

    def __init__(self) -> None:
        self.rng = random.Random()
        self.current = FloorEncounter()
        self.floor_encounters: dict[int, EncounterType] = {}

    def reset(self) -> None:
        self.current = FloorEncounter()
        self.floor_encounters.clear()

    def roll_for_floor(self, floor: int, *, is_arena: bool, is_boss_floor: bool) -> FloorEncounter:
        if is_arena or is_boss_floor or floor <= 1:
            self.current = FloorEncounter()
            return self.current

        if floor in self.floor_encounters:
            kind = self.floor_encounters[floor]
        else:
            kind = self.rng.choice(self.ENCOUNTER_POOL)
            self.floor_encounters[floor] = kind

        horde_mult = 3.0 if kind == EncounterType.HORDE else 1.0
        self.current = FloorEncounter(kind=kind, active=kind != EncounterType.NONE, horde_mult=horde_mult)
        return self.current

    def should_spawn_elite(self, enemies_alive: int) -> bool:
        return (
            self.current.kind == EncounterType.KILL_ALL_ELITE
            and self.current.active
            and not self.current.elite_spawned
            and enemies_alive == 0
        )

    def mark_elite_spawned(self) -> None:
        self.current.elite_spawned = True
