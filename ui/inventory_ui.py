"""Inventory and equipment UI — combined view with disintegrate."""

from __future__ import annotations

import pygame

from core.config import ARCANE_SET_SLOTS, EquipmentSlot, SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_CARD_HOVER, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer
from entities.player import PlayerEntity
from player.equipment import SLOT_LABELS
from player.inventory import Inventory, Item
from systems.loot_system import LootSystem
from ui.tooltip import TooltipDrawer, item_tooltip_rows
from ui.styles import UIStyles

# Equipment panel layout — two columns + set row (no overlaps)
_ARMOR_COL = [
    EquipmentSlot.HELMET,
    EquipmentSlot.SHOULDERS,
    EquipmentSlot.CHEST,
    EquipmentSlot.GLOVES,
    EquipmentSlot.BELT,
    EquipmentSlot.PANTS,
    EquipmentSlot.BOOTS,
]
_MISC_COL = [
    EquipmentSlot.AMULET,
    EquipmentSlot.RING_LEFT,
    EquipmentSlot.RING_RIGHT,
    EquipmentSlot.TALISMAN,
    EquipmentSlot.WEAPON_MAIN,
    EquipmentSlot.WEAPON_OFF,
]


class InventoryUI:
    CELL = 36
    CELL_GAP = 4
    SLOT_W = 76
    SLOT_H = 30
    SLOT_COL_GAP = 28
    SLOT_ROW_GAP = 10
    LABEL_H = 15

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self.tooltips = TooltipDrawer(renderer)
        self._panel = pygame.Rect(0, 0, 0, 0)
        self._disintegrate_all_btn = pygame.Rect(0, 0, 0, 0)
        self._mouse_pos = (0, 0)
        self.loot: LootSystem | None = None

    def set_loot_system(self, loot: LootSystem) -> None:
        self.loot = loot

    def handle_click(self, pos: tuple[int, int], player: PlayerEntity, button: int = 1) -> None:
        mx, my = pos
        if button == 3:
            self.handle_disintegrate(pos, player)
            return
        if button == 1 and self._disintegrate_all_btn.collidepoint(mx, my):
            self._disintegrate_all(player)
            return

        for i, rect in enumerate(self._grid_slot_rects()):
            if rect.collidepoint(mx, my):
                item = player.inventory.slots[i]
                if item and item.slot:
                    prev = player.equipment.equip(item)
                    player.inventory.slots[i] = prev
                return

        for slot, rect in self._equipment_slot_rects().items():
            if rect.collidepoint(mx, my):
                item = player.equipment.unequip(slot)
                if item and not player.inventory.add_item(item):
                    player.equipment.equip(item)
                return

    def handle_disintegrate(self, pos: tuple[int, int], player: PlayerEntity) -> None:
        if not self.loot:
            return
        mx, my = pos
        for i, rect in enumerate(self._grid_slot_rects()):
            if rect.collidepoint(mx, my):
                item = player.inventory.remove_at(i)
                if item:
                    self.loot.disintegrate_item(player, item)
                return
        for slot, rect in self._equipment_slot_rects().items():
            if rect.collidepoint(mx, my):
                item = player.equipment.unequip(slot)
                if item:
                    self.loot.disintegrate_item(player, item)
                return

    def _disintegrate_all(self, player: PlayerEntity) -> None:
        if not self.loot:
            return
        for i, item in enumerate(player.inventory.slots):
            if item:
                self.loot.disintegrate_item(player, item)
                player.inventory.slots[i] = None

    def _hover_target(self, player: PlayerEntity) -> tuple[Item, EquipmentSlot | None, bool] | None:
        mx, my = self._mouse_pos
        for i, rect in enumerate(self._grid_slot_rects()):
            if rect.collidepoint(mx, my):
                item = player.inventory.slots[i]
                if item:
                    return item, item.slot, True
                return None
        for slot, rect in self._equipment_slot_rects().items():
            if rect.collidepoint(mx, my):
                item = player.equipment.slots.get(slot)
                if item:
                    return item, slot, True
                return None
        return None

    def draw(self, player: PlayerEntity, mouse_pos: tuple[int, int] | None = None) -> None:
        if mouse_pos:
            self._mouse_pos = mouse_pos
        r = self.renderer
        UIStyles.blit_dim(r.screen, 235)

        panel_w, panel_h = 1180, 660
        self._panel = pygame.Rect(SCREEN_WIDTH // 2 - panel_w // 2, SCREEN_HEIGHT // 2 - panel_h // 2, panel_w, panel_h)
        r.draw_panel(self._panel, alpha=245)

        r.blit_centered(r.font_big, "ИНВЕНТАРЬ", UI_ACCENT, self._panel.centerx, self._panel.top + 10)
        r.blit_centered(
            r.font_small,
            "ЛКМ — надеть/снять  ·  ПКМ — распылить  ·  ESC — закрыть",
            UI_TEXT_DIM,
            self._panel.centerx,
            self._panel.top + 52,
        )

        self._draw_combined(r, player)

        footer_y = self._panel.bottom - 32
        gold = r.font_menu.render(f"Золото: {player.inventory.gold}", True, UI_ACCENT)
        r.screen.blit(gold, gold.get_rect(midleft=(self._panel.left + 24, footer_y)))

        dust = r.font_menu.render(f"Пыль: {player.inventory.dust}", True, (180, 140, 255))
        r.screen.blit(dust, dust.get_rect(midleft=(self._panel.left + 180, footer_y)))

        set_pieces = player.equipment.count_set_pieces()
        if set_pieces > 0:
            set_txt = r.font_small.render(f"Комплект: {set_pieces}/5", True, (60, 200, 90))
            r.screen.blit(set_txt, set_txt.get_rect(midleft=(self._panel.left + 320, footer_y)))

        btn_w, btn_h = 220, 36
        self._disintegrate_all_btn = pygame.Rect(self._panel.right - btn_w - 24, footer_y - btn_h // 2, btn_w, btn_h)
        hovered = self._disintegrate_all_btn.collidepoint(self._mouse_pos)
        fill = UI_CARD_HOVER if hovered else UI_CARD
        surf = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*fill, 240), (0, 0, btn_w, btn_h), border_radius=8)
        pygame.draw.rect(surf, ((255, 120, 80, 255) if hovered else (*UI_PANEL_BORDER, 255)), (0, 0, btn_w, btn_h), width=2, border_radius=8)
        r.screen.blit(surf, self._disintegrate_all_btn.topleft)
        btn_label = r.font_menu.render("Распылить сумку", True, (255, 160, 120) if hovered else UI_TEXT)
        r.screen.blit(btn_label, btn_label.get_rect(center=self._disintegrate_all_btn.center))

        hover = self._hover_target(player)
        if hover:
            item, slot, _ = hover
            rows = item_tooltip_rows(item, player, compare_slot=slot)
            rows.append((f"ПКМ — распылить (+{LootSystem.dust_for_item(item)} пыли)", UI_TEXT_DIM))
            self.tooltips.draw_at(self._mouse_pos, rows, prefer_above=True)

    def _content_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self._panel.left + 20,
            self._panel.top + 78,
            self._panel.width - 40,
            self._panel.height - 148,
        )

    def _bag_zone(self) -> pygame.Rect:
        content = self._content_rect()
        grid_w = Inventory.GRID_W * self.CELL + (Inventory.GRID_W - 1) * self.CELL_GAP
        return pygame.Rect(content.left, content.top, grid_w + 16, content.height)

    def _divider_x(self) -> int:
        return self._bag_zone().right + 12

    def _equipment_zone(self) -> pygame.Rect:
        content = self._content_rect()
        div = self._divider_x()
        return pygame.Rect(div + 12, content.top, content.right - div - 12, content.height)

    def _grid_slot_rects(self) -> list[pygame.Rect]:
        zone = self._bag_zone()
        cols, rows = Inventory.GRID_W, Inventory.GRID_H
        grid_w = cols * self.CELL + (cols - 1) * self.CELL_GAP
        grid_h = rows * self.CELL + (rows - 1) * self.CELL_GAP
        ox = zone.left + (zone.width - grid_w) // 2
        oy = zone.top + 28 + (zone.height - 28 - grid_h) // 2
        rects = []
        for i in range(cols * rows):
            col = i % cols
            row = i // cols
            rects.append(
                pygame.Rect(
                    ox + col * (self.CELL + self.CELL_GAP),
                    oy + row * (self.CELL + self.CELL_GAP),
                    self.CELL,
                    self.CELL,
                )
            )
        return rects

    def _equipment_layout(self) -> dict[EquipmentSlot, tuple[int, int]]:
        zone = self._equipment_zone()
        row_h = self.LABEL_H + self.SLOT_H + self.SLOT_ROW_GAP
        set_row_h = self.LABEL_H + self.SLOT_H + 16
        set_slots = list(ARCANE_SET_SLOTS)
        set_row_w = len(set_slots) * self.SLOT_W + (len(set_slots) - 1) * 8
        cols_top = zone.top + 24
        cols_bottom = zone.bottom - set_row_h
        avail_h = cols_bottom - cols_top
        armor_rows = len(_ARMOR_COL)
        misc_rows = len(_MISC_COL)
        max_rows = max(armor_rows, misc_rows)
        total_h = max_rows * row_h - self.SLOT_ROW_GAP
        start_y = cols_top + max(0, (avail_h - total_h) // 2)

        left_x = zone.left + 8
        right_x = zone.left + self.SLOT_W + self.SLOT_COL_GAP + 8
        layout: dict[EquipmentSlot, tuple[int, int]] = {}

        for i, slot in enumerate(_ARMOR_COL):
            cy = start_y + i * row_h + self.LABEL_H + self.SLOT_H // 2
            layout[slot] = (left_x + self.SLOT_W // 2, cy)

        for i, slot in enumerate(_MISC_COL):
            cy = start_y + i * row_h + self.LABEL_H + self.SLOT_H // 2
            layout[slot] = (right_x + self.SLOT_W // 2, cy)

        set_y = zone.bottom - set_row_h + self.LABEL_H + self.SLOT_H // 2
        set_x0 = zone.centerx - set_row_w // 2 + self.SLOT_W // 2
        for i, slot in enumerate(set_slots):
            layout[slot] = (set_x0 + i * (self.SLOT_W + 8), set_y)

        return layout

    def _equipment_slot_rects(self) -> dict[EquipmentSlot, pygame.Rect]:
        layout = self._equipment_layout()
        half_w, half_h = self.SLOT_W // 2, self.SLOT_H // 2
        return {
            slot: pygame.Rect(int(x) - half_w, int(y) - half_h, self.SLOT_W, self.SLOT_H)
            for slot, (x, y) in layout.items()
        }

    def _draw_combined(self, r: Renderer, player: PlayerEntity) -> None:
        mx, my = self._mouse_pos
        grid_rects = self._grid_slot_rects()
        eq_rects = self._equipment_slot_rects()
        zone = self._bag_zone()
        eq_zone = self._equipment_zone()

        bag_label = r.font_menu.render("Сумка", True, UI_ACCENT)
        r.screen.blit(bag_label, bag_label.get_rect(midtop=(zone.centerx, zone.top + 4)))

        for i, rect in enumerate(grid_rects):
            hovered = rect.collidepoint(mx, my)
            item = player.inventory.slots[i]
            UIStyles.draw_item_cell(r.screen, rect, item, hovered=hovered, font=r.font_label)

        div_x = self._divider_x()
        content = self._content_rect()
        pygame.draw.line(r.screen, UI_PANEL_BORDER, (div_x, content.top), (div_x, content.bottom), 2)

        eq_label = r.font_menu.render("Снаряжение", True, UI_ACCENT)
        r.screen.blit(eq_label, eq_label.get_rect(midtop=(eq_zone.centerx, eq_zone.top + 4)))

        set_label = r.font_small.render("Комплект", True, UI_TEXT_DIM)
        set_slots = list(ARCANE_SET_SLOTS)
        if set_slots[0] in eq_rects:
            set_rect = eq_rects[set_slots[0]]
            r.screen.blit(set_label, set_label.get_rect(midbottom=(eq_zone.centerx, set_rect.top - self.LABEL_H - 2)))

        for slot, rect in eq_rects.items():
            hovered = rect.collidepoint(mx, my)
            label = SLOT_LABELS[slot]
            if len(label) > 11:
                label = label[:10] + "…"
            lbl = r.font_label.render(label, True, UI_TEXT_DIM)
            r.screen.blit(lbl, lbl.get_rect(midbottom=(rect.centerx, rect.top - 2)))

            fill = (48, 52, 72) if hovered else UI_CARD
            pygame.draw.rect(r.screen, fill, rect, border_radius=6)
            border = UI_ACCENT if hovered else UI_PANEL_BORDER
            pygame.draw.rect(r.screen, border, rect, width=2 if hovered else 1, border_radius=6)

            item = player.equipment.slots.get(slot)
            if item:
                inner = rect.inflate(-4, -4)
                UIStyles.draw_item_cell(r.screen, inner, item, hovered=hovered, font=r.font_label)
