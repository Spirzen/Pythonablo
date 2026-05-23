"""Main menu and game over screens."""

from __future__ import annotations

import math

import pygame

from core.config import DIFFICULTY_LABELS, Difficulty, SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_CARD_HOVER, UI_HP_FILL, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer


class MenuUI:
    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self.selected = 0
        self.difficulty = Difficulty.NORMAL
        self._item_rects: list[tuple[pygame.Rect, str]] = []
        self._diff_left = pygame.Rect(0, 0, 0, 0)
        self._diff_right = pygame.Rect(0, 0, 0, 0)
        self._anim = 0.0

    def _visible_items(self, has_save: bool) -> list[tuple[str, str]]:
        out = [("Новая игра", "new")]
        if has_save:
            out.append(("Продолжить", "continue"))
        out.append(("Выход", "quit"))
        return out

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

    def _draw_background(self, r: Renderer) -> None:
        self._anim += 0.02
        # Gradient backdrop
        for y in range(0, SCREEN_HEIGHT, 3):
            t = y / SCREEN_HEIGHT
            col = (int(8 + 14 * t), int(10 + 12 * t), int(20 + 22 * t))
            pygame.draw.rect(r.screen, col, (0, y, SCREEN_WIDTH, 3))
        # Ambient orbs
        for i in range(8):
            ox = SCREEN_WIDTH * (0.12 + 0.11 * i) + math.sin(self._anim + i) * 30
            oy = SCREEN_HEIGHT * (0.25 + 0.08 * (i % 3)) + math.cos(self._anim * 0.7 + i) * 20
            rad = int(40 + 20 * math.sin(self._anim * 0.5 + i))
            surf = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            color = (255, 180, 80, 12) if i % 2 == 0 else (100, 140, 255, 10)
            pygame.draw.circle(surf, color, (rad, rad), rad)
            r.screen.blit(surf, surf.get_rect(center=(int(ox), int(oy))))
        r.draw_vignette(0.7)

    def draw(self, has_save: bool) -> None:
        r = self.renderer
        self._draw_background(r)

        r.blit_text_outlined(r.font_huge, "PYTHONABLO", UI_TEXT, (SCREEN_WIDTH // 2 - 200, 72), outline=(30, 20, 10), outline_width=3)
        sub = r.font_title.render("DIABLOID ARPG", True, UI_ACCENT)
        r.screen.blit(sub, sub.get_rect(midtop=(SCREEN_WIDTH // 2, 148)))

        diff_y = 200
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
        menu_w, item_h, gap = 480, 56, 14
        start_y = 280
        self._item_rects = []
        mx, my = pygame.mouse.get_pos()
        for i, (label, _) in enumerate(visible):
            rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_w // 2, start_y + i * (item_h + gap), menu_w, item_h)
            action = visible[i][1]
            self._item_rects.append((rect, action))
            selected = i == self.selected
            hovered = rect.collidepoint(mx, my)
            fill = UI_CARD_HOVER if selected or hovered else UI_CARD
            surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            pygame.draw.rect(surf, (*fill, 245), (0, 0, rect.w, rect.h), border_radius=14)
            border_c = UI_ACCENT if selected else UI_PANEL_BORDER
            pygame.draw.rect(surf, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=14)
            if selected:
                pygame.draw.line(surf, (*UI_ACCENT, 180), (14, 4), (rect.w - 14, 4), 2)
            r.screen.blit(surf, rect.topleft)
            color = UI_ACCENT if selected else UI_TEXT
            text = r.font_menu.render(label, True, color)
            r.screen.blit(text, text.get_rect(center=rect.center))

        r.blit_centered(r.font_small, "←/→ — сложность  ·  ↑/↓ — выбор  ·  ENTER — начать", UI_TEXT_DIM, SCREEN_WIDTH // 2, 530)
        r.blit_centered(r.font_small, "WASD — движение  ·  ЛКМ — атака  ·  E — переход  ·  I — инвентарь", UI_TEXT_DIM, SCREEN_WIDTH // 2, 558)

    def handle_click(self, pos: tuple[int, int], has_save: bool) -> str | None:
        if self.handle_difficulty_click(pos):
            return None
        visible = self._visible_items(has_save)
        if not self._item_rects:
            menu_w, item_h, gap = 480, 56, 14
            start_y = 280
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

    def draw(self, floor: int, level: int, kills: int) -> None:
        r = self.renderer
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((6, 8, 18, 215))
        r.screen.blit(overlay, (0, 0))
        r.blit_text_outlined(r.font_huge, "ВЫ ПОГИБЛИ", (255, 90, 90), (SCREEN_WIDTH // 2 - 175, 168), outline=(60, 10, 10), outline_width=3)
        r.blit_centered(r.font_mid, f"Этаж {floor}  ·  Уровень {level}  ·  Убийств: {kills}", UI_TEXT, SCREEN_WIDTH // 2, 280)
        r.blit_centered(r.font_menu, "ENTER — в меню", UI_ACCENT, SCREEN_WIDTH // 2, 380)
