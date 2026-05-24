"""Pickup bonus spawning and application."""

from __future__ import annotations

import math
import random

from core.config import GameMode
from core.event_bus import EventBus
from entities.enemy import EnemyEntity
from entities.pickup_bonus import BONUS_TYPES, PickupBonus
from entities.player import PlayerEntity
from player.buffs import BONUS_LABELS, BuffManager
from systems.effects import EffectSystem


class BonusSystem:
  BONUS_DROP_CHANCE = 0.12
  BONUS_DURATIONS = {
    "armor": 15.0,
    "speed": 12.0,
    "damage": 12.0,
    "pain_aura": 10.0,
    "skill_boost": 15.0,
  }

  def __init__(self, events: EventBus, effects: EffectSystem) -> None:
    self.events = events
    self.effects = effects
    self.rng = random.Random()
    self.ground_bonuses: list[PickupBonus] = []
    self.game_mode = GameMode.CLASSIC
    events.subscribe("enemy_killed", self._on_kill)

  def set_game_mode(self, mode: GameMode) -> None:
    self.game_mode = mode

  def _on_kill(self, enemy: EnemyEntity, **_) -> None:
    chance = 1.0 if self.game_mode == GameMode.SPEED else self.BONUS_DROP_CHANCE
    if self.rng.random() > chance:
      return
    bonus_type = self.rng.choice(BONUS_TYPES)
    self.ground_bonuses.append(
      PickupBonus(x=enemy.x, y=enemy.y, bonus_type=bonus_type, bob_phase=self.rng.random() * 6.28)
    )

  def try_pickup(self, player: PlayerEntity, enemies: list[EnemyEntity], *, threshold: float = 1.2) -> str | None:
    for bonus in list(self.ground_bonuses):
      if player.distance_sq_to(bonus.x, bonus.y) >= threshold * threshold:
        continue
      label = self.apply_bonus(player, bonus.bonus_type, enemies)
      self.ground_bonuses.remove(bonus)
      self.events.emit("bonus_picked", label=label, bonus_type=bonus.bonus_type)
      return label
    return None

  def apply_bonus(self, player: PlayerEntity, bonus_type: str, enemies: list[EnemyEntity]) -> str:
    label = BONUS_LABELS.get(bonus_type, "Бонус!")
    if bonus_type == "explosion":
      self._explosion(player, enemies)
      return label
    duration = self.BONUS_DURATIONS.get(bonus_type, 12.0)
    player.buffs.add(bonus_type, duration, magnitude=1.0)
    return label

  def _explosion(self, player: PlayerEntity, enemies: list[EnemyEntity]) -> None:
    radius = 2.8
    dmg = player.damage * 1.5 + player.skill_damage_bonus * 0.5
    self.effects.spawn_death_explosion(player.x, player.y, big=True)
    self.effects.spawn_aoe_ring(player.x, player.y, 100.0, (255, 140, 40))
    for enemy in enemies:
      if not enemy.alive:
        continue
      if player.distance_to(enemy) <= radius + enemy.current_radius:
        enemy.take_damage(dmg)
        if enemy.hp <= 0:
          enemy.alive = False
          self.events.emit("enemy_killed", enemy=enemy, killer=player)

  def update(self, dt: float, player: PlayerEntity, enemies: list[EnemyEntity]) -> None:
    player.buffs.update(dt)
    if player.buffs.has("pain_aura"):
      player.buffs.pain_aura_tick -= dt
      if player.buffs.pain_aura_tick <= 0:
        player.buffs.pain_aura_tick = 0.5
        radius = 2.5
        dmg = player.damage * 0.35 + 8.0
        self.effects.spawn_aoe_ring(player.x, player.y, 55.0, (180, 50, 220))
        for enemy in enemies:
          if enemy.alive and player.distance_to(enemy) <= radius + enemy.current_radius:
            enemy.take_damage(dmg)
            if enemy.hp <= 0:
              enemy.alive = False
              self.events.emit("enemy_killed", enemy=enemy, killer=player)

  def ground_to_dict(self) -> list[dict]:
    return [{"x": b.x, "y": b.y, "bonus_type": b.bonus_type, "bob_phase": b.bob_phase} for b in self.ground_bonuses]

  def restore_ground(self, data: list) -> None:
    self.ground_bonuses = [
      PickupBonus(x=raw["x"], y=raw["y"], bonus_type=raw.get("bonus_type", "armor"), bob_phase=raw.get("bob_phase", 0.0))
      for raw in data
    ]
