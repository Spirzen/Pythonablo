"""Temporary player buffs from pickup bonuses."""

from __future__ import annotations

from dataclasses import dataclass, field


BONUS_LABELS = {
    "explosion": "Взрыв!",
    "armor": "Броня!",
    "speed": "Скорость!",
    "damage": "Ярость!",
    "pain_aura": "Аура боли!",
    "skill_boost": "Мощь умений!",
}

BONUS_COLORS = {
    "explosion": (255, 120, 40),
    "armor": (120, 180, 255),
    "speed": (100, 255, 180),
    "damage": (255, 80, 80),
    "pain_aura": (200, 60, 220),
    "skill_boost": (255, 200, 60),
}


@dataclass
class ActiveBuff:
    kind: str
    remaining: float
    magnitude: float = 1.0
    tick_timer: float = 0.0


@dataclass
class BuffManager:
    buffs: list[ActiveBuff] = field(default_factory=list)
    pain_aura_tick: float = 0.0

    def add(self, kind: str, duration: float, magnitude: float = 1.0) -> None:
        for buff in self.buffs:
            if buff.kind == kind:
                buff.remaining = max(buff.remaining, duration)
                if magnitude >= 0:
                    buff.magnitude = max(buff.magnitude, magnitude)
                else:
                    buff.magnitude = min(buff.magnitude, magnitude)
                return
        self.buffs.append(ActiveBuff(kind=kind, remaining=duration, magnitude=magnitude))

    def has(self, kind: str) -> bool:
        return any(b.kind == kind and b.remaining > 0 for b in self.buffs)

    def magnitude(self, kind: str) -> float:
        total = 0.0
        for b in self.buffs:
            if b.kind == kind and b.remaining > 0:
                total += b.magnitude
        return total

    def update(self, dt: float) -> None:
        for buff in self.buffs:
            buff.remaining -= dt
        self.buffs = [b for b in self.buffs if b.remaining > 0]

    def armor_bonus(self) -> float:
        return self.magnitude("armor") * 25.0

    def damage_mult(self) -> float:
        return max(0.55, 1.0 + self.magnitude("damage") * 0.35)

    def speed_mult(self) -> float:
        return max(0.45, 1.0 + self.magnitude("speed") * 0.4)

    def skill_damage_bonus(self) -> float:
        return self.magnitude("skill_boost") * 25.0

    def to_dict(self) -> list[dict]:
        return [
            {"kind": b.kind, "remaining": b.remaining, "magnitude": b.magnitude}
            for b in self.buffs
        ]

    @classmethod
    def from_dict(cls, data: list | None) -> "BuffManager":
        mgr = cls()
        if not data:
            return mgr
        for raw in data:
            mgr.buffs.append(
                ActiveBuff(
                    kind=raw["kind"],
                    remaining=raw.get("remaining", 0.0),
                    magnitude=raw.get("magnitude", 1.0),
                )
            )
        return mgr
