"""Loot generation on kill."""

from __future__ import annotations

import random
import uuid

from core.config import (
    ARCANE_SET_ID,
    ARCANE_SET_SLOTS,
    DUST_BY_QUALITY,
    EquipmentSlot,
    GameMode,
    ItemCategory,
    ItemQuality,
    LEGENDARY_AFFIXES,
)
from core.legendary_defs import (
    REPLACEABLE_SKILLS,
    STAT_LEGENDARY_AFFIXES,
    UNIQUE_LEGENDARY_ITEMS,
)
from core.event_bus import EventBus
from entities.enemy import EnemyEntity
from entities.item import GroundItem
from player.inventory import Item, load_item_templates


QUALITY_WEIGHTS = [
    (ItemQuality.NORMAL, 58),
    (ItemQuality.MAGIC, 30),
    (ItemQuality.RARE, 10),
    (ItemQuality.LEGENDARY, 1),
    (ItemQuality.SET, 1),
]

CATEGORY_SLOTS = {
    ItemCategory.WEAPON: [EquipmentSlot.WEAPON_MAIN, EquipmentSlot.WEAPON_OFF],
    ItemCategory.ARMOR: [
        EquipmentSlot.HELMET,
        EquipmentSlot.CHEST,
        EquipmentSlot.SHOULDERS,
        EquipmentSlot.GLOVES,
        EquipmentSlot.PANTS,
        EquipmentSlot.BOOTS,
        EquipmentSlot.BELT,
    ],
    ItemCategory.JEWELRY: [
        EquipmentSlot.AMULET,
        EquipmentSlot.RING_LEFT,
        EquipmentSlot.RING_RIGHT,
        EquipmentSlot.TALISMAN,
    ],
}

ARCANE_SET_NAMES = {
    EquipmentSlot.SET_PRIMARY: "Обод силы",
    EquipmentSlot.SET_SECONDARY: "Кристалл магии",
    EquipmentSlot.SET_THIRD: "Печать стихий",
    EquipmentSlot.SET_FOURTH: "Сфера разрушения",
    EquipmentSlot.SET_FIFTH: "Ядро заклинателя",
}


