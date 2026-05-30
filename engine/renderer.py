"""Isometric coordinate helpers and rendering."""

from __future__ import annotations

import math
from typing import Optional

import pygame

from core.config import ISO_TILE_H, ISO_TILE_W, SCREEN_HEIGHT, SCREEN_WIDTH, UI_PANEL, UI_PANEL_BORDER


def world_to_screen(wx: float, wy: float, cam_x: float, cam_y: float) -> tuple[float, float]:
    sx = (wx - wy) * (ISO_TILE_W / 2) - cam_x + SCREEN_WIDTH / 2
    sy = (wx + wy) * (ISO_TILE_H / 2) - cam_y + SCREEN_HEIGHT / 2 - 80
    return sx, sy


def screen_to_world(sx: float, sy: float, cam_x: float, cam_y: float) -> tuple[float, float]:
    x = sx - SCREEN_WIDTH / 2 + cam_x
    y = sy - SCREEN_HEIGHT / 2 + 80 + cam_y
    wx = (x / (ISO_TILE_W / 2) + y / (ISO_TILE_H / 2)) / 2
    wy = (y / (ISO_TILE_H / 2) - x / (ISO_TILE_W / 2)) / 2
    return wx, wy


def _clamp_color(r: int, g: int, b: int) -> tuple[int, int, int]:
    return max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))


def _shade(color: tuple[int, int, int], delta: int) -> tuple[int, int, int]:
    return _clamp_color(color[0] + delta, color[1] + delta, color[2] + delta)


