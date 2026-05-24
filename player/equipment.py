"""Equipment slots and bonuses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.config import ARCANE_SET_ID, ARCANE_SET_SLOTS, EquipmentSlot
from core.legendary_defs import REPLACEABLE_SKILLS, WHIRLWIND_ELEMENTS
from player.inventory import Item


ALL_SLOTS = [
    EquipmentSlot.HELMET,
    EquipmentSlot.SHOULDERS,
    EquipmentSlot.CHEST,
    EquipmentSlot.GLOVES,
    EquipmentSlot.BELT,
    EquipmentSlot.PANTS,
    EquipmentSlot.BOOTS,
    EquipmentSlot.AMULET,
    EquipmentSlot.RING_LEFT,
    EquipmentSlot.RING_RIGHT,
    EquipmentSlot.TALISMAN,
    EquipmentSlot.WEAPON_MAIN,
    EquipmentSlot.WEAPON_OFF,
    EquipmentSlot.SET_PRIMARY,
    EquipmentSlot.SET_SECONDARY,
    EquipmentSlot.SET_THIRD,
    EquipmentSlot.SET_FOURTH,
    EquipmentSlot.SET_FIFTH,
]

SLOT_LABELS = {
    EquipmentSlot.HELMET: "Шлем",
    EquipmentSlot.SHOULDERS: "Наплечники",
    EquipmentSlot.CHEST: "Доспех",
    EquipmentSlot.GLOVES: "Перчатки",
    EquipmentSlot.BELT: "Пояс",
    EquipmentSlot.PANTS: "Штаны",
    EquipmentSlot.BOOTS: "Сапоги",
    EquipmentSlot.AMULET: "Амулет",
    EquipmentSlot.RING_LEFT: "Кольцо (L)",
    EquipmentSlot.RING_RIGHT: "Кольцо (R)",
    EquipmentSlot.TALISMAN: "Талисман",
    EquipmentSlot.WEAPON_MAIN: "Оружие (осн.)",
    EquipmentSlot.WEAPON_OFF: "Оружие (доп.)",
    EquipmentSlot.SET_PRIMARY: "Комплект I",
    EquipmentSlot.SET_SECONDARY: "Комплект II",
    EquipmentSlot.SET_THIRD: "Комплект III",
    EquipmentSlot.SET_FOURTH: "Комплект IV",
    EquipmentSlot.SET_FIFTH: "Комплект V",
}


@dataclass
class Equipment:
    slots: dict[EquipmentSlot, Item | None] = field(default_factory=lambda: {s: None for s in ALL_SLOTS})

    def equip(self, item: Item) -> Item | None:
        if item.slot is None:
            return item
        prev = self.slots.get(item.slot)
        self.slots[item.slot] = item
        return prev

    def unequip(self, slot: EquipmentSlot) -> Item | None:
        item = self.slots.get(slot)
        self.slots[slot] = None
        return item

    def bonus(self, stat: str) -> float:
        total = 0.0
        for item in self.slots.values():
            if item and stat in item.stats:
                total += item.stats[stat]
        return total

    def legendary_bonus(self, affix_id: str) -> int:
        """Count equipped items with a given legendary affix."""
        count = 0
        for item in self.slots.values():
            if item and item.legendary_affix == affix_id:
                count += 1
        return count

    def legendary_affixes(self) -> list[str]:
        affixes: list[str] = []
        for item in self.slots.values():
            if item and item.legendary_affix and item.legendary_affix not in affixes:
                affixes.append(item.legendary_affix)
        return affixes

    def count_set_pieces(self, set_id: str = ARCANE_SET_ID) -> int:
        count = 0
        for slot in ARCANE_SET_SLOTS:
            item = self.slots.get(slot)
            if item and item.set_id == set_id:
                count += 1
        return count

    def skill_bonuses(self) -> tuple[float, float]:
        """Returns (damage_multiplier, radius_multiplier)."""
        pieces = self.count_set_pieces()
        dmg_mult = 1.0
        radius_mult = 1.0
        if pieces >= 2:
            dmg_mult = 2.0
        if pieces >= 3:
            dmg_mult *= 1.15
        if pieces >= 4:
            radius_mult *= 1.2
        if pieces >= 5:
            radius_mult *= 1.55
        return dmg_mult, radius_mult

    def set_regen_bonus(self) -> float:
        if self.count_set_pieces() >= 3:
            return 2.5
        return 0.0

    def whirlwind_element(self) -> str:
        for item in self.slots.values():
            if item and item.legendary_affix in WHIRLWIND_ELEMENTS:
                return WHIRLWIND_ELEMENTS[item.legendary_affix]
        return "default"

    def has_homing_arrow(self) -> bool:
        return self.legendary_bonus("homing_arrow") > 0

    def has_phoenix_amulet(self) -> bool:
        return self.legendary_bonus("phoenix_heart") > 0

    def consume_phoenix_amulet(self) -> None:
        for slot, item in self.slots.items():
            if item and item.legendary_affix == "phoenix_heart":
                self.slots[slot] = None
                return

    def skill_overrides(self) -> dict[str, str]:
        """Map base skill id -> override skill id."""
        overrides: dict[str, str] = {}
        for item in self.slots.values():
            if not item or not item.legendary_affix or not item.replaces_skill:
                continue
            if item.legendary_affix.startswith("skill_"):
                override = item.legendary_affix.replace("skill_", "", 1)
                overrides[item.replaces_skill] = override
        return overrides

    def effective_skill(self, base: str) -> str:
        return self.skill_overrides().get(base, base)

    def passive_skill_affixes(self) -> set[str]:
        affixes: set[str] = set()
        for item in self.slots.values():
            if not item or not item.legendary_affix:
                continue
            if item.legendary_affix in ("skill_mana_shield", "skill_ice_armor", "skill_reflect", "skill_vampirism"):
                affixes.add(item.legendary_affix.replace("skill_", "", 1))
        return affixes

    def hud_skill_layout(self) -> list[tuple[str, str, str]]:
        """Returns (key_label, skill_id, short_name) for HUD slots 1-4."""
        overrides = self.skill_overrides()
        layout = [
            ("1/F", "fireball", "Огонь"),
            ("2", overrides.get("aoe", "aoe"), "Волна"),
            ("3", overrides.get("summon", "summon"), "Приз."),
            ("4", overrides.get("pulse", "pulse"), "Имп."),
        ]
        return layout

    def to_dict(self) -> dict[str, Any]:
        from player.inventory import Inventory

        return {s.value: Inventory._item_to_dict(self.slots[s]) for s in ALL_SLOTS}

    @classmethod
    def from_dict(cls, data: dict) -> "Equipment":
        from core.config import ItemCategory, ItemQuality
        from player.inventory import Item

        eq = cls()
        for slot in ALL_SLOTS:
            raw = data.get(slot.value)
            if raw:
                eq.slots[slot] = Item(
                    uid=raw["uid"],
                    name=raw["name"],
                    category=ItemCategory(raw["category"]),
                    quality=ItemQuality(raw["quality"]),
                    level=raw["level"],
                    slot=EquipmentSlot(raw["slot"]) if raw.get("slot") else slot,
                    stats=raw.get("stats", {}),
                    description=raw.get("description", ""),
                    set_id=raw.get("set_id"),
                    legendary_affix=raw.get("legendary_affix"),
                    replaces_skill=raw.get("replaces_skill"),
                    upgrade_level=raw.get("upgrade_level", 0),
                )
        return eq
