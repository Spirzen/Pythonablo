"""Loot generation on kill."""

from __future__ import annotations

import random
import uuid

from core.config import (
    ARCANE_SET_ID,
    ARCANE_SET_SLOTS,
    DUST_BY_QUALITY,
    EquipmentSlot,
    ItemCategory,
    ItemQuality,
)
from core.event_bus import EventBus
from entities.enemy import EnemyEntity
from entities.item import GroundItem
from player.inventory import Item, load_item_templates


QUALITY_WEIGHTS = [
    (ItemQuality.NORMAL, 55),
    (ItemQuality.MAGIC, 28),
    (ItemQuality.RARE, 12),
    (ItemQuality.LEGENDARY, 4),
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
    def __init__(self, events: EventBus) -> None:
        self.events = events
        self.rng = random.Random()
        self.templates = load_item_templates()
        events.subscribe("enemy_killed", self._on_kill)

    @staticmethod
    def dust_for_item(item: Item) -> int:
        return DUST_BY_QUALITY.get(item.quality.value, 1)

    def disintegrate_item(self, player, item: Item) -> int:
        dust = self.dust_for_item(item)
        player.inventory.dust += dust
        return dust

    def _on_kill(self, enemy: EnemyEntity, killer=None, **_) -> None:
        item = self.generate_drop(enemy)
        if item:
            ground = GroundItem(enemy.x, enemy.y, item=item)
            self.events.emit("item_dropped", ground=ground, item=item)

    def roll_quality(self, area_level: int) -> ItemQuality:
        weights = []
        for q, w in QUALITY_WEIGHTS:
            bonus = area_level * (0.5 if q != ItemQuality.NORMAL else 0)
            if q == ItemQuality.SET:
                bonus = area_level * 0.15
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
        return self._build_item(category, quality, item_level)

    def _build_arcane_set_item(self, level: int) -> Item:
        slot = self.rng.choice(ARCANE_SET_SLOTS)
        name = ARCANE_SET_NAMES.get(slot, "Фрагмент комплекта")
        skill_dmg = 8 + level * 2.5
        return Item(
            uid=str(uuid.uuid4())[:8],
            name=name,
            category=ItemCategory.JEWELRY,
            quality=ItemQuality.SET,
            level=level,
            slot=slot,
            stats={"skill_damage": skill_dmg},
            description="Часть магического комплекта. Усиливает урон умений.",
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
        )

    def _roll_stats(self, category: ItemCategory, quality: ItemQuality, level: int, base_stats: dict) -> dict[str, float]:
        mult = 1.0 + (level - 1) * 0.12
        qmult = {"normal": 1.0, "magic": 1.2, "rare": 1.45, "legendary": 1.8, "set": 1.55}[quality.value]
        stats: dict[str, float] = {}
        for k, v in base_stats.items():
            stats[k] = float(v) * mult * qmult
        if category == ItemCategory.WEAPON and "damage" not in stats:
            stats["damage"] = (8 + level * 2.5) * qmult
        if category == ItemCategory.ARMOR and "armor" not in stats:
            stats["armor"] = (3 + level * 1.5) * qmult
        return stats

    def _add_random_affixes(self, stats: dict[str, float], count: int, level: int) -> dict[str, float]:
        affixes = ["max_hp", "max_mana", "damage", "armor", "regen", "strength", "dexterity", "skill_damage"]
        for _ in range(count):
            key = self.rng.choice(affixes)
            val = (2 + level * self.rng.uniform(0.5, 1.2)) * self.rng.uniform(0.8, 1.3)
            if key == "skill_damage":
                val = (2 + level * 0.8) * self.rng.uniform(0.9, 1.2)
            stats[key] = stats.get(key, 0) + val
        return stats

    def pickup(self, player, ground_items: list[GroundItem]) -> None:
        from core.config import ItemCategory

        for g in list(ground_items):
            if g.item and player.distance_sq_to(g.x, g.y) < 0.6:
                item = g.item
                if item.category == ItemCategory.CONSUMABLE:
                    if "max_hp" in item.stats:
                        player.stats.hp = min(player.max_hp, player.stats.hp + item.stats["max_hp"])
                    if "max_mana" in item.stats:
                        player.stats.mana = min(player.max_mana, player.stats.mana + item.stats.get("max_mana", 20))
                    ground_items.remove(g)
                    self.events.emit("item_picked", item=item)
                    continue
                if player.inventory.add_item(item):
                    ground_items.remove(g)
                    self.events.emit("item_picked", item=item)
