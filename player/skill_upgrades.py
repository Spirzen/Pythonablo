"""Active skill upgrade levels (every 5 player levels)."""

from __future__ import annotations

from dataclasses import dataclass, field

UPGRADEABLE_SKILLS = ("aoe", "fireball", "whirlwind", "pulse", "summon")

SKILL_UPGRADE_LABELS = {
    "aoe": "Ударная волна",
    "fireball": "Огненный шар",
    "whirlwind": "Вихрь",
    "pulse": "Импульс",
    "summon": "Призыв",
}

SKILL_UPGRADE_EFFECTS = {
    "aoe": "Радиус ×2 за улучшение",
    "fireball": "Размер снаряда +40%",
    "whirlwind": "Красный вихрь, +15% урона",
    "pulse": "Радиус +30%",
    "summon": "+1 прислужник, +20% HP",
}


@dataclass
class SkillUpgrades:
    levels: dict[str, int] = field(default_factory=lambda: {s: 0 for s in UPGRADEABLE_SKILLS})
    pending_points: int = 0

    def level_of(self, skill_id: str) -> int:
        return self.levels.get(skill_id, 0)

    def upgrade(self, skill_id: str) -> bool:
        if self.pending_points <= 0 or skill_id not in self.levels:
            return False
        self.levels[skill_id] += 1
        self.pending_points -= 1
        return True

    def radius_mult(self, skill_id: str) -> float:
        lvl = self.level_of(skill_id)
        if skill_id == "aoe":
            return 2.0 ** lvl
        if skill_id == "pulse":
            return 1.0 + lvl * 0.3
        return 1.0

    def fireball_radius_mult(self) -> float:
        return 1.0 + self.level_of("fireball") * 0.4

    def whirlwind_damage_mult(self) -> float:
        return 1.0 + self.level_of("whirlwind") * 0.15

    def whirlwind_upgraded(self) -> bool:
        return self.level_of("whirlwind") > 0

    def max_minions(self) -> int:
        return 3 + self.level_of("summon")

    def minion_hp_mult(self) -> float:
        return 1.0 + self.level_of("summon") * 0.2

    def to_dict(self) -> dict:
        return {"levels": dict(self.levels), "pending_points": self.pending_points}

    @classmethod
    def from_dict(cls, data: dict | None) -> "SkillUpgrades":
        if not data:
            return cls()
        levels = {s: 0 for s in UPGRADEABLE_SKILLS}
        levels.update(data.get("levels", {}))
        return cls(levels=levels, pending_points=data.get("pending_points", 0))
