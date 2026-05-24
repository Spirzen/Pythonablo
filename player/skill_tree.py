"""Passive skill tree — 10 stackable slots, +1% per rank."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from player.passive_defs import MAX_RANK_PER_SLOT, PASSIVE_VALUE, STAT_POOL, PassiveSlot, build_passive_slots


@dataclass
class SkillTree:
    unspent_points: int = 0
    slots: dict[str, PassiveSlot] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.slots:
            self.slots = build_passive_slots()

    @property
    def points(self) -> int:
        return self.unspent_points

    @points.setter
    def points(self, value: int) -> None:
        self.unspent_points = value

    def unlocked_count(self) -> int:
        return sum(slot.rank for slot in self.slots.values())

    def invest(self, stat_key: str) -> bool:
        slot = self.slots.get(stat_key)
        if not slot:
            return False
        if self.unspent_points < 1:
            return False
        if slot.rank >= MAX_RANK_PER_SLOT:
            return False
        self.unspent_points -= 1
        slot.rank += 1
        return True

    def unlock(self, node_id: str, player_level: int) -> bool:
        """Legacy hook — node_id is stat_key for slot-based tree."""
        return self.invest(node_id)

    def pct_bonus(self, stat_key: str) -> float:
        slot = self.slots.get(stat_key)
        if not slot:
            return 0.0
        return slot.rank * PASSIVE_VALUE

    def damage_mult(self) -> float:
        return 1.0 + self.pct_bonus("damage_pct") + self.pct_bonus("crit_pct") * 0.5

    def skill_damage_bonus(self) -> float:
        return 0.0

    def skill_damage_mult(self) -> float:
        return 1.0 + self.pct_bonus("skill_damage_pct")

    def max_hp_bonus(self) -> float:
        return 0.0

    def max_mana_bonus(self) -> float:
        return 0.0

    def armor_bonus(self) -> float:
        return 0.0

    def regen_bonus(self) -> float:
        return 0.0

    def cooldown_mult(self) -> float:
        asp = self.pct_bonus("attack_speed_pct")
        return max(0.5, 1.0 - asp * 0.35)

    def move_speed_mult(self) -> float:
        return 1.0 + self.pct_bonus("move_speed_pct")

    def attack_speed_mult(self) -> float:
        return 1.0 + self.pct_bonus("attack_speed_pct")

    def hp_mult(self) -> float:
        return 1.0 + self.pct_bonus("max_hp_pct")

    def mana_mult(self) -> float:
        return 1.0 + self.pct_bonus("max_mana_pct")

    def armor_mult(self) -> float:
        return 1.0 + self.pct_bonus("armor_pct")

    def regen_mult(self) -> float:
        return 1.0 + self.pct_bonus("regen_pct")

    def mana_regen_mult(self) -> float:
        return 1.0 + self.pct_bonus("mana_regen_pct")

    def to_dict(self) -> dict[str, Any]:
        return {
            "unspent_points": self.unspent_points,
            "points": self.unspent_points,
            "slots": {key: slot.rank for key, slot in self.slots.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillTree":
        tree = cls()
        tree.unspent_points = data.get("unspent_points", data.get("points", 0))
        slot_ranks = data.get("slots", {})
        if slot_ranks:
            for key, rank in slot_ranks.items():
                if key in tree.slots:
                    tree.slots[key].rank = min(MAX_RANK_PER_SLOT, int(rank))
        else:
            for nid, nd in data.get("nodes", {}).items():
                if not nd.get("unlocked"):
                    continue
                if nid.startswith("p") and nid[1:].isdigit():
                    lvl = int(nid[1:])
                    stat_key = STAT_POOL[(lvl - 1) % len(STAT_POOL)][0]
                    if stat_key in tree.slots:
                        tree.slots[stat_key].rank = min(
                            MAX_RANK_PER_SLOT, tree.slots[stat_key].rank + 1
                        )
        return tree
