"""Main menu and game over screens."""

from __future__ import annotations

import math

import pygame

from core.config import (
    DIFFICULTY_LABELS,
    GAME_MODE_DESCRIPTIONS,
    GAME_MODE_LABELS,
    GameMode,
    Difficulty,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    UI_ACCENT,
    UI_CARD,
    UI_CARD_HOVER,
    UI_HP_FILL,
    UI_PANEL_BORDER,
    UI_TEXT,
    UI_TEXT_DIM,
)
from engine.renderer import Renderer
from ui.styles import UIStyles


class MenuUI:
    LOGO_TOP = 22

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self.selected = 0
        self.difficulty = Difficulty.NORMAL
        self._item_rects: list[tuple[pygame.Rect, str]] = []
        self._diff_left = pygame.Rect(0, 0, 0, 0)
        self._diff_right = pygame.Rect(0, 0, 0, 0)
        self._anim = 0.0
        self._logo: pygame.Surface | None = None

    def set_logo(self, logo: pygame.Surface | None) -> None:
        self._logo = logo

    def _visible_items(self, has_save: bool) -> list[tuple[str, str]]:
        out = [
            (GAME_MODE_LABELS[GameMode.CLASSIC], "mode_classic"),
            (GAME_MODE_LABELS[GameMode.ARENA], "mode_arena"),
            (GAME_MODE_LABELS[GameMode.ARENA_BOSSES], "mode_arena_bosses"),
            (GAME_MODE_LABELS[GameMode.SPEED], "mode_speed"),
        ]
        if has_save:
            out.append(("Продолжить", "continue"))
        out.append(("Выход", "quit"))
        return out

    def _mode_for_action(self, action: str) -> GameMode | None:
        mapping = {
            "mode_classic": GameMode.CLASSIC,
            "mode_arena": GameMode.ARENA,
            "mode_arena_bosses": GameMode.ARENA_BOSSES,
            "mode_speed": GameMode.SPEED,
        }
        return mapping.get(action)

    def cycle_difficulty(self, direction: int) -> None:
        order = [Difficulty.EASY, Difficulty.NORMAL, Difficulty.HARD]
        idx = order.index(self.difficulty)
        self.difficulty = order[(idx + direction) % len(order)]

    def handle_input(self, up: bool, down: bool, confirm: bool, has_save: bool, left: bool = False, right: bool = False) -> str | None:
        if left:
            self.cycle_difficulty(-1)
        if right:
            self.cycle_difficulty(1)
        visible = self._visible_items(has_save)
        if up:
            self.selected = max(0, self.selected - 1)
        if down:
            self.selected = min(len(visible) - 1, self.selected + 1)
        if confirm and visible:
            return visible[self.selected][1]
        return None

    def handle_difficulty_click(self, pos: tuple[int, int]) -> bool:
        mx, my = pos
        if self._diff_left.collidepoint(mx, my):
            self.cycle_difficulty(-1)
            return True
        if self._diff_right.collidepoint(mx, my):
            self.cycle_difficulty(1)
            return True
        return False

    def _content_top(self) -> int:
        if self._logo:
            return self.LOGO_TOP + self._logo.get_height() + 18
        return 168

    def _draw_background(self, r: Renderer) -> None:
        self._anim += 0.02
        bg = UIStyles.menu_background(self._anim)
        r.screen.blit(bg, (0, 0))
        r.draw_vignette(0.7)

    def draw(self, has_save: bool) -> None:
        r = self.renderer
        self._draw_background(r)

        content_top = self._content_top()
        if self._logo:
            lw, lh = self._logo.get_size()
            lx = SCREEN_WIDTH // 2 - lw // 2
            ly = self.LOGO_TOP
            pulse = 0.5 + 0.5 * math.sin(self._anim * 2.2)
            glow = pygame.Surface((lw + 32, lh + 32), pygame.SRCALPHA)
            pygame.draw.ellipse(glow, (255, 180, 80, int(18 + pulse * 22)), (0, 0, lw + 32, lh + 32))
            r.screen.blit(glow, glow.get_rect(center=(SCREEN_WIDTH // 2, ly + lh // 2)))
            r.screen.blit(self._logo, (lx, ly))
        else:
            r.blit_text_outlined(r.font_huge, "PYTHONABLO", UI_TEXT, (SCREEN_WIDTH // 2 - 200, 52), outline=(30, 20, 10), outline_width=3)
            sub = r.font_title.render("DIABLOID ARPG", True, UI_ACCENT)
            r.screen.blit(sub, sub.get_rect(midtop=(SCREEN_WIDTH // 2, 128)))

        diff_y = content_top
        r.blit_centered(r.font_small, "Сложность", UI_TEXT_DIM, SCREEN_WIDTH // 2, diff_y)
        arrow_w, arrow_h = 40, 40
        cx = SCREEN_WIDTH // 2
        self._diff_left = pygame.Rect(cx - 190, diff_y + 14, arrow_w, arrow_h)
        self._diff_right = pygame.Rect(cx + 150, diff_y + 14, arrow_w, arrow_h)
        for rect, label in ((self._diff_left, "◀"), (self._diff_right, "▶")):
            hovered = rect.collidepoint(pygame.mouse.get_pos())
            fill = UI_CARD_HOVER if hovered else UI_CARD
            surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*fill, 240), (0, 0, rect.w, rect.h), border_radius=10)
            pygame.draw.rect(surf, (*UI_ACCENT, 255), (0, 0, rect.w, rect.h), width=2, border_radius=10)
            r.screen.blit(surf, rect.topleft)
            t = r.font_menu.render(label, True, UI_ACCENT)
            r.screen.blit(t, t.get_rect(center=rect.center))

        diff_color = UI_HP_FILL if self.difficulty == Difficulty.EASY else UI_ACCENT if self.difficulty == Difficulty.NORMAL else (255, 100, 100)
        r.blit_centered(r.font_menu, DIFFICULTY_LABELS[self.difficulty], diff_color, cx, diff_y + 36)

        visible = self._visible_items(has_save)
        menu_w, item_h, gap = 520, 46, 8
        start_y = diff_y + 70
        self._item_rects = []
        mx, my = pygame.mouse.get_pos()
        for i, (label, action) in enumerate(visible):
            rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_w // 2, start_y + i * (item_h + gap), menu_w, item_h)
            self._item_rects.append((rect, action))
            selected = i == self.selected
            hovered = rect.collidepoint(mx, my)
            fill = UI_CARD_HOVER if selected or hovered else UI_CARD
            surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*fill, 245), (0, 0, rect.w, rect.h), border_radius=12)
            border_c = UI_ACCENT if selected else UI_PANEL_BORDER
            pygame.draw.rect(surf, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=12)
            if selected:
                pygame.draw.line(surf, (*UI_ACCENT, 180), (14, 4), (rect.w - 14, 4), 2)
            r.screen.blit(surf, rect.topleft)
            color = UI_ACCENT if selected else UI_TEXT
            text = r.font_menu.render(label, True, color)
            r.screen.blit(text, text.get_rect(midleft=(rect.x + 18, rect.centery)))

            mode = self._mode_for_action(action)
            if mode:
                desc = GAME_MODE_DESCRIPTIONS[mode]
                desc_surf = r.font_small.render(desc, True, UI_TEXT_DIM)
                r.screen.blit(desc_surf, desc_surf.get_rect(midright=(rect.right - 14, rect.centery)))

        r.blit_centered(r.font_small, "←/→ — сложность  ·  ↑/↓ — выбор  ·  ENTER — начать", UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 52)
        r.blit_centered(r.font_small, "WASD — движение  ·  ЛКМ — атака  ·  E — переход  ·  I — инвентарь", UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 28)

    def handle_click(self, pos: tuple[int, int], has_save: bool) -> str | None:
        if self.handle_difficulty_click(pos):
            return None
        visible = self._visible_items(has_save)
        if not self._item_rects:
            menu_w, item_h, gap = 520, 46, 8
            start_y = self._content_top() + 70
            self._item_rects = []
            for i, (_, action) in enumerate(visible):
                rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_w // 2, start_y + i * (item_h + gap), menu_w, item_h)
                self._item_rects.append((rect, action))
        for idx, (rect, action) in enumerate(self._item_rects):
            if rect.collidepoint(pos):
                self.selected = idx
                return action
        return None


class GameOverUI:
    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer

    def draw(self, floor: int, level: int, kills: int, killer: str | None = None) -> None:
        r = self.renderer
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 215))
        r.screen.blit(overlay, (0, 0))
        r.blit_text_outlined(r.font_huge, "ВЫ ПОГИБЛИ", (255, 90, 90), (SCREEN_WIDTH // 2 - 175, 148), outline=(60, 10, 10), outline_width=3)
        if killer:
            r.blit_centered(r.font_mid, f"Убийца: {killer}", (255, 160, 120), SCREEN_WIDTH // 2, 230)
        r.blit_centered(r.font_mid, f"Этаж {floor}  ·  Уровень {level}  ·  Убийств: {kills}", UI_TEXT, SCREEN_WIDTH // 2, 280 if killer else 250)
        r.blit_centered(r.font_menu, "ENTER — в меню", UI_ACCENT, SCREEN_WIDTH // 2, 380)