class Renderer:
    _MAX_TEXT_CACHE = 512
    _MAX_SCALE_CACHE = 256
    _MAX_TILE_CACHE = 64
    _MAX_SHADOW_CACHE = 32

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.font = pygame.font.SysFont("Segoe UI", 17, bold=True)
        self.font_small = pygame.font.SysFont("Segoe UI", 14)
        self.font_label = pygame.font.SysFont("Segoe UI", 13, bold=True)
        self.font_big = pygame.font.SysFont("Segoe UI", 40, bold=True)
        self.font_huge = pygame.font.SysFont("Segoe UI", 56, bold=True)
        self.font_mid = pygame.font.SysFont("Segoe UI", 26)
        self.font_menu = pygame.font.SysFont("Segoe UI", 22)
        self.font_title = pygame.font.SysFont("Segoe UI", 18, bold=True)
        self.font_damage = pygame.font.SysFont("Segoe UI", 20, bold=True)
        self._vignette: pygame.Surface | None = None
        self._text_cache: dict[tuple, pygame.Surface] = {}
        self._scale_cache: dict[tuple, pygame.Surface] = {}
        self._iso_tile_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._shadow_cache: dict[tuple[int, int, int], pygame.Surface] = {}
        self._effect_scratch: pygame.Surface | None = None

    def _ensure_vignette(self) -> pygame.Surface:
        if self._vignette is None:
            w, h = SCREEN_WIDTH, SCREEN_HEIGHT
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            cx, cy = w // 2, h // 2
            max_dist = math.hypot(cx, cy)
            for y in range(0, h, 2):
                for x in range(0, w, 2):
                    d = math.hypot(x - cx, y - cy) / max_dist
                    alpha = int(165 * max(0.0, max(0.0, d - 0.32) ** 1.6))
                    if alpha > 0:
                        surf.fill((18, 12, 8, alpha), (x, y, 2, 2))
            self._vignette = surf
        return self._vignette

    def draw_vignette(self, strength: float = 1.0, *, tint: tuple[int, int, int] | None = None) -> None:
        vig = self._ensure_vignette()
        if tint and strength > 0.05:
            tinted = vig.copy()
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            tr, tg, tb = tint
            overlay.fill((tr, tg, tb, int(80 * strength)))
            tinted.blit(overlay, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            vig = tinted
        if strength >= 0.99:
            self.screen.blit(vig, (0, 0))
        else:
            temp = vig.copy()
            temp.set_alpha(int(255 * strength))
            self.screen.blit(temp, (0, 0))

    def draw_panel(
        self,
        rect: pygame.Rect,
        *,
        fill: tuple = UI_PANEL,
        alpha: int = 210,
        border: tuple = UI_PANEL_BORDER,
        radius: int = 12,
        accent_top: bool = True,
        shadow: bool = True,
    ) -> None:
        if shadow:
            sh = pygame.Surface((rect.w + 6, rect.h + 6), pygame.SRCALPHA)
            pygame.draw.rect(sh, (0, 0, 0, 55), (4, 4, rect.w, rect.h), border_radius=radius)
            self.screen.blit(sh, (rect.x - 2, rect.y - 1))
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*fill, alpha), (0, 0, rect.w, rect.h), border_radius=radius)
        highlight = pygame.Surface((rect.w - 4, max(8, rect.h // 5)), pygame.SRCALPHA)
        highlight.fill((255, 255, 255, 18))
        surf.blit(highlight, (2, 2))
        if accent_top:
            pygame.draw.line(surf, (218, 175, 55, 140), (radius, 2), (rect.w - radius, 2), 2)
        pygame.draw.rect(surf, (*border, 220), (0, 0, rect.w, rect.h), width=2, border_radius=radius)
        self.screen.blit(surf, rect.topleft)

    def draw_bar(
        self,
        x: int,
        y: int,
        w: int,
        h: int,
        ratio: float,
        fill: tuple,
        bg: tuple,
        *,
        radius: int = 6,
        glossy: bool = True,
    ) -> None:
        ratio = max(0.0, min(1.0, ratio))
        pygame.draw.rect(self.screen, bg, (x, y, w, h), border_radius=radius)
        fill_w = max(0, int(w * ratio))
        if fill_w > 0:
            if glossy and fill_w >= 4:
                bar_surf = pygame.Surface((fill_w, h), pygame.SRCALPHA)
                pygame.draw.rect(bar_surf, fill, (0, 0, fill_w, h), border_radius=radius)
                shine_h = max(2, h // 3)
                shine = pygame.Surface((fill_w, shine_h), pygame.SRCALPHA)
                shine.fill((255, 255, 255, 55))
                bar_surf.blit(shine, (0, 1))
                self.screen.blit(bar_surf, (x, y))
            else:
                pygame.draw.rect(self.screen, fill, (x, y, fill_w, h), border_radius=radius)
        pygame.draw.rect(self.screen, _shade(UI_PANEL_BORDER, 20), (x, y, w, h), width=1, border_radius=radius)

    def render_text(self, font: pygame.font.Font, text: str, color: tuple) -> pygame.Surface:
        key = (id(font), text, color)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        surf = font.render(text, True, color)
        if len(self._text_cache) >= self._MAX_TEXT_CACHE:
            self._text_cache.clear()
        self._text_cache[key] = surf
        return surf

    def blit_centered(self, font: pygame.font.Font, text: str, color: tuple, cx: int, y: int) -> pygame.Rect:
        surf = self.render_text(font, text, color)
        rect = surf.get_rect(midtop=(cx, y))
        self.screen.blit(surf, rect)
        return rect

    def blit_text_outlined(
        self,
        font: pygame.font.Font,
        text: str,
        color: tuple,
        pos: tuple[int, int],
        *,
        outline: tuple = (20, 12, 8),
        outline_width: int = 2,
        alpha: int = 255,
    ) -> None:
        cached = self._outlined_surface(font, text, color, outline=outline, outline_width=outline_width, alpha=alpha)
        self.screen.blit(cached, (pos[0] - outline_width - 1, pos[1] - outline_width - 1))

    def _outlined_surface(
        self,
        font: pygame.font.Font,
        text: str,
        color: tuple,
        *,
        outline: tuple = (20, 12, 8),
        outline_width: int = 2,
        alpha: int = 255,
    ) -> pygame.Surface:
        key = (id(font), text, color, outline, outline_width, alpha)
        cached = self._text_cache.get(key)
        if cached is not None:
            return cached
        base = font.render(text, True, color)
        w, h = base.get_size()
        pad = outline_width + 1
        surf = pygame.Surface((w + pad * 2, h + pad * 2), pygame.SRCALPHA)
        ox, oy = pad, pad
        for dx in range(-outline_width, outline_width + 1):
            for dy in range(-outline_width, outline_width + 1):
                if dx * dx + dy * dy <= outline_width * outline_width + 1:
                    shadow = font.render(text, True, outline)
                    surf.blit(shadow, (ox + dx, oy + dy))
        surf.blit(base, (ox, oy))
        if alpha < 255:
            surf.set_alpha(alpha)
        if len(self._text_cache) >= self._MAX_TEXT_CACHE:
            self._text_cache.clear()
        self._text_cache[key] = surf
        return surf

    def blit_text_outlined_centered(
        self,
        font: pygame.font.Font,
        text: str,
        color: tuple,
        cx: float,
        y: float,
        *,
        anchor: str = "midbottom",
        outline: tuple = (20, 12, 8),
        outline_width: int = 2,
        alpha: int = 255,
    ) -> None:
        surf = self._outlined_surface(
            font, text, color, outline=outline, outline_width=outline_width, alpha=alpha,
        )
        if anchor == "midtop":
            rect = surf.get_rect(midtop=(int(cx), int(y)))
        elif anchor == "center":
            rect = surf.get_rect(center=(int(cx), int(y)))
        else:
            rect = surf.get_rect(midbottom=(int(cx), int(y)))
        self.screen.blit(surf, rect)

    # Screen-pixel offsets above entity center (multiply by scale for large enemies).
    OVERHEAD_HP = 38
    OVERHEAD_TAG = 54
    OVERHEAD_ABILITY = 70
    OVERHEAD_DAMAGE = 62
    OVERHEAD_FLOAT = 68

    @staticmethod
    def overhead_y(base_sy: float, layer: str, scale: float = 1.0) -> int:
        offsets = {
            "hp": Renderer.OVERHEAD_HP,
            "tag": Renderer.OVERHEAD_TAG,
            "ability": Renderer.OVERHEAD_ABILITY,
            "damage": Renderer.OVERHEAD_DAMAGE,
            "float": Renderer.OVERHEAD_FLOAT,
        }
        return int(base_sy - offsets.get(layer, 50) * scale)

    def _scaled_sprite(self, sprite: pygame.Surface, scale: float) -> pygame.Surface:
        if abs(scale - 1.0) < 0.02:
            return sprite
        qscale = round(scale * 20) / 20.0
        w, h = sprite.get_size()
        key = (id(sprite), qscale)
        cached = self._scale_cache.get(key)
        if cached is not None:
            return cached
        img = pygame.transform.smoothscale(sprite, (max(1, int(w * qscale)), max(1, int(h * qscale))))
        if len(self._scale_cache) >= self._MAX_SCALE_CACHE:
            self._scale_cache.clear()
        self._scale_cache[key] = img
        return img

    def blit_sprite(
        self,
        sprite: Optional[pygame.Surface],
        sx: float,
        sy: float,
        *,
        hit_flash: bool = False,
        scale: float = 1.0,
        glow_color: tuple[int, int, int] | None = None,
    ) -> bool:
        if sprite is None:
            return False
        img = self._scaled_sprite(sprite, scale) if scale != 1.0 else sprite
        rect = img.get_rect(center=(int(sx), int(sy)))
        if glow_color:
            glow = pygame.transform.scale(img, (int(rect.w * 1.15), int(rect.h * 1.15)))
            glow.set_alpha(45)
            glow_rect = glow.get_rect(center=rect.center)
            tint = pygame.Surface(glow.get_size(), pygame.SRCALPHA)
            tint.fill((*glow_color, 80))
            glow.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            self.screen.blit(glow, glow_rect)
        if hit_flash:
            temp = img.copy()
            white = pygame.Surface(temp.get_size(), pygame.SRCALPHA)
            white.fill((255, 255, 255, 140))
            temp.blit(white, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
            self.screen.blit(temp, rect)
        else:
            self.screen.blit(img, rect)
        return True

    def draw_entity_shadow(
        self,
        sx: float,
        sy: float,
        radius: float = 14.0,
        alpha: int = 70,
        *,
        width_scale: float = 1.0,
    ) -> None:
        w = int(radius * 2.2 * width_scale)
        h = max(6, int(radius * 0.55))
        key = (w, h, alpha)
        surf = self._shadow_cache.get(key)
        if surf is None:
            surf = pygame.Surface((w, h), pygame.SRCALPHA)
            pygame.draw.ellipse(surf, (0, 0, 0, alpha), (0, 0, w, h))
            if len(self._shadow_cache) >= self._MAX_SHADOW_CACHE:
                self._shadow_cache.clear()
            self._shadow_cache[key] = surf
        self.screen.blit(surf, surf.get_rect(center=(int(sx), int(sy + radius * 0.35))))

    def get_iso_tile_surface(
        self,
        color: tuple[int, int, int],
        *,
        is_wall: bool = False,
        seed: int = 0,
    ) -> pygame.Surface:
        cache_key = (*color, is_wall, seed % 7)
        cached = self._iso_tile_cache.get(cache_key)
        if cached is not None:
            return cached
        hw, hh = ISO_TILE_W // 2, ISO_TILE_H // 2
        w, h = ISO_TILE_W + 8, ISO_TILE_H + 16
        depth_h = 12 if is_wall else 7
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        cx, cy = w // 2, h // 2 - 4
        top = (cx, cy - 4)
        right = (cx + hw, cy + hh - 4)
        bottom = (cx, cy + ISO_TILE_H - 4)
        left = (cx - hw, cy + hh - 4)
        top_color = _shade(color, 28 if is_wall else 22)
        left_color = _shade(color, -22 if is_wall else -18)
        right_color = _shade(color, -10 if is_wall else -8)
        pygame.draw.polygon(surf, top_color, [top, right, bottom, left])
        pygame.draw.polygon(
            surf,
            left_color,
            [left, bottom, (left[0], left[1] + depth_h), (bottom[0] - hw, bottom[1] + depth_h // 2)],
        )
        if is_wall:
            pygame.draw.polygon(
                surf,
                _shade(color, 12),
                [right, bottom, (right[0], right[1] + depth_h // 2), (bottom[0] + hw // 2, bottom[1] + depth_h)],
            )
        pygame.draw.line(surf, right_color, top, right, 1)
        pygame.draw.line(surf, right_color, right, bottom, 1)
        mid_l = ((top[0] + left[0]) // 2, (top[1] + left[1]) // 2)
        mid_r = ((top[0] + right[0]) // 2, (top[1] + right[1]) // 2)
        pygame.draw.line(surf, _shade(color, 42), mid_l, top, 2)
        pygame.draw.line(surf, _shade(color, 42), top, mid_r, 2)
        pygame.draw.polygon(surf, _shade(color, -35), [top, right, bottom, left], 1)
        if not is_wall and seed % 3 == 0:
            for i in range(3):
                ox = ((seed + i * 5) % 9) - 4
                oy = ((seed + i * 7) % 7) - 3
                speck = _shade(color, -12 + (i * 4))
                pygame.draw.circle(surf, speck, (cx + ox, cy + oy), 1)
        if len(self._iso_tile_cache) >= self._MAX_TILE_CACHE:
            self._iso_tile_cache.clear()
        self._iso_tile_cache[cache_key] = surf
        return surf

    def draw_iso_tile(
        self,
        wx: float,
        wy: float,
        cam_x: float,
        cam_y: float,
        color: tuple,
        *,
        height: int = 0,
        pulse: float = 0.0,
        accent: tuple[int, int, int] | None = None,
    ) -> None:
        sx, sy = world_to_screen(wx, wy, cam_x, cam_y)
        hw, hh = ISO_TILE_W // 2, ISO_TILE_H // 2
        top = (int(sx), int(sy - height))
        right = (int(sx + hw), int(sy + hh - height))
        bottom = (int(sx), int(sy + ISO_TILE_H - height))
        left = (int(sx - hw), int(sy + hh - height))

        if pulse > 0 and accent:
            glow_r = int(ISO_TILE_W * (0.55 + pulse * 0.15))
            glow_s = pygame.Surface((glow_r * 2, glow_r), pygame.SRCALPHA)
            pygame.draw.ellipse(glow_s, (*accent, int(35 + pulse * 45)), (0, 0, glow_r * 2, glow_r))
            self.screen.blit(glow_s, glow_s.get_rect(center=(int(sx), int(sy + hh - height + 4))))

        top_color = _shade(color, 22)
        left_color = _shade(color, -18)
        right_color = _shade(color, -8)
        pygame.draw.polygon(self.screen, top_color, [top, right, bottom, left])
        # Left face depth
        depth_h = 7
        pygame.draw.polygon(
            self.screen,
            left_color,
            [left, bottom, (left[0], left[1] + depth_h), (bottom[0] - hw, bottom[1] + depth_h // 2)],
        )
        # Right edge accent
        pygame.draw.line(self.screen, right_color, top, right, 1)
        pygame.draw.line(self.screen, right_color, right, bottom, 1)
        # Top highlight
        mid_l = ((top[0] + left[0]) // 2, (top[1] + left[1]) // 2)
        mid_r = ((top[0] + right[0]) // 2, (top[1] + right[1]) // 2)
        pygame.draw.line(self.screen, _shade(color, 38), mid_l, top, 2)
        pygame.draw.line(self.screen, _shade(color, 38), top, mid_r, 2)
        # Subtle outline
        outline = _shade(color, -35)
        pygame.draw.polygon(self.screen, outline, [top, right, bottom, left], 1)

        if accent and pulse > 0:
            inner = [
                (top[0], top[1] + 2),
                (right[0] - 4, right[1] - 2),
                (bottom[0], bottom[1] - 2),
                (left[0] + 4, left[1] - 2),
            ]
            pulse_a = int(50 + pulse * 70)
            overlay = pygame.Surface((ISO_TILE_W + 4, ISO_TILE_H + 12), pygame.SRCALPHA)
            cx, cy = (ISO_TILE_W + 4) // 2, (ISO_TILE_H + 12) // 2
            pts = [
                (top[0] - sx + cx, top[1] - sy + cy),
                (right[0] - sx + cx, right[1] - sy + cy),
                (bottom[0] - sx + cx, bottom[1] - sy + cy),
                (left[0] - sx + cx, left[1] - sy + cy),
            ]
            if len(pts) >= 3:
                pygame.draw.polygon(overlay, (*accent, pulse_a), pts)
                self.screen.blit(overlay, (int(sx) - cx, int(sy) - cy))

    def draw_character_orb(
        self,
        sx: float,
        sy: float,
        radius: float,
        body: tuple[int, int, int],
        *,
        accent: tuple[int, int, int] | None = None,
        hit_flash: bool = False,
        shape: str = "default",
        status_tint: tuple[int, int, int] | None = None,
    ) -> None:
        if hit_flash:
            body = (255, 255, 255)
        elif status_tint:
            body = (
                int(body[0] * 0.65 + status_tint[0] * 0.35),
                int(body[1] * 0.65 + status_tint[1] * 0.35),
                int(body[2] * 0.65 + status_tint[2] * 0.35),
            )
        r = int(radius)
        width_scale = 1.0
        height_scale = 1.0
        if shape == "hero":
            height_scale = 1.12
            width_scale = 0.92
        elif shape == "brute":
            width_scale = 1.28
            height_scale = 1.08
        elif shape == "runner":
            width_scale = 0.82
            height_scale = 0.92
        elif shape == "caster":
            height_scale = 1.05
        elif shape == "boss":
            width_scale = 1.35
            height_scale = 1.2
        self.draw_entity_shadow(sx, sy, radius, width_scale=width_scale * 1.05)
        if accent:
            glow = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
            glow_alpha = 45 if shape != "boss" else 55
            glow_r = r + (10 if shape == "boss" else 6)
            pygame.draw.ellipse(glow, (*accent, glow_alpha), (r * 2 - int(glow_r * width_scale), r * 2 - glow_r, int(glow_r * 2 * width_scale), glow_r * 2))
            self.screen.blit(glow, glow.get_rect(center=(int(sx), int(sy))))
        body_s = pygame.Surface((int(r * 2 * width_scale) + 8, int(r * 2 * height_scale) + 8), pygame.SRCALPHA)
        cx, cy = body_s.get_width() // 2, body_s.get_height() // 2
        rx, ry = int(r * width_scale), int(r * height_scale)
        pygame.draw.ellipse(body_s, body, (cx - rx, cy - ry, rx * 2, ry * 2))
        pygame.draw.ellipse(body_s, _shade(body, 40), (cx - rx // 2, cy - ry, max(2, rx), max(2, ry // 2)))
        pygame.draw.ellipse(body_s, _shade(body, -35), (cx - rx, cy - ry // 3, rx * 2, ry * 2), 2)
        if shape == "hero":
            pygame.draw.arc(body_s, accent or (218, 175, 55), (cx - rx, cy - ry, rx * 2, ry * 2), math.pi * 0.15, math.pi * 0.85, 2)
        elif shape == "caster":
            ring_col = accent if accent else (180, 120, 255)
            pygame.draw.ellipse(body_s, (*ring_col, 80), (cx - rx - 4, cy - ry - 6, (rx + 4) * 2, (ry + 4) * 2), 2)
        self.screen.blit(body_s, body_s.get_rect(center=(int(sx), int(sy))))

    def draw_loot_orb(self, sx: float, sy: float, color: tuple, anim: float) -> None:
        bob = math.sin(anim * 4.0) * 4.0
        cy = sy - 10 + bob
        pulse = 0.5 + 0.5 * math.sin(anim * 5.0)
        r = int(7 + pulse * 2)
        # Beam
        beam_h = int(28 + pulse * 10)
        beam = pygame.Surface((16, beam_h), pygame.SRCALPHA)
        for i in range(beam_h):
            a = int(30 * (1.0 - i / beam_h) * (0.6 + pulse * 0.4))
            pygame.draw.line(beam, (*color, a), (8, beam_h - i), (8, beam_h - i), 2)
        self.screen.blit(beam, beam.get_rect(midbottom=(int(sx), int(cy) + r)))
        # Glow
        glow = pygame.Surface((r * 6, r * 6), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, int(40 + pulse * 30)), (r * 3, r * 3), r + 8)
        self.screen.blit(glow, glow.get_rect(center=(int(sx), int(cy))))
        pygame.draw.circle(self.screen, color, (int(sx), int(cy)), r)
        pygame.draw.circle(self.screen, _shade(color, 60), (int(sx - 2), int(cy - 2)), max(2, r // 2))
        pygame.draw.circle(self.screen, _shade(color, -30), (int(sx), int(cy)), r, 2)

    def draw_portal_marker(
        self,
        sx: float,
        sy: float,
        label: str,
        color: tuple,
        anim: float,
        *,
        direction: str = "down",
    ) -> None:
        pulse = 0.5 + 0.5 * math.sin(anim * 3.0)
        r = int(18 + pulse * 6)
        glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*color, int(25 + pulse * 35)), (r * 2, r * 2), r + 10)
        self.screen.blit(glow, glow.get_rect(center=(int(sx), int(sy))))
        ring_s = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
        pygame.draw.circle(ring_s, (*color, int(100 + pulse * 80)), (r + 4, r + 4), r, 3)
        self.screen.blit(ring_s, ring_s.get_rect(center=(int(sx), int(sy))))
        # Rotating runes
        for i in range(4):
            a = anim * 2.0 + i * math.pi / 2
            ox = sx + math.cos(a) * (r + 4)
            oy = sy + math.sin(a) * (r * 0.45)
            pygame.draw.circle(self.screen, _shade(color, 40), (int(ox), int(oy)), 3)
        arrow = "▼" if direction == "down" else "▲"
        self.blit_text_outlined(self.font_mid, arrow, color, (int(sx) - 10, int(sy) - r - 8), outline=(20, 10, 8))
        lbl = self.font_label.render(label, True, _shade(color, 30))
        shadow = self.font_label.render(label, True, (10, 8, 16))
        rect = lbl.get_rect(midbottom=(int(sx), int(sy) - r - 14))
        self.screen.blit(shadow, shadow.get_rect(midbottom=(rect.midbottom[0] + 1, rect.midbottom[1] + 1)))
        self.screen.blit(lbl, rect)

    def draw_hp_bar_world(self, sx: float, sy: float, ratio: float, width: int = 38, height: int = 6) -> None:
        ratio = max(0.0, min(1.0, ratio))
        bx = int(sx) - width // 2
        by = int(sy)
        pygame.draw.rect(self.screen, (15, 8, 10), (bx - 1, by - 1, width + 2, height + 2), border_radius=3)
        pygame.draw.rect(self.screen, (35, 18, 22), (bx, by, width, height), border_radius=3)
        fill_w = max(0, int(width * ratio))
        if fill_w > 0:
            col = (230, 55, 45) if ratio < 0.35 else (230, 100, 45) if ratio < 0.65 else (210, 70, 55)
            pygame.draw.rect(self.screen, col, (bx, by, fill_w, height), border_radius=3)
            shine = pygame.Surface((fill_w, max(2, height // 3)), pygame.SRCALPHA)
            shine.fill((255, 255, 255, 45))
            self.screen.blit(shine, (bx, by + 1))

    def draw_fireball(self, sx: float, sy: float, anim: float, sprite: Optional[pygame.Surface] = None, *, scale: float = 1.0) -> None:
        if sprite is not None:
            pulse = 0.85 + 0.15 * math.sin(anim * 12.0)
            w, h = sprite.get_size()
            size = max(16, int(max(w, h) * pulse * 0.55 * scale))
            img = pygame.transform.smoothscale(sprite, (size, size))
            glow = pygame.Surface((size + 12, size + 12), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 120, 40, 60), (size // 2 + 6, size // 2 + 6), size // 2 + 4)
            self.screen.blit(glow, glow.get_rect(center=(int(sx), int(sy - 6))))
            self.screen.blit(img, img.get_rect(center=(int(sx), int(sy - 6))))
            return
        pulse = 0.5 + 0.5 * math.sin(anim * 12.0)
        r = int((10 + pulse * 2) * scale)
        glow = pygame.Surface((r * 5, r * 5), pygame.SRCALPHA)
        pygame.draw.circle(glow, (255, 100, 30, 50), (r * 2 + 4, r * 2 + 4), r + 8)
        pygame.draw.circle(glow, (255, 180, 60, 80), (r * 2 + 4, r * 2 + 4), r + 3)
        self.screen.blit(glow, glow.get_rect(center=(int(sx), int(sy - 6))))
        pygame.draw.circle(self.screen, (255, 120, 40), (int(sx), int(sy - 6)), r)
        pygame.draw.circle(self.screen, (255, 230, 140), (int(sx - 2), int(sy - 8)), max(3, r // 2))

    def blit_icon(
        self,
        sprite: Optional[pygame.Surface],
        rect: pygame.Rect,
        *,
        alpha: int = 255,
        pad: int = 4,
    ) -> bool:
        if sprite is None:
            return False
        inner = rect.inflate(-pad * 2, -pad * 2)
        w, h = sprite.get_size()
        if w <= 0 or h <= 0:
            return False
        scale = min(inner.width / w, inner.height / h)
        nw, nh = max(1, int(w * scale)), max(1, int(h * scale))
        img = pygame.transform.smoothscale(sprite, (nw, nh))
        if alpha < 255:
            img = img.copy()
            img.set_alpha(alpha)
        self.screen.blit(img, img.get_rect(center=inner.center))
        return True

    def draw_hit_burst(
        self,
        sx: float,
        sy: float,
        sprite: Optional[pygame.Surface],
        progress: float,
        *,
        base_scale: float = 1.0,
    ) -> None:
        if sprite is None:
            return
        fade = max(0.0, 1.0 - progress)
        w, h = sprite.get_size()
        size = max(12, int(max(w, h) * base_scale * (0.7 + progress * 0.5)))
        img = pygame.transform.smoothscale(sprite, (size, size))
        img.set_alpha(int(220 * fade))
        self.screen.blit(img, img.get_rect(center=(int(sx), int(sy - 8))))

    def draw_arc_slash(
        self,
        cx: float,
        cy: float,
        radius: float,
        angle: float,
        arc: float,
        progress: float,
        color: tuple = (255, 240, 180),
    ) -> None:
        sweep = arc * min(1.0, progress * 1.15)
        start = angle - arc / 2
        steps = max(12, int(32 * progress))
        outer_r = radius * (0.85 + progress * 0.2)
        pad = int(outer_r + 12)
        size = pad * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        lcx, lcy = pad, pad
        outer_pts = [(lcx, lcy)]
        for i in range(steps + 1):
            a = start + sweep * (i / max(1, steps))
            outer_pts.append((int(lcx + math.cos(a) * outer_r), int(lcy + math.sin(a) * outer_r)))
        if len(outer_pts) > 2:
            pygame.draw.polygon(surf, (*color, int(120 * (1 - progress * 0.35))), outer_pts)
            pygame.draw.polygon(surf, (255, 255, 255, int(40 * (1 - progress))), outer_pts, 1)
        arc_pts = []
        for i in range(steps + 1):
            a = start + sweep * (i / max(1, steps))
            arc_pts.append((int(lcx + math.cos(a) * outer_r), int(lcy + math.sin(a) * outer_r)))
        if len(arc_pts) > 1:
            pygame.draw.lines(surf, (*color, 230), False, arc_pts, 5)
            pygame.draw.lines(surf, (255, 255, 255, 200), False, arc_pts, 2)
        self.screen.blit(surf, surf.get_rect(center=(int(cx), int(cy))))

    def draw_whirlwind(self, cx: float, cy: float, radius: float, angle: float, *, element: str = "default") -> None:
        from core.legendary_defs import WHIRLWIND_COLORS
        ring_c, line_col, highlight = WHIRLWIND_COLORS.get(element, WHIRLWIND_COLORS["default"])
        pad = int(radius + 16)
        size = pad * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        lcx, lcy = pad, pad
        pygame.draw.circle(surf, (*ring_c, 45), (lcx, lcy), int(radius), 2)
        for i in range(5):
            a = angle + i * (math.tau / 5)
            x1 = lcx + math.cos(a) * radius * 0.35
            y1 = lcy + math.sin(a) * radius * 0.35
            x2 = lcx + math.cos(a + 1.1) * radius
            y2 = lcy + math.sin(a + 1.1) * radius
            pygame.draw.line(surf, (*line_col, 200), (int(x1), int(y1)), (int(x2), int(y2)), 4)
            pygame.draw.line(surf, (*highlight, 120), (int(x1), int(y1)), (int(x2), int(y2)), 2)
        self.screen.blit(surf, surf.get_rect(center=(int(cx), int(cy))))

    def draw_aoe_ring_world(self, sx: float, sy: float, radius: int, color: tuple, alpha: int, width: int = 3) -> None:
        surf = pygame.Surface((radius * 2 + 8, radius * 2 + 8), pygame.SRCALPHA)
        cx, cy = radius + 4, radius + 4
        pygame.draw.circle(surf, (*color, alpha // 3), (cx, cy), radius)
        pygame.draw.circle(surf, (*color, alpha), (cx, cy), radius, width)
        pygame.draw.circle(surf, (255, 255, 255, alpha // 2), (cx, cy), max(1, radius - width), 1)
        self.screen.blit(surf, (int(sx) - radius - 4, int(sy) - radius - 4))

    def draw_dash_trail(self, sx: float, sy: float, anim: float) -> None:
        for i in range(3):
            a = anim * 8.0 - i * 0.4
            r = 26 - i * 5
            alpha = 80 - i * 22
            surf = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (218, 175, 55, alpha), (r, r), r, 2)
            self.screen.blit(surf, surf.get_rect(center=(int(sx), int(sy))))
