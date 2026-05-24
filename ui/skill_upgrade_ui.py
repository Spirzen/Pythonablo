"""Skill upgrade selection UI."""

from __future__ import annotations

import pygame

from core.config import SCREEN_HEIGHT, SCREEN_WIDTH, UI_ACCENT, UI_CARD, UI_CARD_HOVER, UI_PANEL_BORDER, UI_TEXT, UI_TEXT_DIM
from engine.renderer import Renderer
from entities.player import PlayerEntity
from player.skill_upgrades import SKILL_UPGRADE_EFFECTS, SKILL_UPGRADE_LABELS, UPGRADEABLE_SKILLS


class SkillUpgradeUI:
  def __init__(self, renderer: Renderer) -> None:
    self.renderer = renderer
    self._rects: list[tuple[pygame.Rect, str]] = []

  def handle_click(self, pos: tuple[int, int], player: PlayerEntity) -> bool:
    if player.skill_upgrades.pending_points <= 0:
      return False
    for rect, skill_id in self._rects:
      if rect.collidepoint(pos):
        return player.skill_upgrades.upgrade(skill_id)
    return False

  def handle_input(self, confirm: bool, player: PlayerEntity, selected: int) -> bool:
    if not confirm or player.skill_upgrades.pending_points <= 0:
      return False
    if 0 <= selected < len(UPGRADEABLE_SKILLS):
      return player.skill_upgrades.upgrade(UPGRADEABLE_SKILLS[selected])
    return False

  def draw(self, player: PlayerEntity, selected: int = 0) -> None:
    r = self.renderer
    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    overlay.fill((6, 8, 18, 210))
    r.screen.blit(overlay, (0, 0))

    r.blit_text_outlined(
      r.font_huge, "УЛУЧШЕНИЕ НАВЫКА", UI_ACCENT,
      (SCREEN_WIDTH // 2 - 220, 100), outline=(30, 20, 10), outline_width=3,
    )
    pts = player.skill_upgrades.pending_points
    r.blit_centered(r.font_mid, f"Очков улучшения: {pts}", UI_TEXT, SCREEN_WIDTH // 2, 170)

    menu_w, item_h, gap = 520, 58, 10
    start_y = 220
    self._rects = []
    mx, my = pygame.mouse.get_pos()
    for i, skill_id in enumerate(UPGRADEABLE_SKILLS):
      rect = pygame.Rect(SCREEN_WIDTH // 2 - menu_w // 2, start_y + i * (item_h + gap), menu_w, item_h)
      self._rects.append((rect, skill_id))
      lvl = player.skill_upgrades.level_of(skill_id)
      sel = i == selected
      hovered = rect.collidepoint(mx, my)
      fill = UI_CARD_HOVER if sel or hovered else UI_CARD
      surf = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
      pygame.draw.rect(surf, (*fill, 245), (0, 0, rect.w, rect.h), border_radius=12)
      border_c = UI_ACCENT if sel else UI_PANEL_BORDER
      pygame.draw.rect(surf, (*border_c, 255), (0, 0, rect.w, rect.h), width=2, border_radius=12)
      r.screen.blit(surf, rect.topleft)
      title = f"{SKILL_UPGRADE_LABELS[skill_id]}  (ур. {lvl})"
      r.screen.blit(r.font_menu.render(title, True, UI_ACCENT if sel else UI_TEXT), (rect.left + 16, rect.top + 8))
      effect = SKILL_UPGRADE_EFFECTS.get(skill_id, "")
      r.screen.blit(r.font_small.render(effect, True, UI_TEXT_DIM), (rect.left + 16, rect.top + 32))

    r.blit_centered(r.font_small, "Клик или Enter — выбрать   ESC — позже", UI_TEXT_DIM, SCREEN_WIDTH // 2, SCREEN_HEIGHT - 60)
