"""Inventory and item definitions."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from core.config import DATA_DIR, EquipmentSlot, ItemCategory, ItemQuality, RARITY_COLORS


@dataclass
class Item:
    uid: str
    name: str
    category: ItemCategory
    quality: ItemQuality
    level: int
    slot: EquipmentSlot | None = None
    stats: dict[str, float] = field(default_factory=dict)
    description: str = ""
    set_id: str | None = None

    @property
    def color(self) -> tuple[int, int, int]:
        if self.quality == ItemQuality.SET or self.set_id or self.stats.get("skill_damage", 0) > 0:
            return RARITY_COLORS["set"]
        return RARITY_COLORS.get(self.quality.value, (200, 200, 200))

    def display_name(self) -> str:
        prefix = {
            ItemQuality.NORMAL: "",
            ItemQuality.MAGIC: "Магический ",
            ItemQuality.RARE: "Редкий ",
            ItemQuality.LEGENDARY: "Легендарный ",
            ItemQuality.SET: "Сетовый ",
        }[self.quality]
        return f"{prefix}{self.name}"

    def tooltip_lines(self) -> list[str]:
        lines = [self.display_name(), f"Уровень {self.level}", self.description]
        for k, v in self.stats.items():
            label = STAT_LABELS.get(k, k)
            lines.append(f"+{int(v) if v == int(v) else v:.1f} {label}")
        if self.set_id:
            lines.append(f"Комплект: {self.set_id}")
        qname = {
            ItemQuality.NORMAL: "Обычный",
            ItemQuality.MAGIC: "Магический",
            ItemQuality.RARE: "Редкий",
            ItemQuality.LEGENDARY: "Легендарный",
            ItemQuality.SET: "Сетовый",
        }[self.quality]
        lines.append(qname)
        return lines


STAT_LABELS = {
    "damage": "урон",
    "max_hp": "HP",
    "max_mana": "мана",
    "armor": "броня",
    "regen": "реген",
    "mana_regen": "реген маны",
    "strength": "сила",
    "dexterity": "ловкость",
    "skill_damage": "урон умений",
}


class Inventory:
    GRID_W = 10
    GRID_H = 6

    def __init__(self) -> None:
        self.slots: list[Item | None] = [None] * (self.GRID_W * self.GRID_H)
        self.gold: int = 0
        self.dust: int = 0

    def add_item(self, item: Item) -> bool:
        for i, slot in enumerate(self.slots):
            if slot is None:
                self.slots[i] = item
                return True
        return False

    def remove_at(self, index: int) -> Item | None:
        if 0 <= index < len(self.slots):
            item = self.slots[index]
            self.slots[index] = None
            return item
        return None

    def items(self) -> list[Item]:
        return [s for s in self.slots if s is not None]

    def to_dict(self) -> dict[str, Any]:
        return {
            "gold": self.gold,
            "dust": self.dust,
            "slots": [self._item_to_dict(s) for s in self.slots],
        }

    @staticmethod
    def _item_to_dict(item: Item | None) -> dict | None:
        if item is None:
            return None
        return {
            "uid": item.uid,
            "name": item.name,
            "category": item.category.value,
            "quality": item.quality.value,
            "level": item.level,
            "slot": item.slot.value if item.slot else None,
            "stats": item.stats,
            "description": item.description,
            "set_id": item.set_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Inventory":
        inv = cls()
        inv.gold = data.get("gold", 0)
        inv.dust = data.get("dust", 0)
        slots = data.get("slots", [])
        inv.slots = [None] * (cls.GRID_W * cls.GRID_H)
        for i, raw in enumerate(slots[: len(inv.slots)]):
            if raw:
                inv.slots[i] = Item(
                    uid=raw["uid"],
                    name=raw["name"],
                    category=ItemCategory(raw["category"]),
                    quality=ItemQuality(raw["quality"]),
                    level=raw["level"],
                    slot=EquipmentSlot(raw["slot"]) if raw.get("slot") else None,
                    stats=raw.get("stats", {}),
                    description=raw.get("description", ""),
                    set_id=raw.get("set_id"),
                )
        return inv


def load_item_templates() -> dict[str, Any]:
    path = DATA_DIR / "items.json"
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {"weapons": [], "armor": [], "jewelry": [], "consumables": []}
