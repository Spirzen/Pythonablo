"""Serialize / deserialize per-floor dungeon state."""

from __future__ import annotations

from typing import Any

from core.config import ItemCategory, ItemQuality, EquipmentSlot
from entities.enemy import EnemyEntity, EnemyKind
from entities.item import GroundItem
from player.inventory import Item


def enemy_to_dict(enemy: EnemyEntity) -> dict[str, Any]:
    return {
        "x": enemy.x,
        "y": enemy.y,
        "kind": enemy.kind.name,
        "max_hp": enemy.max_hp,
        "hp": enemy.hp,
        "damage": enemy.damage,
        "speed": enemy.speed,
        "xp_value": enemy.xp_value,
        "area_level": enemy.area_level,
        "is_boss": enemy.is_boss,
        "enemy_id": enemy.enemy_id,
        "sprite_name": enemy.sprite_name,
        "visual_scale": enemy.visual_scale,
        "special_abilities": enemy.special_abilities,
        "shield_timer": enemy.shield_timer,
        "enraged": enemy.enraged,
        "is_floor_elite": enemy.is_floor_elite,
        "poison_rem": enemy.poison_rem,
        "poison_dps": enemy.poison_dps,
        "burn_rem": enemy.burn_rem,
        "burn_dps": enemy.burn_dps,
        "bleed_rem": enemy.bleed_rem,
        "bleed_dps": enemy.bleed_dps,
        "curse_rem": enemy.curse_rem,
        "curse_stacks": enemy.curse_stacks,
        "slow_rem": enemy.slow_rem,
        "slow_strength": enemy.slow_strength,
    }


def enemy_from_dict(data: dict[str, Any]) -> EnemyEntity:
    return EnemyEntity(
        x=data["x"],
        y=data["y"],
        kind=EnemyKind[data.get("kind", "GRUNT")],
        max_hp=data.get("max_hp", 40),
        hp=data.get("hp", 40),
        damage=data.get("damage", 8),
        speed=data.get("speed", 85),
        xp_value=data.get("xp_value", 12),
        area_level=data.get("area_level", 1),
        is_boss=data.get("is_boss", False),
        enemy_id=data.get("enemy_id", "fallen"),
        sprite_name=data.get("sprite_name", "enemy_normal.png"),
        visual_scale=data.get("visual_scale", 1.0),
        special_abilities=data.get("special_abilities", []),
        shield_timer=data.get("shield_timer", 0.0),
        enraged=data.get("enraged", False),
        is_floor_elite=data.get("is_floor_elite", False),
        poison_rem=data.get("poison_rem", 0.0),
        poison_dps=data.get("poison_dps", 0.0),
        burn_rem=data.get("burn_rem", 0.0),
        burn_dps=data.get("burn_dps", 0.0),
        bleed_rem=data.get("bleed_rem", 0.0),
        bleed_dps=data.get("bleed_dps", 0.0),
        curse_rem=data.get("curse_rem", 0.0),
        curse_stacks=data.get("curse_stacks", 0),
        slow_rem=data.get("slow_rem", 0.0),
        slow_strength=data.get("slow_strength", 0.0),
        ability_cooldowns={a: 3.0 for a in data.get("special_abilities", [])},
    )


def ground_item_to_dict(g: GroundItem) -> dict[str, Any]:
    item_data = None
    if g.item:
        item_data = {
            "uid": g.item.uid,
            "name": g.item.name,
            "category": g.item.category.value,
            "quality": g.item.quality.value,
            "level": g.item.level,
            "slot": g.item.slot.value if g.item.slot else None,
            "stats": g.item.stats,
            "description": g.item.description,
            "set_id": g.item.set_id,
            "legendary_affix": g.item.legendary_affix,
            "replaces_skill": g.item.replaces_skill,
        }
    return {"x": g.x, "y": g.y, "item": item_data}


def ground_item_from_dict(data: dict[str, Any]) -> GroundItem:
    raw = data.get("item")
    item = None
    if raw:
        item = Item(
            uid=raw["uid"],
            name=raw["name"],
            category=ItemCategory(raw["category"]),
            quality=ItemQuality(raw["quality"]),
            level=raw["level"],
            slot=EquipmentSlot(raw["slot"]) if raw.get("slot") else None,
            stats=raw.get("stats", {}),
            description=raw.get("description", ""),
            set_id=raw.get("set_id"),
            legendary_affix=raw.get("legendary_affix"),
            replaces_skill=raw.get("replaces_skill"),
        )
    return GroundItem(x=data["x"], y=data["y"], item=item)


def floor_state_to_dict(enemies: list[EnemyEntity], ground_items: list[GroundItem], ground_bonuses: list | None = None) -> dict[str, Any]:
    return {
        "enemies": [enemy_to_dict(e) for e in enemies if e.alive and e.hp > 0],
        "ground_items": [ground_item_to_dict(g) for g in ground_items],
        "ground_bonuses": ground_bonuses or [],
    }


def restore_floor_state(data: dict[str, Any]) -> tuple[list[EnemyEntity], list[GroundItem], list]:
    enemies = [enemy_from_dict(e) for e in data.get("enemies", [])]
    ground = [ground_item_from_dict(g) for g in data.get("ground_items", [])]
    bonuses = data.get("ground_bonuses", [])
    return enemies, ground, bonuses
