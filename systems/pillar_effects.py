"""Random pillar buff/debuff application."""

from __future__ import annotations

import random

from entities.player import PlayerEntity
from player.buffs import BONUS_LABELS, BuffManager

PILLAR_EFFECTS: list[tuple[str, str, bool, float, float]] = [
    # id, label, is_buff, magnitude, duration
    ("hp_burst", "Исцеление!", True, 0.0, 0.0),
    ("mana_burst", "Приток маны!", True, 0.0, 0.0),
    ("damage", "Сила!", True, 1.0, 12.0),
    ("speed", "Стремительность!", True, 1.0, 10.0),
    ("armor", "Каменная кожа!", True, 1.0, 15.0),
    ("skill_boost", "Мощь умений!", True, 1.0, 12.0),
    ("weakness", "Слабость…", False, 1.0, 10.0),
    ("slow", "Вязкость…", False, 1.0, 8.0),
    ("mana_drain", "Истощение…", False, 0.0, 0.0),
    ("curse_touch", "Проклятие…", False, 1.0, 8.0),
]


def roll_pillar_effect(rng: random.Random) -> tuple[str, str, bool, float, float]:
    return rng.choice(PILLAR_EFFECTS)


def apply_pillar_effect(player: PlayerEntity, effect: tuple[str, str, bool, float, float]) -> str:
    eid, label, is_buff, magnitude, duration = effect
    if eid == "hp_burst":
        player.stats.hp = min(player.max_hp, player.stats.hp + player.max_hp * 0.25)
        return label
    if eid == "mana_burst":
        player.stats.mana = min(player.max_mana, player.stats.mana + player.max_mana * 0.35)
        return label
    if eid == "mana_drain":
        player.stats.mana = max(0, player.stats.mana - player.max_mana * 0.3)
        return label
    if is_buff:
        kind = {"damage": "damage", "speed": "speed", "armor": "armor", "skill_boost": "skill_boost"}.get(eid, "damage")
        player.buffs.add(kind, duration, magnitude=magnitude)
    else:
        kind = {"weakness": "damage", "slow": "speed", "curse_touch": "skill_boost"}.get(eid, "damage")
        player.buffs.add(kind, duration, magnitude=-abs(magnitude) * 0.65)
    return label
