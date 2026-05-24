"""Merchant / blacksmith — random shop, upgrade, reroll."""

from __future__ import annotations

import pygame

from core.config import ItemCategory, SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_CARD_HOVER, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer
from entities.player import PlayerEntity
from player.inventory import Item
from systems.loot_system import LootSystem


class MerchantUI:
    DUST_ITEM_COST = 12
    GOLD_ITEM_COST = 35
    UPGRADE_COST = 10
    REROLL_COST = 10

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self.tab = 0  # 0 shop, 1 services
        self.selected = 0
        self._rects: list[tuple[pygame.Rect, str, object]] = []
        self.message: str | None = None
        self.message_timer: float = 0.0
        self.dust_items: list[Item] = []
        self.gold_item: Item | None = None
        self.selected_inv_index: int | None = None
        self._loot: LootSystem | None = None
        self._floor: int = 1

    def set_loot_system(self, loot: LootSystem) -> None:
        self._loot = loot

    def open(self, floor: int) -> None:
        self.tab = 0
        self.selected = 0
        self.selected_inv_index = None
        self.message = None
        self.message_timer = 0.0
        self._floor = floor
        if self._loot:
            self.dust_items, self.gold_item = self._loot.generate_shop_items(floor)

    def update(self, dt: float) -> None:
        if self.message_timer > 0:
            self.message_timer -= dt
            if self.message_timer <= 0:
                self.message = None

    def _shop_entries(self) -> list[tuple[str, str, str, int, Item | None]]:
        entries: list[tuple[str, str, str, int, Item | None]] = []
        for i, item in enumerate(self.dust_items):
            entries.append((f"dust_{i}", item.display_name(), "dust", self.DUST_ITEM_COST, item))
        if self.gold_item:
            entries.append(("gold_0", self.gold_item.display_name(), "gold", self.GOLD_ITEM_COST, self.gold_item))
        return entries

    def _can_afford(self, player: PlayerEntity, currency: str, cost: int) -> bool:
        if currency == "gold":
            return player.inventory.gold >= cost
        return player.inventory.dust >= cost

    def _purchase_shop(self, player: PlayerEntity, offer_id: str) -> bool:
        for oid, label, currency, cost, item in self._shop_entries():
            if oid != offer_id or item is None:
                continue
            if not self._can_afford(player, currency, cost):
                self.message = "Недостаточно ресурсов!"
                self.message_timer = 2.0
                return False
            if not player.inventory.add_item(item):
                self.message = "Инвентарь полон!"
                self.message_timer = 2.0
                return False
            if currency == "gold":
                player.inventory.gold -= cost
                self.gold_item = None
            else:
                player.inventory.dust -= cost
                idx = int(oid.split("_")[1])
                if 0 <= idx < len(self.dust_items):
                    self.dust_items.pop(idx)
            self.message = f"Куплено: {label}"
            self.message_timer = 2.5
            return True
        return False

    def _selected_item(self, player: PlayerEntity) -> Item | None:
        if self.selected_inv_index is None:
            return None
        if 0 <= self.selected_inv_index < len(player.inventory.slots):
            return player.inventory.slots[self.selected_inv_index]
        return None

    def _upgrade_selected(self, player: PlayerEntity) -> bool:
        item = self._selected_item(player)
        if not item:
            self.message = "Выберите предмет в инвентаре"
            self.message_timer = 2.0
            return False
        if item.category == ItemCategory.CONSUMABLE:
            self.message = "Нельзя улучшить расходник"
            self.message_timer = 2.0
            return False
        if player.inventory.gold < self.UPGRADE_COST:
            self.message = "Нужно 10 золота"
            self.message_timer = 2.0
            return False
        if not self._loot:
            return False
        player.inventory.gold -= self.UPGRADE_COST
        self._loot.upgrade_item(item)
        self.message = f"{item.display_name()} улучшен (+10%)"
        self.message_timer = 2.5
        return True

    def _reroll_selected(self, player: PlayerEntity) -> bool:
        item = self._selected_item(player)
        if not item:
            self.message = "Выберите предмет в инвентаре"
            self.message_timer = 2.0
            return False
        if item.category == ItemCategory.CONSUMABLE:
            self.message = "Нельзя перековать расходник"
            self.message_timer = 2.0
            return False
        if player.inventory.dust < self.REROLL_COST:
            self.message = "Нужно 10 пыли"
            self.message_timer = 2.0
            return False
        if not self._loot:
            return False
        player.inventory.dust -= self.REROLL_COST
        self._loot.reroll_item(item)
        self.message = f"Свойства перекованы: {item.display_name()}"
        self.message_timer = 2.5
        return True

    def handle_click(self, pos: tuple[int, int], player: PlayerEntity) -> bool:
        mx, my = pos
        for rect, action, payload in self._rects:
            if not rect.collidepoint(mx, my):
                continue
            if action == "tab":
                self.tab = payload
                self.selected = 0
                return True
            if action == "buy":
                return self._purchase_shop(player, payload)
            if action == "pick":
                self.selected_inv_index = payload
                return True
            if action == "upgrade":
                return self._upgrade_selected(player)
            if action == "reroll":
                return self._reroll_selected(player)
        return False

    def handle_input(self, up: bool, down: bool, confirm: bool, player: PlayerEntity) -> bool:
        if self.tab == 0:
            entries = self._shop_entries()
            if up:
                self.selected = max(0, self.selected - 1)
            if down:
                self.selected = min(max(0, len(entries) - 1), self.selected + 1)
            if confirm and entries:
                return self._purchase_shop(player, entries[self.selected][0])
        else:
            inv_indices = [i for i, s in enumerate(player.inventory.slots) if s is not None]
            if up and inv_indices:
                if self.selected_inv_index in inv_indices:
                    idx = inv_indices.index(self.selected_inv_index)
                    self.selected_inv_index = inv_indices[max(0, idx - 1)]
                else:
                    self.selected_inv_index = inv_indices[0]
            if down and inv_indices:
                if self.selected_inv_index in inv_indices:
                    idx = inv_indices.index(self.selected_inv_index)
                    self.selected_inv_index = inv_indices[min(len(inv_indices) - 1, idx + 1)]
                else:
                    self.selected_inv_index = inv_indices[0]
        return False

    def draw(self, player: PlayerEntity, npc_name: str = "Кузнец") -> None:
        r = self.renderer
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 215))
        r.screen.blit(overlay, (0, 0))

        r.blit_text_outlined(
            r.font_huge, npc_name.upper(), UI_ACCENT,
            (SCREEN_WIDTH // 2 - 120, 50), outline=(30, 20, 10), outline_width=2,
        )
        r.blit_centered(
            r.font_mid,
            f"Золото: {player.inventory.gold}   Пыль: {player.inventory.dust}",
            UI_TEXT, SCREEN_WIDTH // 2, 105,
        )

        tab_y = 140
        tab_w = 200
        self._rects = []
        for i, label in enumerate(("Магазин", "Улучшение")):
            rect = pygame.Rect(SCREEN_WIDTH // 2 - tab_w - 10 + i * (tab_w + 20), tab_y, tab_w, 36)
            self._rects.append((rect, "tab", i))
            fill = UI_CARD_HOVER if self.tab == i else UI_CARD
            surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            border_c = UI_ACCENT if self.tab == i else UI_PANEL_BORDER
            pygame.draw.rect(surf, (*fill, 240), (0, 0, rect.w, rect.h), border_radius=8)
            pygame.draw.rect(surf, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=8)
            r.screen.blit(surf, rect.topleft)
            t = r.font_menu.render(label, True, UI_ACCENT if self.tab == i else UI_TEXT)
            r.screen.blit(t, t.get_rect(center=rect.center))

        panel_w = 680
        start_y = 195
        mx, my = pygame.mouse.get_pos()

        if self.tab == 0:
            entries = self._shop_entries()
            if not entries:
                r.blit_centered(r.font_mid, "Товары распроданы — зайдите позже", UI_TEXT_DIM, SCREEN_WIDTH // 2, start_y + 80)
            for i, (oid, label, currency, cost, item) in enumerate(entries):
                rect = pygame.Rect(SCREEN_WIDTH // 2 - panel_w // 2, start_y + i * 50, panel_w, 42)
                self._rects.append((rect, "buy", oid))
                selected = i == self.selected
                hovered = rect.collidepoint(mx, my)
                affordable = self._can_afford(player, currency, cost)
                fill = UI_CARD_HOVER if selected or hovered else UI_CARD
                if not affordable:
                    fill = (28, 28, 38)
                surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                pygame.draw.rect(surf, (*fill, 240), (0, 0, rect.w, rect.h), border_radius=10)
                border_c = UI_ACCENT if selected and affordable else UI_PANEL_BORDER
                pygame.draw.rect(surf, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=10)
                r.screen.blit(surf, rect.topleft)
                cur_label = "зол." if currency == "gold" else "пыль"
                tag = " [ЗОЛОТО]" if currency == "gold" else ""
                color = UI_TEXT if affordable else UI_TEXT_DIM
                text = r.font_menu.render(f"{label}{tag}  —  {cost} {cur_label}", True, color)
                r.screen.blit(text, text.get_rect(center=rect.center))
            r.blit_centered(r.font_small, "3 случайных предмета за пыль · 1 редкий за золото", UI_TEXT_DIM, SCREEN_WIDTH // 2, start_y + len(entries) * 50 + 20)
        else:
            r.blit_centered(r.font_mid, "Выберите предмет из инвентаря", UI_TEXT_DIM, SCREEN_WIDTH // 2, start_y - 10)
            row = 0
            for i, item in enumerate(player.inventory.slots):
                if item is None:
                    continue
                rect = pygame.Rect(SCREEN_WIDTH // 2 - panel_w // 2, start_y + row * 44, panel_w, 38)
                self._rects.append((rect, "pick", i))
                picked = self.selected_inv_index == i
                hovered = rect.collidepoint(mx, my)
                fill = UI_CARD_HOVER if picked or hovered else UI_CARD
                surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                pygame.draw.rect(surf, (*fill, 240), (0, 0, rect.w, rect.h), border_radius=8)
                border_c = UI_ACCENT if picked else UI_PANEL_BORDER
                pygame.draw.rect(surf, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=8)
                r.screen.blit(surf, rect.topleft)
                t = r.font_menu.render(item.display_name(), True, item.color)
                r.screen.blit(t, t.get_rect(midleft=(rect.x + 14, rect.centery)))
                row += 1

            btn_y = start_y + max(row, 1) * 44 + 16
            upgrade_rect = pygame.Rect(SCREEN_WIDTH // 2 - panel_w // 2, btn_y, panel_w // 2 - 8, 44)
            reroll_rect = pygame.Rect(SCREEN_WIDTH // 2 + 8, btn_y, panel_w // 2 - 8, 44)
            self._rects.append((upgrade_rect, "upgrade", None))
            self._rects.append((reroll_rect, "reroll", None))
            for rect, label, cost_txt in (
                (upgrade_rect, f"Улучшить (+10%) — {self.UPGRADE_COST} зол.", "gold"),
                (reroll_rect, f"Перековать — {self.REROLL_COST} пыль", "dust"),
            ):
                hovered = rect.collidepoint(mx, my)
                fill = UI_CARD_HOVER if hovered else UI_CARD
                surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                pygame.draw.rect(surf, (*fill, 240), (0, 0, rect.w, rect.h), border_radius=10)
                pygame.draw.rect(surf, (*UI_ACCENT, 255), (0, 0, rect.w, rect.h), width=2, border_radius=10)
                r.screen.blit(surf, rect.topleft)
                t = r.font_menu.render(label, True, UI_TEXT)
                r.screen.blit(t, t.get_rect(center=rect.center))

        if self.message:
            r.blit_centered(r.font_mid, self.message, UI_ACCENT, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 100)

        r.blit_centered(
            r.font_small,
            "↑/↓ — выбор  ·  ENTER / клик  ·  ESC — закрыть",
            UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40,
        )
