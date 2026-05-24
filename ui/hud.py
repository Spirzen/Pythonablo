"""HUD overlay — polished dark fantasy UI."""

from __future__ import annotations

import math

import pygame

from core.config import SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_HP_BG, UI_HP_FILL, UI_MARGIN, UI_MP_BG, UI_MP_FILL, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer
from entities.player import PlayerEntity
from core.legendary_defs import SKILL_OVERRIDE_LABELS
from ui.styles import UIStyles
from ui.tooltip import TooltipDrawer, skill_tooltip_rows


class HUD:
    HUD_W = 420
    HUD_H = 138
    PAD = 14
    INV_BTN = 56
    SKILL_SLOT = 56
    SKILL_GAP = 10

    SKILL_COLORS = {
        "fireball": (255, 90, 40),
        "aoe": (255, 160, 60),
        "summon": (120, 255, 140),
        "pulse": (120, 180, 255),
        "power_strike": (255, 200, 80),
        "knife_fan": (200, 200, 220),
        "meteor": (255, 120, 40),
        "ice_wave": (100, 200, 255),
        "chain_lightning": (180, 220, 255),
        "poison": (80, 220, 80),
        "burning": (255, 140, 40),
        "bleeding": (200, 60, 60),
        "curse": (160, 80, 200),
        "battle_cry": (255, 200, 60),
        "mana_shield": (110, 180, 255),
        "ice_armor": (100, 200, 255),
        "vampirism": (200, 60, 80),
        "reflect": (200, 200, 255),
    }

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self.tooltips = TooltipDrawer(renderer)
        self.inventory_btn = pygame.Rect(0, 0, self.INV_BTN, self.INV_BTN)
        self._skill_rects: list[tuple[pygame.Rect, str]] = []
        self._ww_rect = pygame.Rect(0, 0, 0, 0)
        self._mouse_pos = (0, 0)
        self._anim = 0.0
        self._icon_fire: pygame.Surface | None = None
        self._icon_whirlwind: pygame.Surface | None = None
        self._icon_inventory: pygame.Surface | None = None
        self._stat_cache: dict[str, object] = {}
        self._stat_surfaces: dict[str, pygame.Surface] = {}

    def set_icons(
        self,
        *,
        fire: pygame.Surface | None = None,
        whirlwind: pygame.Surface | None = None,
        inventory: pygame.Surface | None = None,
    ) -> None:
        self._icon_fire = fire
        self._icon_whirlwind = whirlwind
        self._icon_inventory = inventory

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
            hint = r.font_small.render("ЛКМ — удар/стрела   ПКМ — вихрь   1/F — огонь   2–4 — скиллы   E — подбор   ESC — пауза", True, UI_TEXT_DIM)
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
        r.draw_panel(hud, alpha=235, accent_top=True)

        inner_l = hud.left + self.PAD
        inner_r = hud.right - self.PAD
        top = hud.top + self.PAD

        stats = {
            "floor": floor,
            "level": player.experience.level,
            "kills": kills,
            "dash": int(math.ceil(dash_cd)) if dash_cd > 0 else -1,
            "xp": (player.experience.xp, player.experience.xp_to_next),
            "hp": (int(player.hp), int(player.max_hp)),
            "mp": (int(player.mana), int(player.max_mana)),
        }
        if stats != self._stat_cache:
            self._stat_cache = stats
            self._stat_surfaces = {
                "floor": r.render_text(r.font_label, f"ЭТАЖ {floor}", UI_ACCENT),
                "level": r.render_text(r.font_label, f"УР. {player.experience.level}", UI_TEXT),
                "kills": r.render_text(r.font_small, f"Убийств: {kills}", UI_TEXT_DIM),
                "xp": r.render_text(
                    r.font_small,
                    f"XP {player.experience.xp}/{player.experience.xp_to_next}",
                    UI_TEXT_DIM,
                ),
                "hp": r.render_text(r.font_small, f"HP {int(player.hp)}/{int(player.max_hp)}", UI_TEXT),
                "mp": r.render_text(r.font_small, f"MP {int(player.mana)}/{int(player.max_mana)}", UI_TEXT_DIM),
            }

        r.screen.blit(self._stat_surfaces["floor"], (inner_l, top))
        r.screen.blit(self._stat_surfaces["level"], (inner_l + 108, top))

        dash_ready = dash_cd <= 0
        dash_text = "РЫВОК [ПРОБЕЛ]" if dash_ready else f"РЫВОК {math.ceil(dash_cd):.0f}с"
        dash_color = UI_HP_FILL if dash_ready else UI_TEXT_DIM
        dash_s = r.render_text(r.font_label, dash_text, dash_color)
        r.screen.blit(dash_s, dash_s.get_rect(topright=(inner_r, top)))

        row2 = top + 22
        r.screen.blit(self._stat_surfaces["kills"], (inner_l, row2))

        xp_ratio = player.experience.xp / max(1, player.experience.xp_to_next)
        bar_w = inner_r - inner_l
        xp_y = row2 + 18
        r.screen.blit(self._stat_surfaces["xp"], (inner_l, xp_y))
        r.draw_bar(inner_l, xp_y + 14, bar_w, 8, xp_ratio, (255, 204, 96), (48, 40, 22), radius=4, glossy=True)

        hp_y = xp_y + 28
        r.screen.blit(self._stat_surfaces["hp"], (inner_l, hp_y))
        r.draw_bar(inner_l, hp_y + 16, bar_w, 12, player.hp / max(1, player.max_hp), UI_HP_FILL, UI_HP_BG, glossy=True)

        mp_y = hp_y + 36
        r.screen.blit(self._stat_surfaces["mp"], (inner_l, mp_y))
        r.draw_bar(inner_l, mp_y + 16, bar_w, 10, player.mana / max(1, player.max_mana), UI_MP_FILL, UI_MP_BG, radius=5, glossy=True)

    def _skill_layout(self, player: PlayerEntity) -> list[tuple[str, str, str, tuple, str | None]]:
        rows = []
        for key, sid, short in player.equipment.hud_skill_layout():
            if sid in SKILL_OVERRIDE_LABELS:
                short = SKILL_OVERRIDE_LABELS[sid][:5]
            color = self.SKILL_COLORS.get(sid, (180, 180, 200))
            icon = "fire" if sid == "fireball" else None
            rows.append((key, sid, short, color, icon))
        return rows

    def _skill_bar_origin(self) -> tuple[int, int]:
        n = 5
        total_w = n * self.SKILL_SLOT + (n - 1) * self.SKILL_GAP
        right_limit = self.inventory_btn.left - 20
        x0 = max(UI_MARGIN + 8, right_limit - total_w)
        y0 = self.inventory_btn.centery - self.SKILL_SLOT // 2
        return x0, y0

    def _draw_bottom_bar_panel(self, r: Renderer) -> None:
        x0, y0 = self._skill_bar_origin()
        n = 5
        total_w = n * self.SKILL_SLOT + (n - 1) * self.SKILL_GAP
        panel = pygame.Rect(x0 - 12, y0 - 10, total_w + 24, self.SKILL_SLOT + 20)
        r.draw_panel(panel, alpha=180, radius=14)

    def _draw_bottom_bar(self, r: Renderer, cds: dict[str, float], whirlwind: bool, player: PlayerEntity) -> None:
        layout = self._skill_layout(player)
        x0, y0 = self._skill_bar_origin()
        self._skill_rects = []

        base_cd_map = {
            "fireball": "fireball", "aoe": "aoe", "summon": "summon", "pulse": "pulse",
        }
        for i, (key, sid, short, color, icon_key) in enumerate(layout):
            rect = pygame.Rect(x0 + i * (self.SKILL_SLOT + self.SKILL_GAP), y0, self.SKILL_SLOT, self.SKILL_SLOT)
            cd_key = sid if sid in cds else next((b for b, o in player.equipment.skill_overrides().items() if o == sid), sid)
            if cd_key not in cds:
                for base in ("aoe", "summon", "pulse"):
                    if player.equipment.effective_skill(base) == sid:
                        cd_key = base
                        break
            self._skill_rects.append((rect, sid))
            from systems.skill_system import SkillSystem
            max_cd = SkillSystem.COOLDOWNS.get(cd_key, SkillSystem.OVERRIDE_COOLDOWNS.get(sid, 4.0))
            cd = max(0.0, cds.get(cd_key, 0.0))
            hovered = rect.collidepoint(self._mouse_pos)
            icon = self._icon_fire if icon_key == "fire" else None
            self._draw_skill_slot(r, rect, key, short, color, cd, max_cd, hovered, icon=icon)

        ww_i = len(layout)
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
        icon: pygame.Surface | None = None,
    ) -> None:
        ready = cd <= 0.05
        bg = (44, 48, 68) if hovered else (20, 22, 36)
        surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*bg, 240), (0, 0, rect.w, rect.h), border_radius=12)
        border = UI_ACCENT if hovered else (color if ready else (70, 76, 98))
        pygame.draw.rect(surf, (*border, 255), (0, 0, rect.w, rect.h), width=2, border_radius=12)
        r.screen.blit(surf, rect.topleft)

        inner = rect.inflate(-8, -8)
        if icon is not None and ready:
            r.blit_icon(icon, inner, pad=2)
        elif icon is not None and not ready:
            r.blit_icon(icon, inner, alpha=90, pad=2)
        else:
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
        if icon is None:
            nm = r.font_label.render(name, True, UI_TEXT_DIM)
            r.screen.blit(nm, nm.get_rect(midbottom=(rect.centerx, rect.bottom - 6)))

        if not ready:
            ratio = min(1.0, cd / max_cd)
            UIStyles.draw_radial_cooldown(r.screen, inner, ratio)
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
        if self._icon_whirlwind is not None:
            r.blit_icon(self._icon_whirlwind, inner, alpha=255 if active else 170, pad=2)
        lbl = r.font_label.render("ПКМ", True, UI_TEXT if active else UI_TEXT_DIM)
        r.screen.blit(lbl, lbl.get_rect(topleft=(rect.left + 7, rect.top + 6)))
        if self._icon_whirlwind is None:
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
        if self._icon_inventory is not None:
            icon_rect = rect.inflate(-10, -10)
            r.blit_icon(self._icon_inventory, icon_rect, pad=0)
        else:
            cx, cy = rect.center
            pygame.draw.rect(r.screen, UI_ACCENT, (cx - 13, cy - 7, 26, 18), border_radius=5)
            pygame.draw.arc(r.screen, UI_ACCENT, (cx - 8, cy - 16, 16, 16), 0, math.pi, 2)
            bag = r.font_label.render("INV", True, UI_TEXT_DIM)
            r.screen.blit(bag, bag.get_rect(midbottom=(cx, rect.bottom - 5)))

    def draw_level_up_banner(self, text: str, remaining: float) -> None:
        r = self.renderer
        alpha = min(1.0, remaining / 0.5)
        pulse = 0.5 + 0.5 * math.sin(self._anim * 8)
        y = 200
        r.blit_text_outlined(
            r.font_huge,
            text,
            (255, 220, 80),
            (SCREEN_WIDTH // 2 - 160, y),
            outline=(80, 50, 10),
            outline_width=3,
            alpha=int(255 * alpha),
        )
        sub = r.font_mid.render("+1 очко навыка", True, UI_ACCENT)
        sub.set_alpha(int(220 * alpha * pulse))
        r.screen.blit(sub, sub.get_rect(midtop=(SCREEN_WIDTH // 2, y + 58)))

    def draw_arena_timer(self, remaining: float, *, round_num: int | None = None) -> None:
        r = self.renderer
        if round_num is not None:
            text = f"РАУНД {round_num} — {max(0, int(remaining) + 1)} сек"
        else:
            text = f"АРЕНА — {max(0, int(remaining) + 1)} сек"
        pulse = 0.7 + 0.3 * math.sin(self._anim * 6)
        col = (int(255 * pulse), int(120 * pulse), int(80 * pulse))
        surf = pygame.Surface((380, 48), pygame.SRCALPHA)
        pygame.draw.rect(surf, (40, 12, 12, 220), (0, 0, 380, 48), border_radius=12)
        pygame.draw.rect(surf, (*UI_ACCENT, 80), (0, 0, 380, 48), width=2, border_radius=12)
        label = r.render_text(r.font_mid, text, col)
        surf.blit(label, label.get_rect(center=(190, 24)))
        r.screen.blit(surf, surf.get_rect(midtop=(SCREEN_WIDTH // 2, UI_MARGIN + self.HUD_H + 8)))

    def draw_toast(self, message: str) -> None:
        r = self.renderer
        text = r.render_text(r.font_mid, message, UI_TEXT)
        surf = pygame.Surface((max(520, text.get_width() + 48), 48), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*UI_CARD, 235), (0, 0, surf.get_width(), 48), border_radius=12)
        pygame.draw.rect(surf, (*UI_ACCENT, 100), (0, 0, surf.get_width(), 48), width=2, border_radius=12)
        surf.blit(text, text.get_rect(center=(surf.get_width() // 2, 24)))
        r.screen.blit(surf, surf.get_rect(midbottom=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 120)))

    def draw_floating_texts(self, texts: list[tuple[float, float, str, tuple, float]], camera) -> None:
        r = self.renderer
        for wx, wy, msg, color, alpha in texts:
            if not msg:
                continue
            sx, sy = camera.world_to_screen(wx, wy)
            r.blit_text_outlined(
                r.font_mid, msg, color,
                (int(sx) - len(msg) * 4, int(sy) - 40),
                outline=(20, 10, 10), alpha=int(255 * alpha),
            )
