"""HUD overlay — polished dark fantasy UI."""

from __future__ import annotations

import math

import pygame

from core.config import SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_HP_BG, UI_HP_FILL, UI_MARGIN, UI_MP_BG, UI_MP_FILL, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer
from entities.player import PlayerEntity
from systems.skill_system import SkillSystem
from ui.tooltip import TooltipDrawer, skill_tooltip_rows


class HUD:
    HUD_W = 420
    HUD_H = 124
    PAD = 14
    INV_BTN = 56
    SKILL_SLOT = 56
    SKILL_GAP = 10

    SKILL_META = [
        ("1", "aoe", "Волна", (255, 160, 60)),
        ("2", "fireball", "Огонь", (255, 90, 40)),
        ("3", "summon", "Приз.", (120, 255, 140)),
        ("4", "pulse", "Имп.", (120, 180, 255)),
    ]

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self.tooltips = TooltipDrawer(renderer)
        self.inventory_btn = pygame.Rect(0, 0, self.INV_BTN, self.INV_BTN)
        self._skill_rects: list[tuple[pygame.Rect, str]] = []
        self._ww_rect = pygame.Rect(0, 0, 0, 0)
        self._mouse_pos = (0, 0)
        self._anim = 0.0

    def _layout(self) -> None:
        self.inventory_btn = pygame.Rect(
            SCREEN_WIDTH - UI_MARGIN - self.INV_BTN,
            SCREEN_HEIGHT - UI_MARGIN - self.INV_BTN,
            self.INV_BTN,
            self.INV_BTN,
        )

    def inventory_clicked(self, pos: tuple[int, int]) -> bool:
        self._layout()
        return self.inventory_btn.collidepoint(pos)

    def draw(
        self,
        player: PlayerEntity,
        floor: int,
        kills: int,
        dash_cd: float,
        *,
        skill_cooldowns: dict[str, float] | None = None,
        whirlwind: bool = False,
        inventory_open: bool = False,
        mouse_pos: tuple[int, int] | None = None,
        portal_hint: str | None = None,
    ) -> None:
        r = self.renderer
        skill_cooldowns = skill_cooldowns or {}
        if mouse_pos:
            self._mouse_pos = mouse_pos
        self._layout()
        self._anim += 0.016

        self._draw_top_hud(r, player, floor, kills, dash_cd)

        if not inventory_open:
            self._draw_bottom_bar_panel(r)
            self._draw_bottom_bar(r, skill_cooldowns, whirlwind, player)
            self._draw_inventory_button(r)
            hint_y = SCREEN_HEIGHT - UI_MARGIN - self.INV_BTN - 18
            hint = r.font_small.render("ЛКМ — удар   ПКМ — вихрь   1–4 — скиллы   E — взаимодействие", True, UI_TEXT_DIM)
            r.screen.blit(hint, hint.get_rect(midbottom=(SCREEN_WIDTH // 2, hint_y)))
            if portal_hint:
                pulse = 0.7 + 0.3 * math.sin(self._anim * 4.0)
                col = (int(255 * pulse), int(204 * pulse), int(96 * pulse))
                ph = r.font_menu.render(portal_hint, True, col)
                shadow = r.font_menu.render(portal_hint, True, (20, 14, 8))
                rect = ph.get_rect(midbottom=(SCREEN_WIDTH // 2, hint_y - 30))
                r.screen.blit(shadow, shadow.get_rect(midbottom=(rect.midbottom[0] + 1, rect.midbottom[1] + 1)))
                r.screen.blit(ph, rect)
            self._draw_skill_tooltip(player, skill_cooldowns)

    def _draw_top_hud(self, r: Renderer, player: PlayerEntity, floor: int, kills: int, dash_cd: float) -> None:
        hud = pygame.Rect(UI_MARGIN, UI_MARGIN, self.HUD_W, self.HUD_H)
        r.draw_panel(hud, alpha=230)

        inner_l = hud.left + self.PAD
        inner_r = hud.right - self.PAD
        top = hud.top + self.PAD

        floor_s = r.font_label.render(f"ЭТАЖ {floor}", True, UI_ACCENT)
        r.screen.blit(floor_s, (inner_l, top))
        lvl = r.font_label.render(f"УР. {player.experience.level}", True, UI_TEXT)
        r.screen.blit(lvl, (inner_l + 108, top))

        dash_ready = dash_cd <= 0
        dash_text = "РЫВОК [ПРОБЕЛ]" if dash_ready else f"РЫВОК {math.ceil(dash_cd):.0f}с"
        dash_color = UI_HP_FILL if dash_ready else UI_TEXT_DIM
        dash_s = r.font_label.render(dash_text, True, dash_color)
        r.screen.blit(dash_s, dash_s.get_rect(topright=(inner_r, top)))

        row2 = top + 22
        r.screen.blit(r.font_small.render(f"Убийств: {kills}", True, UI_TEXT_DIM), (inner_l, row2))
        xp_s = r.font_small.render(f"XP {player.experience.xp}/{player.experience.xp_to_next}", True, UI_TEXT_DIM)
        r.screen.blit(xp_s, xp_s.get_rect(topright=(inner_r, row2)))

        bar_w = inner_r - inner_l
        hp_y = row2 + 22
        r.screen.blit(r.font_small.render(f"HP {int(player.hp)}/{int(player.max_hp)}", True, UI_TEXT), (inner_l, hp_y))
        r.draw_bar(inner_l, hp_y + 16, bar_w, 12, player.hp / max(1, player.max_hp), UI_HP_FILL, UI_HP_BG, glossy=True)

        mp_y = hp_y + 36
        r.screen.blit(r.font_small.render(f"MP {int(player.mana)}/{int(player.max_mana)}", True, UI_TEXT_DIM), (inner_l, mp_y))
        r.draw_bar(inner_l, mp_y + 16, bar_w, 10, player.mana / max(1, player.max_mana), UI_MP_FILL, UI_MP_BG, radius=5, glossy=True)

    def _skill_bar_origin(self) -> tuple[int, int]:
        n = len(self.SKILL_META) + 1
        total_w = n * self.SKILL_SLOT + (n - 1) * self.SKILL_GAP
        right_limit = self.inventory_btn.left - 20
        x0 = max(UI_MARGIN + 8, right_limit - total_w)
        y0 = self.inventory_btn.centery - self.SKILL_SLOT // 2
        return x0, y0

    def _draw_bottom_bar_panel(self, r: Renderer) -> None:
        x0, y0 = self._skill_bar_origin()
        n = len(self.SKILL_META) + 1
        total_w = n * self.SKILL_SLOT + (n - 1) * self.SKILL_GAP
        panel = pygame.Rect(x0 - 12, y0 - 10, total_w + 24, self.SKILL_SLOT + 20)
        r.draw_panel(panel, alpha=180, radius=14)

    def _draw_bottom_bar(self, r: Renderer, cds: dict[str, float], whirlwind: bool, player: PlayerEntity) -> None:
        x0, y0 = self._skill_bar_origin()
        self._skill_rects = []

        for i, (key, sid, short, color) in enumerate(self.SKILL_META):
            rect = pygame.Rect(x0 + i * (self.SKILL_SLOT + self.SKILL_GAP), y0, self.SKILL_SLOT, self.SKILL_SLOT)
            self._skill_rects.append((rect, sid))
            max_cd = SkillSystem.COOLDOWNS.get(sid, 1.0)
            cd = max(0.0, cds.get(sid, 0.0))
            hovered = rect.collidepoint(self._mouse_pos)
            self._draw_skill_slot(r, rect, key, short, color, cd, max_cd, hovered)

        ww_i = len(self.SKILL_META)
        self._ww_rect = pygame.Rect(x0 + ww_i * (self.SKILL_SLOT + self.SKILL_GAP), y0, self.SKILL_SLOT, self.SKILL_SLOT)
        self._draw_whirlwind_slot(r, self._ww_rect, whirlwind, self._ww_rect.collidepoint(self._mouse_pos))

    def _draw_skill_tooltip(self, player: PlayerEntity, cds: dict[str, float]) -> None:
        mx, my = self._mouse_pos
        for rect, sid in self._skill_rects:
            if rect.collidepoint(mx, my):
                rows = skill_tooltip_rows(sid, player, cds.get(sid, 0.0))
                self.tooltips.draw_at((mx, my), rows, prefer_above=True)
                return
        if self._ww_rect.collidepoint(mx, my):
            rows = skill_tooltip_rows("whirlwind", player, 0.0)
            self.tooltips.draw_at((mx, my), rows, prefer_above=True)

    def _draw_skill_slot(
        self,
        r: Renderer,
        rect: pygame.Rect,
        key: str,
        name: str,
        color: tuple,
        cd: float,
        max_cd: float,
        hovered: bool = False,
    ) -> None:
        ready = cd <= 0.05
        bg = (44, 48, 68) if hovered else (20, 22, 36)
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*bg, 240), (0, 0, rect.w, rect.h), border_radius=12)
        border = UI_ACCENT if hovered else (color if ready else (70, 76, 98))
        pygame.draw.rect(surf, (*border, 255), (0, 0, rect.w, rect.h), width=2, border_radius=12)
        r.screen.blit(surf, rect.topleft)

        inner = rect.inflate(-8, -8)
        inner_col = color if ready else tuple(int(c * 0.3) for c in color)
        inner_s = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
        pygame.draw.rect(inner_s, (*inner_col, 200 if ready else 100), (0, 0, inner.w, inner.h), border_radius=8)
        if ready:
            glow = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*color, 40), (0, 0, inner.w, inner.h), border_radius=8)
            inner_s.blit(glow, (0, 0))
        r.screen.blit(inner_s, inner.topleft)

        k = r.font_label.render(key, True, UI_TEXT if ready else UI_TEXT_DIM)
        r.screen.blit(k, k.get_rect(topleft=(rect.left + 8, rect.top + 6)))
        nm = r.font_label.render(name, True, UI_TEXT_DIM)
        r.screen.blit(nm, nm.get_rect(midbottom=(rect.centerx, rect.bottom - 6)))

        if not ready:
            ratio = min(1.0, cd / max_cd)
            veil_h = max(1, int(inner.height * ratio))
            veil = pygame.Surface((inner.width, veil_h), pygame.SRCALPHA)
            veil.fill((6, 8, 18, 200))
            r.screen.blit(veil, (inner.left, inner.top))
            cd_text = f"{cd:.1f}" if cd < 10 else f"{int(math.ceil(cd))}"
            cd_w = r.font_mid.size(cd_text)[0]
            r.blit_text_outlined(
                r.font_mid, cd_text, (255, 230, 120),
                (rect.centerx - cd_w // 2, rect.centery - 12),
                outline=(40, 20, 8),
            )

    def _draw_whirlwind_slot(self, r: Renderer, rect: pygame.Rect, active: bool, hovered: bool = False) -> None:
        bg = (44, 48, 68) if hovered else (20, 22, 36)
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*bg, 240), (0, 0, rect.w, rect.h), border_radius=12)
        c = (150, 200, 255) if active or hovered else (90, 110, 140)
        pygame.draw.rect(surf, (*c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=12)
        r.screen.blit(surf, rect.topleft)
        inner = rect.inflate(-8, -8)
        if active:
            inner_s = pygame.Surface((inner.w, inner.h), pygame.SRCALPHA)
            pygame.draw.rect(inner_s, (100, 160, 220, 180), (0, 0, inner.w, inner.h), border_radius=8)
            r.screen.blit(inner_s, inner.topleft)
        lbl = r.font_label.render("ПКМ", True, UI_TEXT if active else UI_TEXT_DIM)
        r.screen.blit(lbl, lbl.get_rect(topleft=(rect.left + 7, rect.top + 6)))
        sub = r.font_label.render("Вихрь", True, UI_TEXT_DIM)
        r.screen.blit(sub, sub.get_rect(midbottom=(rect.centerx, rect.bottom - 6)))

    def _draw_inventory_button(self, r: Renderer) -> None:
        rect = self.inventory_btn
        hovered = rect.collidepoint(self._mouse_pos)
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        fill = (52, 58, 88) if hovered else UI_CARD
        pygame.draw.rect(surf, (*fill, 245), (0, 0, rect.w, rect.h), border_radius=14)
        pygame.draw.rect(surf, (*UI_ACCENT, 255 if hovered else 200), (0, 0, rect.w, rect.h), width=2, border_radius=14)
        r.screen.blit(surf, rect.topleft)
        cx, cy = rect.center
        pygame.draw.rect(r.screen, UI_ACCENT, (cx - 13, cy - 7, 26, 18), border_radius=5)
        pygame.draw.arc(r.screen, UI_ACCENT, (cx - 8, cy - 16, 16, 16), 0, math.pi, 2)
        bag = r.font_label.render("INV", True, UI_TEXT_DIM)
        r.screen.blit(bag, bag.get_rect(midbottom=(cx, rect.bottom - 5)))