class LootSystem:
    AFFIX_POOL = [
        "max_hp", "max_mana", "damage", "armor", "regen", "strength", "dexterity",
        "skill_damage", "attack_speed", "crit_chance", "block", "move_speed",
        "gold_find", "xp_bonus", "life_on_hit", "thorns_damage", "fire_resist",
        "cold_resist", "poison_resist", "cooldown_reduction", "magic_find",
        "mana_regen", "vitality", "energy",
    ]

    AFFIX_VALUE_SCALE = {
        "crit_chance": 0.35,
        "block": 0.45,
        "gold_find": 0.5,
        "xp_bonus": 0.55,
        "magic_find": 0.4,
        "cooldown_reduction": 0.35,
        "attack_speed": 0.7,
        "move_speed": 0.6,
        "fire_resist": 0.55,
        "cold_resist": 0.55,
        "poison_resist": 0.55,
    }

    def __init__(self, events: EventBus) -> None:
        self.events = events
        self.rng = random.Random()
        self.templates = load_item_templates()
        self.game_mode = GameMode.CLASSIC
        events.subscribe("enemy_killed", self._on_kill)

    def set_game_mode(self, mode: GameMode) -> None:
        self.game_mode = mode

    @staticmethod
    def dust_for_item(item: Item) -> int:
        return DUST_BY_QUALITY.get(item.quality.value, 1)

    def disintegrate_item(self, player, item: Item) -> int:
        dust = self.dust_for_item(item)
        player.inventory.dust += dust
        return dust

    def _on_kill(self, enemy: EnemyEntity, killer=None, **_) -> None:
        if self.game_mode == GameMode.SPEED:
            return
        item = self.generate_drop(enemy)
        if item:
            ground = GroundItem(enemy.x, enemy.y, item=item)
            self.events.emit("item_dropped", ground=ground, item=item)

    def roll_quality(self, area_level: int) -> ItemQuality:
        weights = []
        for q, w in QUALITY_WEIGHTS:
            bonus = area_level * (0.5 if q != ItemQuality.NORMAL else 0)
            if q == ItemQuality.SET:
                bonus = area_level * 0.08
            elif q == ItemQuality.LEGENDARY:
                bonus = area_level * 0.05
            weights.append((q, max(1, int(w + bonus))))
        total = sum(w for _, w in weights)
        roll = self.rng.randint(1, total)
        acc = 0
        for q, w in weights:
            acc += w
            if roll <= acc:
                return q
        return ItemQuality.NORMAL

    def roll_category(self) -> ItemCategory:
        roll = self.rng.random()
        if roll < 0.35:
            return ItemCategory.WEAPON
        if roll < 0.72:
            return ItemCategory.ARMOR
        if roll < 0.92:
            return ItemCategory.JEWELRY
        return ItemCategory.CONSUMABLE

    def generate_drop(self, enemy: EnemyEntity) -> Item | None:
        if self.rng.random() > 0.42:
            return None
        category = self.roll_category()
        quality = self.roll_quality(enemy.area_level)
        item_level = max(1, min(enemy.area_level + self.rng.randint(-1, 2), enemy.area_level + 3))
        if quality == ItemQuality.SET:
            return self._build_arcane_set_item(item_level)
        if quality == ItemQuality.LEGENDARY and self.rng.random() < 0.32:
            unique = self._build_unique_legendary(item_level)
            if unique:
                return unique
        return self._build_item(category, quality, item_level)

    def _build_unique_legendary(self, level: int) -> Item | None:
        affix_id = self.rng.choice(list(UNIQUE_LEGENDARY_ITEMS.keys()))
        meta = UNIQUE_LEGENDARY_ITEMS[affix_id]
        aff = LEGENDARY_AFFIXES.get(affix_id, {})
        slot = EquipmentSlot(meta["slot"])
        category = ItemCategory(meta["category"])
        replaces = None
        if affix_id.startswith("skill_"):
            replaces = self.rng.choice(REPLACEABLE_SKILLS)
        stats = self._roll_stats(category, ItemQuality.LEGENDARY, level, {})
        stats["skill_damage"] = stats.get("skill_damage", 0) + 6 + level * 2.5
        stats["damage"] = stats.get("damage", 0) + 5 + level * 1.8
        if category == ItemCategory.ARMOR:
            stats["armor"] = stats.get("armor", 0) + 4 + level
        return Item(
            uid=str(uuid.uuid4())[:8],
            name=meta["name"],
            category=category,
            quality=ItemQuality.LEGENDARY,
            level=level,
            slot=slot,
            stats=stats,
            description=aff.get("desc", "Особый легендарный предмет."),
            legendary_affix=affix_id,
            replaces_skill=replaces,
        )

    def _build_arcane_set_item(self, level: int) -> Item:
        slot = self.rng.choice(ARCANE_SET_SLOTS)
        name = ARCANE_SET_NAMES.get(slot, "Фрагмент комплекта")
        skill_dmg = 12 + level * 3.0
        set_effects = {
            EquipmentSlot.SET_PRIMARY: {"skill_damage": skill_dmg, "max_mana": 8 + level * 2},
            EquipmentSlot.SET_SECONDARY: {"skill_damage": skill_dmg, "energy": 3 + level * 0.5},
            EquipmentSlot.SET_THIRD: {"skill_damage": skill_dmg, "regen": 1.5 + level * 0.2},
            EquipmentSlot.SET_FOURTH: {"skill_damage": skill_dmg * 1.1, "damage": 4 + level},
            EquipmentSlot.SET_FIFTH: {"skill_damage": skill_dmg * 1.2, "max_hp": 10 + level * 3},
        }
        stats = set_effects.get(slot, {"skill_damage": skill_dmg})
        return Item(
            uid=str(uuid.uuid4())[:8],
            name=name,
            category=ItemCategory.JEWELRY,
            quality=ItemQuality.SET,
            level=level,
            slot=slot,
            stats=stats,
            description="Часть магического комплекта «Аркан». Усиливает заклинания и даёт бонусы комплекта.",
            set_id=ARCANE_SET_ID,
        )

    def _build_item(self, category: ItemCategory, quality: ItemQuality, level: int) -> Item:
        pool_key = {
            ItemCategory.WEAPON: "weapons",
            ItemCategory.ARMOR: "armor",
            ItemCategory.JEWELRY: "jewelry",
            ItemCategory.CONSUMABLE: "consumables",
        }[category]
        pool = self.templates.get(pool_key, [])
        base = self.rng.choice(pool) if pool else {"name": "Предмет", "stats": {}}

        slot = None
        if category != ItemCategory.CONSUMABLE:
            slots = CATEGORY_SLOTS.get(category, [EquipmentSlot.WEAPON_MAIN])
            slot_name = base.get("slot")
            if slot_name:
                slot = EquipmentSlot(slot_name)
            else:
                slot = self.rng.choice(slots)

        stats = self._roll_stats(category, quality, level, base.get("stats", {}))
        affix_count = {"normal": 0, "magic": 1, "rare": 2, "legendary": 3, "set": 2}[quality.value]
        stats = self._add_random_affixes(stats, affix_count, level)

        # Some magic+ items get skill_damage bonus (green tint via SET quality on arcane only;
        # for regular drops we add skill_damage as affix on magic+ jewelry/weapons)
        set_id = None
        legendary_affix = None
        replaces_skill = None
        if quality == ItemQuality.LEGENDARY:
            legendary_affix = self._roll_legendary_affix()
            stats = self._apply_legendary_affix_stats(stats, legendary_affix, level)
        if quality in (ItemQuality.MAGIC, ItemQuality.RARE, ItemQuality.LEGENDARY):
            if category in (ItemCategory.WEAPON, ItemCategory.JEWELRY) and self.rng.random() < 0.18:
                stats["skill_damage"] = stats.get("skill_damage", 0) + (3 + level * 1.2)

        return Item(
            uid=str(uuid.uuid4())[:8],
            name=base.get("name", "Предмет"),
            category=category,
            quality=quality,
            level=level,
            slot=slot,
            stats=stats,
            description=base.get("description", ""),
            set_id=set_id,
            legendary_affix=legendary_affix,
            replaces_skill=replaces_skill,
        )

    def _roll_stats(self, category: ItemCategory, quality: ItemQuality, level: int, base_stats: dict) -> dict[str, float]:
        mult = 1.0 + (level - 1) * 0.12
        qmult = {"normal": 1.0, "magic": 1.2, "rare": 1.45, "legendary": 2.35, "set": 1.65}[quality.value]
        stats: dict[str, float] = {}
        for k, v in base_stats.items():
            stats[k] = float(v) * mult * qmult
        if category == ItemCategory.WEAPON and "damage" not in stats:
            stats["damage"] = (8 + level * 2.5) * qmult
        if category == ItemCategory.ARMOR and "armor" not in stats:
            stats["armor"] = (3 + level * 1.5) * qmult
        return stats

    def _add_random_affixes(self, stats: dict[str, float], count: int, level: int) -> dict[str, float]:
        pool = list(self.AFFIX_POOL)
        for _ in range(count):
            key = self.rng.choice(pool)
            scale = self.AFFIX_VALUE_SCALE.get(key, 1.0)
            val = (2 + level * self.rng.uniform(0.5, 1.2)) * self.rng.uniform(0.8, 1.3) * scale
            if key == "skill_damage":
                val = (2 + level * 0.8) * self.rng.uniform(0.9, 1.2)
            stats[key] = stats.get(key, 0) + val
        return stats

    def generate_shop_items(self, floor: int) -> tuple[list[Item], Item | None]:
        """Three dust items + one gold item for the blacksmith."""
        level = max(1, floor + self.rng.randint(-1, 1))
        dust_items: list[Item] = []
        for _ in range(3):
            category = self.roll_category()
            if category == ItemCategory.CONSUMABLE:
                category = self.rng.choice([ItemCategory.WEAPON, ItemCategory.ARMOR, ItemCategory.JEWELRY])
            quality = self.rng.choice([ItemQuality.MAGIC, ItemQuality.RARE, ItemQuality.MAGIC])
            dust_items.append(self._build_item(category, quality, level))
        gold_quality = self.rng.choice([ItemQuality.RARE, ItemQuality.LEGENDARY, ItemQuality.RARE])
        gold_item = self._build_item(self.roll_category(), gold_quality, level + 1)
        return dust_items, gold_item

    def upgrade_item(self, item: Item) -> None:
        """+10% to all numeric stats per upgrade."""
        if item.category == ItemCategory.CONSUMABLE:
            return
        for key in list(item.stats.keys()):
            item.stats[key] = item.stats[key] * 1.1
        item.upgrade_level += 1

    def reroll_item(self, item: Item) -> None:
        """Randomly replace rolled affix stats, keeping base identity."""
        if item.category == ItemCategory.CONSUMABLE:
            return
        pool_key = {
            ItemCategory.WEAPON: "weapons",
            ItemCategory.ARMOR: "armor",
            ItemCategory.JEWELRY: "jewelry",
        }.get(item.category, "weapons")
        pool = self.templates.get(pool_key, [])
        base = next((t for t in pool if t.get("name") == item.name), None)
        if not base and pool:
            base = self.rng.choice(pool)
        base_stats = dict(base.get("stats", {})) if base else {}
        stats = self._roll_stats(item.category, item.quality, item.level, base_stats)
        affix_count = {"normal": 1, "magic": 2, "rare": 3, "legendary": 4, "set": 2}[item.quality.value]
        item.stats = self._add_random_affixes(stats, affix_count, item.level)
        if item.legendary_affix and item.legendary_affix in STAT_LEGENDARY_AFFIXES:
            item.stats = self._apply_legendary_affix_stats(item.stats, item.legendary_affix, item.level)

    def goblin_drop(self, enemy: EnemyEntity) -> Item | None:
        """Treasure goblin — frequent loot on hit."""
        category = self.roll_category()
        quality = self.rng.choice([ItemQuality.MAGIC, ItemQuality.RARE, ItemQuality.MAGIC, ItemQuality.NORMAL])
        return self._build_item(category, quality, max(1, enemy.area_level))

    def _roll_legendary_affix(self) -> str:
        return self.rng.choice(list(STAT_LEGENDARY_AFFIXES))

    def _apply_legendary_affix_stats(self, stats: dict[str, float], affix: str, level: int) -> dict[str, float]:
        bonus = 4 + level * 1.5
        if affix == "vampiric":
            stats["max_hp"] = stats.get("max_hp", 0) + bonus * 2
        elif affix == "explosive":
            stats["damage"] = stats.get("damage", 0) + bonus
        elif affix == "thorns":
            stats["armor"] = stats.get("armor", 0) + bonus
        elif affix == "swift":
            stats["dexterity"] = stats.get("dexterity", 0) + bonus * 0.6
        elif affix == "arcane":
            stats["skill_damage"] = stats.get("skill_damage", 0) + bonus * 1.5
        elif affix == "fortune":
            stats["dexterity"] = stats.get("dexterity", 0) + bonus * 0.4
            stats["max_mana"] = stats.get("max_mana", 0) + bonus
        elif affix == "fury":
            stats["damage"] = stats.get("damage", 0) + bonus * 1.3
            stats["strength"] = stats.get("strength", 0) + bonus * 0.5
        elif affix == "ward":
            stats["max_hp"] = stats.get("max_hp", 0) + bonus * 2.5
            stats["armor"] = stats.get("armor", 0) + bonus * 0.5
        elif affix == "precision":
            stats["dexterity"] = stats.get("dexterity", 0) + bonus
            stats["energy"] = stats.get("energy", 0) + bonus * 0.3
        elif affix == "lifesteal":
            stats["damage"] = stats.get("damage", 0) + bonus * 0.8
            stats["regen"] = stats.get("regen", 0) + bonus * 0.15
        elif affix == "phoenix_heart":
            stats["max_hp"] = stats.get("max_hp", 0) + bonus * 1.5
            stats["regen"] = stats.get("regen", 0) + bonus * 0.2
        return stats

    def pickup(self, player, ground_items: list, *, manual: bool = False, auto_pickup: bool = False) -> bool:
        from core.config import ItemCategory, ItemQuality

        picked = False
        threshold = 1.2 if manual else (1.0 if auto_pickup else 0.6)
        for g in list(ground_items):
            if not g.item or player.distance_sq_to(g.x, g.y) >= threshold:
                continue
            item = g.item
            if item.category == ItemCategory.CONSUMABLE:
                if "max_hp" in item.stats:
                    player.stats.hp = min(player.max_hp, player.stats.hp + item.stats["max_hp"])
                if "max_mana" in item.stats:
                    player.stats.mana = min(player.max_mana, player.stats.mana + item.stats.get("max_mana", 20))
                ground_items.remove(g)
                self.events.emit("item_picked", item=item, manual=manual)
                picked = True
                continue
            if player.inventory.add_item(item):
                ground_items.remove(g)
                self.events.emit("item_picked", item=item, manual=manual)
                picked = True
            elif manual:
                self.events.emit("inventory_full")
                return False
        return picked
