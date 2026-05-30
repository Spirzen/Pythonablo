"""Shared UI styling, cached surfaces, and reusable widgets."""

from __future__ import annotations

import math

import pygame

from core.config import (
    RARITY_COLORS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    UI_ACCENT,
    UI_CARD,
    UI_CARD_HOVER,
    UI_PANEL,
    UI_PANEL_BORDER,
    UI_TEXT,
    UI_TEXT_DIM,
)
from engine.renderer import Renderer


class UIStyles:
    """Cached UI resources and draw helpers."""

    _dim_overlays: dict[int, pygame.Surface] = {}
    _menu_bg: pygame.Surface | None = None
    _slot_cache: dict[tuple, pygame.Surface] = {}

    @classmethod
    def dim_overlay(cls, alpha: int = 215) -> pygame.Surface:
        cached = cls._dim_overlays.get(alpha)
        if cached is not None:
            return cached
        surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        surf.fill((12, 10, 8, alpha))
        cls._dim_overlays[alpha] = surf
        return surf

    @classmethod
    def blit_dim(cls, screen: pygame.Surface, alpha: int = 215) -> None:
        screen.blit(cls.dim_overlay(alpha), (0, 0))

    @classmethod
    def menu_background(cls, anim: float) -> pygame.Surface:
        if cls._menu_bg is None:
            base = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            for y in range(0, SCREEN_HEIGHT, 2):
                t = y / SCREEN_HEIGHT
                r = int(12 + 80 * t + 40 * t * t)
                g = int(18 + 50 * t + 30 * t * t)
                b = int(38 - 18 * t)
                pygame.draw.rect(base, (r, g, b), (0, y, SCREEN_WIDTH, 2))
            cls._menu_bg = base.convert()
        out = cls._menu_bg.copy()
        sun_x = SCREEN_WIDTH // 2 + int(math.sin(anim * 0.15) * 40)
        sun_y = int(SCREEN_HEIGHT * 0.38)
        sun = pygame.Surface((220, 220), pygame.SRCALPHA)
        for ring in range(8, 0, -1):
            alpha = int(18 + 12 * (1 - ring / 8))
            rad = ring * 14
            pygame.draw.circle(sun, (255, 190, 80, alpha), (110, 110), rad)
        pygame.draw.circle(sun, (255, 210, 100, 90), (110, 110), 28)
        out.blit(sun, sun.get_rect(center=(sun_x, sun_y)))
        for i in range(10):
            ox = SCREEN_WIDTH * (0.08 + 0.09 * i) + math.sin(anim * 0.6 + i * 1.3) * 35
            oy = SCREEN_HEIGHT * (0.55 + 0.06 * (i % 4)) + math.cos(anim * 0.45 + i) * 25
            rad = int(28 + 14 * math.sin(anim * 0.5 + i))
            surf = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            if i % 3 == 0:
                color = (218, 175, 55, 14)
            elif i % 3 == 1:
                color = (120, 160, 90, 12)
            else:
                color = (180, 100, 60, 10)
            pygame.draw.circle(surf, color, (rad, rad), rad)
            out.blit(surf, surf.get_rect(center=(int(ox), int(oy))))
        return out

    @classmethod
    def draw_button(
        cls,
        screen: pygame.Surface,
        rect: pygame.Rect,
        label: str,
        font: pygame.font.Font,
        *,
        hovered: bool = False,
        accent: tuple[int, int, int] = UI_ACCENT,
        danger: bool = False,
    ) -> None:
        key = (rect.w, rect.h, hovered, danger)
        frame = cls._slot_cache.get(key)
        if frame is None:
            frame = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            fill = UI_CARD_HOVER if hovered else UI_CARD
            if danger and hovered:
                fill = (72, 36, 36)
            pygame.draw.rect(frame, (*fill, 245), (0, 0, rect.w, rect.h), border_radius=12)
            border_c = accent if hovered else UI_PANEL_BORDER
            if danger:
                border_c = (255, 120, 80) if hovered else (140, 70, 60)
            pygame.draw.rect(frame, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=12)
            if hovered:
                pygame.draw.line(frame, (*accent, 180), (14, 4), (rect.w - 14, 4), 2)
            cls._slot_cache[key] = frame
        screen.blit(frame, rect.topleft)
        color = accent if hovered else UI_TEXT
        if danger:
            color = (255, 160, 120) if hovered else UI_TEXT
        text = font.render(label, True, color)
        screen.blit(text, text.get_rect(center=rect.center))

    @classmethod
    def draw_item_cell(
        cls,
        screen: pygame.Surface,
        rect: pygame.Rect,
        item,
        *,
        hovered: bool = False,
        font: pygame.font.Font | None = None,
    ) -> None:
        bg = (38, 34, 26) if hovered else (28, 24, 18)
        pygame.draw.rect(screen, bg, rect, border_radius=6)
        border = UI_ACCENT if hovered else UI_PANEL_BORDER
        pygame.draw.rect(screen, border, rect, width=2 if hovered else 1, border_radius=6)
        if not item:
            return
        inner = rect.inflate(-4, -4)
        rarity = RARITY_COLORS.get(item.quality.value, item.color)
        pygame.draw.rect(screen, item.color, inner, border_radius=4)
        if item.quality.value != "normal":
            glow = pygame.Surface((inner.w + 6, inner.h + 6), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*rarity, 55), (0, 0, inner.w + 6, inner.h + 6), border_radius=6)
            screen.blit(glow, glow.get_rect(center=inner.center))
            pygame.draw.rect(screen, rarity, inner, width=2, border_radius=4)
        if font:
            short = item.name[:3].upper()
            t = font.render(short, True, (20, 22, 30))
            screen.blit(t, t.get_rect(center=inner.center))

    @classmethod
    def draw_radial_cooldown(
        cls,
        screen: pygame.Surface,
        rect: pygame.Rect,
        ratio: float,
        *,
        color: tuple[int, int, int] = (6, 8, 18),
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        if ratio <= 0.01:
            return
        cx, cy = rect.center
        radius = min(rect.w, rect.h) // 2 - 2
        start = -math.pi / 2
        end = start + math.tau * ratio
        points = [(cx, cy)]
        steps = max(8, int(24 * ratio))
        for i in range(steps + 1):
            a = start + (end - start) * i / steps
            points.append((cx + math.cos(a) * radius, cy + math.sin(a) * radius))
        if len(points) > 2:
            veil = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            local = [(p[0] - rect.left, p[1] - rect.top) for p in points]
            pygame.draw.polygon(veil, (*color, 200), local)
            screen.blit(veil, rect.topleft)

    @classmethod
    def draw_section_title(cls, r: Renderer, text: str, x: int, y: int, *, centered: bool = False) -> None:
        if centered:
            r.blit_centered(r.font_menu, text, UI_ACCENT, x, y)
        else:
            title = r.font_menu.render(text, True, UI_ACCENT)
            r.screen.blit(title, (x, y))
            underline = pygame.Surface((title.get_width(), 2), pygame.SRCALPHA)
            underline.fill((*UI_ACCENT, 90))
            r.screen.blit(underline, (x, y + title.get_height() + 2))
