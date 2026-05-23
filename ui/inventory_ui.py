"""Inventory and equipment UI — combined view with disintegrate."""

from __future__ import annotations

import pygame

from core.config import EquipmentSlot, SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_CARD_HOVER, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer
from entities.player import PlayerEntity
from player.equipment import ALL_SLOTS, SLOT_LABELS
from player.inventory import Inventory, Item
from systems.loot_system import LootSystem
from ui.tooltip import TooltipDrawer, item_tooltip_rows


class InventoryUI:
    CELL = 36
    CELL_GAP = 4
    SLOT_W = 68
    SLOT_H = 32
    LABEL_H = 18

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
        for slot in ALL_SLOTS:
            item = player.equipment.slots.get(slot)
            if item:
                self.loot.disintegrate_item(player, item)
                player.equipment.slots[slot] = None

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
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 235))
        r.screen.blit(overlay, (0, 0))

        panel_w, panel_h = 1180, 640
        self._panel = pygame.Rect(SCREEN_WIDTH // 2 - panel_w // 2, SCREEN_HEIGHT // 2 - panel_h // 2, panel_w, panel_h)
        r.draw_panel(self._panel, alpha=245)

        r.blit_centered(r.font_big, "ИНВЕНТАРЬ", UI_ACCENT, self._panel.centerx, self._panel.top + 14)
        r.blit_centered(
            r.font_small,
            "ЛКМ — надеть/снять  ·  ПКМ — распылить  ·  ESC — закрыть",
            UI_TEXT_DIM,
            self._panel.centerx,
            self._panel.top + 44,
        )

        self._draw_combined(r, player)

        # Footer: gold, dust, disintegrate all button
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
        btn_label = r.font_menu.render("Распылить всё", True, (255, 160, 120) if hovered else UI_TEXT)
        r.screen.blit(btn_label, btn_label.get_rect(center=self._disintegrate_all_btn.center))

        hover = self._hover_target(player)
        if hover:
            item, slot, _ = hover
            rows = item_tooltip_rows(item, player, compare_slot=slot)
            rows.append((f"ПКМ — распылить (+{LootSystem.dust_for_item(item)} пыли)", UI_TEXT_DIM))
            self.tooltips.draw_at(self._mouse_pos, rows, prefer_above=True)

    def _content_rect(self) -> pygame.Rect:
        return pygame.Rect(
            self._panel.left + 16,
            self._panel.top + 64,
            self._panel.width - 32,
            self._panel.height - 120,
        )

    def _grid_slot_rects(self) -> list[pygame.Rect]:
        content = self._content_rect()
        cols, rows = Inventory.GRID_W, Inventory.GRID_H
        grid_w = cols * self.CELL + (cols - 1) * self.CELL_GAP
        grid_h = rows * self.CELL + (rows - 1) * self.CELL_GAP
        ox = content.left + 8
        oy = content.top + (content.height - grid_h) // 2
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

    def _equipment_layout(self) -> dict:
        c = self._content_rect()
        cx = c.right - 280
        cy = c.centery + 8
        return {
            ALL_SLOTS[0]: (cx, cy - 130),
            ALL_SLOTS[1]: (cx - 96, cy - 78),
            ALL_SLOTS[2]: (cx, cy - 58),
            ALL_SLOTS[3]: (cx - 96, cy + 8),
            ALL_SLOTS[4]: (cx, cy + 48),
            ALL_SLOTS[5]: (cx, cy + 88),
            ALL_SLOTS[6]: (cx, cy + 128),
            ALL_SLOTS[7]: (cx + 96, cy - 78),
            ALL_SLOTS[8]: (cx - 46, cy + 128),
            ALL_SLOTS[9]: (cx + 46, cy + 128),
            ALL_SLOTS[10]: (cx + 96, cy - 18),
            ALL_SLOTS[11]: (cx - 96, cy + 58),
            ALL_SLOTS[12]: (cx + 96, cy + 58),
            ALL_SLOTS[13]: (cx - 170, cy + 8),
            ALL_SLOTS[14]: (cx + 170, cy + 8),
            ALL_SLOTS[15]: (cx - 170, cy - 38),
            ALL_SLOTS[16]: (cx + 170, cy - 38),
            ALL_SLOTS[17]: (cx, cy - 168),
        }

    def _equipment_slot_rects(self) -> dict:
        half_w, half_h = self.SLOT_W // 2, self.SLOT_H // 2
        return {
            slot: pygame.Rect(int(x) - half_w, int(y) - half_h, self.SLOT_W, self.SLOT_H)
            for slot, (x, y) in self._equipment_layout().items()
        }

    def _draw_combined(self, r: Renderer, player: PlayerEntity) -> None:
        content = self._content_rect()
        mx, my = self._mouse_pos

        # Bag label
        bag_label = r.font_menu.render("Сумка", True, UI_ACCENT)
        grid_rects = self._grid_slot_rects()
        if grid_rects:
            r.screen.blit(bag_label, bag_label.get_rect(midbottom=(grid_rects[0].left + 180, grid_rects[0].top - 6)))

        for i, rect in enumerate(grid_rects):
            hovered = rect.collidepoint(mx, my)
            pygame.draw.rect(r.screen, (32, 36, 52) if hovered else (22, 24, 36), rect, border_radius=5)
            border = UI_ACCENT if hovered else UI_PANEL_BORDER
            pygame.draw.rect(r.screen, border, rect, width=2 if hovered else 1, border_radius=5)
            item = player.inventory.slots[i]
            if item:
                inner = rect.inflate(-4, -4)
                pygame.draw.rect(r.screen, item.color, inner, border_radius=3)
                short = item.name[:3].upper()
                t = r.font_label.render(short, True, (20, 22, 30))
                r.screen.blit(t, t.get_rect(center=inner.center))

        # Divider
        div_x = content.left + 420
        pygame.draw.line(r.screen, UI_PANEL_BORDER, (div_x, content.top), (div_x, content.bottom), 2)

        # Equipment label
        eq_label = r.font_menu.render("Снаряжение", True, UI_ACCENT)
        eq_rects = self._equipment_slot_rects()
        if eq_rects:
            first = next(iter(eq_rects.values()))
            r.screen.blit(eq_label, eq_label.get_rect(midbottom=(first.centerx + 80, first.top - 24)))

        c = self._content_rect()
        cx = c.right - 280
        cy = c.centery + 8
        pygame.draw.ellipse(r.screen, (32, 36, 52), (cx - 24, cy - 36, 48, 62))
        pygame.draw.circle(r.screen, (32, 36, 52), (cx, cy - 52), 16)

        for slot, rect in eq_rects.items():
            hovered = rect.collidepoint(mx, my)
            label = SLOT_LABELS[slot]
            if len(label) > 10:
                label = label[:9] + "…"
            lbl = r.font_label.render(label, True, UI_TEXT_DIM)
            r.screen.blit(lbl, lbl.get_rect(midbottom=(rect.centerx, rect.top - 1)))

            fill = (48, 52, 72) if hovered else UI_CARD
            pygame.draw.rect(r.screen, fill, rect, border_radius=6)
            border = UI_ACCENT if hovered else UI_PANEL_BORDER
            pygame.draw.rect(r.screen, border, rect, width=2 if hovered else 1, border_radius=6)

            item = player.equipment.slots.get(slot)
            if item:
                inner = rect.inflate(-4, -4)
                pygame.draw.rect(r.screen, item.color, inner, border_radius=4)
                name = item.name[:6]
                t = r.font_label.render(name, True, (20, 22, 30))
                if t.get_width() > inner.width - 4:
                    t = r.font_label.render(name[:4] + "…", True, (20, 22, 30))
                r.screen.blit(t, t.get_rect(center=inner.center))
