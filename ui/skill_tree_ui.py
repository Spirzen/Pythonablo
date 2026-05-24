"""Passive skill tree screen — 10 stackable slots."""

from __future__ import annotations

import pygame

from core.config import SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_CARD_HOVER, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer
from entities.player import PlayerEntity
from player.passive_defs import MAX_RANK_PER_SLOT, STAT_POOL
from ui.styles import UIStyles


class SkillTreeUI:
    ROW_H = 48

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self.selected = 0
        self._slot_rects: list[tuple[pygame.Rect, str]] = []

    def _slot_keys(self) -> list[str]:
        return [key for key, _ in STAT_POOL]

    def handle_click(self, pos: tuple[int, int], player: PlayerEntity) -> bool:
        for rect, stat_key in self._slot_rects:
            if rect.collidepoint(pos):
                return player.skill_tree.invest(stat_key)
        return False

    def handle_input(self, up: bool, down: bool, confirm: bool, player: PlayerEntity) -> bool:
        keys = self._slot_keys()
        if not keys:
            return False
        if up:
            self.selected = max(0, self.selected - 1)
        if down:
            self.selected = min(len(keys) - 1, self.selected + 1)
        if confirm:
            return player.skill_tree.invest(keys[self.selected])
        return False

    def draw(self, player: PlayerEntity) -> None:
        r = self.renderer
        UIStyles.blit_dim(r.screen, 210)

        r.blit_text_outlined(
            r.font_huge, "ПАССИВНЫЕ НАВЫКИ", UI_TEXT,
            (SCREEN_WIDTH // 2 - 200, 40), outline=(20, 20, 40), outline_width=3,
        )
        r.blit_centered(
            r.font_mid,
            f"Очков: {player.skill_tree.unspent_points}  ·  Вложено: {player.skill_tree.unlocked_count()}/{MAX_RANK_PER_SLOT * len(STAT_POOL)}",
            UI_ACCENT,
            SCREEN_WIDTH // 2,
            95,
        )
        r.blit_centered(
            r.font_small,
            "Каждый ранг: +1% к параметру. Можно вкладывать в одну позицию до 10 раз.",
            UI_TEXT_DIM,
            SCREEN_WIDTH // 2,
            122,
        )

        panel_w = 720
        start_y = 150
        self._slot_rects = []
        mx, my = pygame.mouse.get_pos()
        keys = self._slot_keys()

        for i, stat_key in enumerate(keys):
            slot = player.skill_tree.slots[stat_key]
            rect = pygame.Rect(SCREEN_WIDTH // 2 - panel_w // 2, start_y + i * self.ROW_H, panel_w, self.ROW_H - 4)
            self._slot_rects.append((rect, stat_key))
            selected = i == self.selected
            hovered = rect.collidepoint(mx, my)
            can_invest = player.skill_tree.unspent_points >= 1 and slot.rank < MAX_RANK_PER_SLOT

            if slot.rank >= MAX_RANK_PER_SLOT:
                fill = (40, 70, 50)
            elif can_invest and (selected or hovered):
                fill = UI_CARD_HOVER
            else:
                fill = UI_CARD

            surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*fill, 240), (0, 0, rect.w, rect.h), border_radius=8)
            border_c = UI_ACCENT if slot.rank > 0 else (UI_ACCENT if can_invest and selected else UI_PANEL_BORDER)
            pygame.draw.rect(surf, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=8)
            r.screen.blit(surf, rect.topleft)

            bar_w = 180
            bar_x = rect.right - bar_w - 16
            bar_y = rect.centery - 6
            pygame.draw.rect(r.screen, (30, 32, 48), (bar_x, bar_y, bar_w, 12), border_radius=4)
            if slot.rank > 0:
                fill_w = int(bar_w * slot.rank / MAX_RANK_PER_SLOT)
                pygame.draw.rect(r.screen, UI_ACCENT, (bar_x, bar_y, fill_w, 12), border_radius=4)

            rank_label = r.font_small.render(f"{slot.rank}/{MAX_RANK_PER_SLOT}", True, UI_ACCENT if slot.rank else UI_TEXT_DIM)
            r.screen.blit(rank_label, (bar_x + bar_w + 8, rect.centery - rank_label.get_height() // 2))

            bonus_pct = slot.rank
            title = r.font_menu.render(f"{slot.label}  (+{bonus_pct}%)", True, UI_ACCENT if slot.rank else UI_TEXT)
            r.screen.blit(title, (rect.x + 12, rect.centery - title.get_height() // 2))

        r.blit_centered(
            r.font_small,
            "↑/↓ — выбор  ·  ENTER / клик — вложить очко  ·  ESC — закрыть",
            UI_TEXT_DIM,
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 36,
        )
