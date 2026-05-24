"""Pause menu overlay."""

from __future__ import annotations

import pygame

from core.config import SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_CARD_HOVER, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer
from ui.styles import UIStyles


class PauseUI:
    ITEMS = [
        ("Продолжить", "resume"),
        ("Сохранить", "save"),
        ("Навыки (у наставника)", "skills"),
        ("Автоподбор: ВЫКЛ", "toggle_autopickup"),
        ("В меню", "menu"),
    ]

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self.selected = 0
        self._rects: list[tuple[pygame.Rect, str]] = []

    def handle_input(self, up: bool, down: bool, confirm: bool) -> str | None:
        if up:
            self.selected = max(0, self.selected - 1)
        if down:
            self.selected = min(len(self.ITEMS) - 1, self.selected + 1)
        if confirm:
            return self.ITEMS[self.selected][1]
        return None

    def handle_click(self, pos: tuple[int, int], player=None) -> str | None:
        for i, (rect, action) in enumerate(self._rects):
            if rect.collidepoint(pos):
                self.selected = i
                if action == "toggle_autopickup" and player is not None:
                    player.settings.auto_pickup = not player.settings.auto_pickup
                    return "toggle_autopickup"
                return action
        return None

    def draw(self, player=None) -> None:
        r = self.renderer
        UIStyles.blit_dim(r.screen, 190)

        r.blit_text_outlined(r.font_huge, "ПАУЗА", UI_TEXT, (SCREEN_WIDTH // 2 - 100, 120), outline=(20, 20, 40), outline_width=3)
        r.blit_centered(r.font_small, "ESC — продолжить", UI_TEXT_DIM, SCREEN_WIDTH // 2, 190)

        items = list(self.ITEMS)
        if player is not None and player.skill_upgrades.pending_points > 0:
            items = items[:3] + [("Улучшение навыков", "skill_upgrade")] + items[3:]

        menu_w, item_h, gap = 420, 48, 10
        start_y = 230
        self._rects = []
        mx, my = pygame.mouse.get_pos()
        for i, (label, action) in enumerate(items):
            if action == "toggle_autopickup" and player is not None:
                on = player.settings.auto_pickup
                label = f"Автоподбор: {'ВКЛ' if on else 'ВЫКЛ'}"
            rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_w // 2, start_y + i * (item_h + gap), menu_w, item_h)
            self._rects.append((rect, action))
            selected = i == self.selected
            hovered = rect.collidepoint(mx, my)
            fill = UI_CARD_HOVER if selected or hovered else UI_CARD
            surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*fill, 245), (0, 0, rect.w, rect.h), border_radius=12)
            border_c = UI_ACCENT if selected else UI_PANEL_BORDER
            pygame.draw.rect(surf, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=12)
            r.screen.blit(surf, rect.topleft)
            color = UI_ACCENT if selected else UI_TEXT
            text = r.font_menu.render(label, True, color)
            r.screen.blit(text, text.get_rect(center=rect.center))
