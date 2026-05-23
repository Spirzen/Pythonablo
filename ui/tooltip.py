"""Floating tooltips for items and skills."""

from __future__ import annotations

import pygame

from core.config import SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_PANEL, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from core.config import EquipmentSlot
from engine.renderer import Renderer
from entities.player import PlayerEntity
from player.inventory import STAT_LABELS, Item
from systems.skill_system import SkillSystem

GOOD = (100, 220, 130)
BAD = (255, 110, 100)
NEUTRAL = (180, 190, 210)

SKILL_INFO: dict[str, dict] = {
    "aoe": {
        "title": "Ударная волна",
        "desc": "Мощный взрыв вокруг героя, бьёт всех врагов рядом.",
        "mana": SkillSystem.MANA_COSTS["aoe"],
        "cd": SkillSystem.COOLDOWNS["aoe"],
        "dmg_base": 32,
    },
    "fireball": {
        "title": "Огненный шар",
        "desc": "Метает огненный снаряд в сторону курсора.",
        "mana": SkillSystem.MANA_COSTS["fireball"],
        "cd": SkillSystem.COOLDOWNS["fireball"],
        "dmg_base": 28,
    },
    "summon": {
        "title": "Призыв прислужника",
        "desc": "Призывает союзника (до 3), атакует врагов.",
        "mana": SkillSystem.MANA_COSTS["summon"],
        "cd": SkillSystem.COOLDOWNS["summon"],
        "dmg_base": 10,
    },
    "pulse": {
        "title": "Импульс",
        "desc": "Быстрый энергетический импульс по ближайшим целям.",
        "mana": SkillSystem.MANA_COSTS["pulse"],
        "cd": SkillSystem.COOLDOWNS["pulse"],
        "dmg_base": 22,
    },
    "whirlwind": {
        "title": "Вихрь",
        "desc": "Удерживай ПКМ — вращающаяся атака вокруг героя.",
        "mana": SkillSystem.MANA_COSTS["whirlwind"],
        "cd": 0,
        "dmg_base": 11,
        "mana_note": "мана / сек",
    },
}


def _fmt_stat(v: float) -> str:
    return str(int(v)) if v == int(v) else f"{v:.1f}"


def item_tooltip_rows(item: Item, player: PlayerEntity, *, compare_slot: EquipmentSlot | None = None) -> list[tuple[str, tuple[int, int, int]]]:
    """Build colored tooltip lines with optional comparison to equipped item."""
    rows: list[tuple[str, tuple[int, int, int]]] = []
    rows.append((item.display_name(), item.color))
    rows.append((f"Уровень {item.level}", UI_TEXT_DIM))
    if item.description:
        rows.append((item.description, UI_TEXT_DIM))

    equipped: Item | None = None
    if compare_slot is not None:
        equipped = player.equipment.slots.get(compare_slot)
        if equipped and equipped.uid != item.uid:
            rows.append(("— сравнение с надетым —", UI_ACCENT))
        elif equipped and equipped.uid == item.uid:
            rows.append(("Сейчас надето", UI_ACCENT))
    elif item.slot:
        rows.append((f"Слот: {item.slot.value}", UI_TEXT_DIM))

    stat_keys = set(item.stats.keys())
    if equipped:
        stat_keys |= set(equipped.stats.keys())

    for key in sorted(stat_keys):
        label = STAT_LABELS.get(key, key)
        new_v = item.stats.get(key, 0.0)
        old_v = equipped.stats.get(key, 0.0) if equipped else 0.0
        diff = new_v - old_v

        if equipped and item.slot == compare_slot:
            if diff > 0.01:
                text = f"+{_fmt_stat(new_v)} {label}  (↑ +{_fmt_stat(diff)})"
                color = GOOD
            elif diff < -0.01:
                text = f"+{_fmt_stat(new_v)} {label}  (↓ {_fmt_stat(diff)})"
                color = BAD
            elif new_v > 0:
                text = f"+{_fmt_stat(new_v)} {label}  (=)"
                color = NEUTRAL
            else:
                continue
        elif new_v > 0:
            text = f"+{_fmt_stat(new_v)} {label}"
            color = UI_TEXT
        else:
            continue
        rows.append((text, color))

    qnames = {
        "normal": "Обычный",
        "magic": "Магический",
        "rare": "Редкий",
        "legendary": "Легендарный",
        "set": "Сетовый",
    }
    rows.append((qnames.get(item.quality.value, ""), item.color))
    return rows


def skill_tooltip_rows(skill_id: str, player: PlayerEntity, cd: float = 0.0) -> list[tuple[str, tuple[int, int, int]]]:
    info = SKILL_INFO.get(skill_id, {})
    title = info.get("title", skill_id)
    rows: list[tuple[str, tuple[int, int, int]]] = [(title, UI_ACCENT)]
    if info.get("desc"):
        rows.append((info["desc"], UI_TEXT_DIM))

    lvl = player.experience.level
    base = info.get("dmg_base", 0)
    if base > 0 and skill_id != "summon":
        est = base * (1.0 + (lvl - 1) * 0.14) + player.damage * 0.35
        rows.append((f"~{int(est)} урона (ур. {lvl})", UI_TEXT))
    elif skill_id == "summon":
        rows.append((f"Прислужник ~{int(base * (1 + (lvl - 1) * 0.14))} урона", UI_TEXT))

    mana = info.get("mana", 0)
    mana_note = info.get("mana_note", "мана")
    rows.append((f"Стоимость: {int(mana)} {mana_note}", UI_TEXT_DIM))

    max_cd = info.get("cd", 0)
    if max_cd > 0:
        cd_line = f"Кулдаун: {max_cd:.1f}с"
        if cd > 0:
            cd_line += f"  (осталось {cd:.1f}с)"
        rows.append((cd_line, (255, 180, 100) if cd > 0 else UI_TEXT_DIM))
    return rows


class TooltipDrawer:
    MAX_W = 300
    PAD = 10
    LINE_H = 18

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer

    def draw_at(
        self,
        anchor: tuple[int, int],
        rows: list[tuple[str, tuple[int, int, int]]],
        *,
        prefer_above: bool = False,
    ) -> None:
        if not rows:
            return
        r = self.renderer
        surfaces: list[pygame.Surface] = []
        max_w = 0
        total_h = self.PAD * 2
        for text, color in rows:
            if not text:
                continue
            font = r.font_small if len(text) > 36 else r.font_label
            surf = font.render(text, True, color)
            surfaces.append(surf)
            max_w = max(max_w, surf.get_width())
            total_h += self.LINE_H

        box_w = min(self.MAX_W, max_w + self.PAD * 2)
        box_h = total_h
        ax, ay = anchor

        x = ax + 16
        y = ay - box_h - 12 if prefer_above else ay - box_h // 2
        if x + box_w > SCREEN_WIDTH - 8:
            x = ax - box_w - 16
        if y < 8:
            y = ay + 20
        if y + box_h > SCREEN_HEIGHT - 8:
            y = SCREEN_HEIGHT - box_h - 8

        rect = pygame.Rect(x, y, box_w, box_h)
        r.draw_panel(rect, alpha=248, fill=(18, 20, 32), border=UI_PANEL_BORDER, radius=8)

        ty = rect.top + self.PAD
        for surf in surfaces:
            r.screen.blit(surf, (rect.left + self.PAD, ty))
            ty += self.LINE_H
