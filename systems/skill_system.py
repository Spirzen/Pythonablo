"""Player skills: AOE, fireball, summon, whirlwind (RMB)."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from core.event_bus import EventBus
from entities.enemy import EnemyEntity
from entities.minion import MinionEntity
from entities.player import PlayerEntity
from systems.effects import EffectSystem
from world.collision import can_occupy, move_slide
from world.map import GameMap


@dataclass
class SkillProjectile:
    x: float
    y: float
    vx: float
    vy: float
    damage: float
    life: float = 2.5
    radius: float = 0.22
    kind: str = "fireball"


class SkillSystem:
    COOLDOWNS = {"aoe": 4.0, "fireball": 1.2, "summon": 12.0, "pulse": 6.0}
    MANA_COSTS = {"aoe": 18.0, "fireball": 10.0, "summon": 28.0, "pulse": 14.0, "whirlwind": 6.0}  # per second for whirlwind

    def __init__(self, events: EventBus, effects: EffectSystem) -> None:
        self.events = events
        self.effects = effects
        self.projectiles: list[SkillProjectile] = []
        self.minions: list[MinionEntity] = []
        self.cooldowns: dict[str, float] = {k: 0.0 for k in self.COOLDOWNS}
        self.whirlwind_angle: float = 0.0
        self.whirlwind_tick: float = 0.0
        self.rng = random.Random()

    def skill_damage(self, player: PlayerEntity, base: float) -> float:
        lvl = player.experience.level
        dmg = base * (1.0 + (lvl - 1) * 0.14) + player.damage * 0.35
        dmg += player.equipment.bonus("skill_damage")
        dmg_mult, _ = player.equipment.skill_bonuses()
        return dmg * dmg_mult

    def skill_radius_mult(self, player: PlayerEntity) -> float:
        _, radius_mult = player.equipment.skill_bonuses()
        return radius_mult

    def try_skill(self, skill_id: str, player: PlayerEntity, enemies: list[EnemyEntity], game_map: GameMap, mouse_world: tuple[float, float]) -> bool:
        if self.cooldowns.get(skill_id, 0) > 0:
            return False
        cost = self.MANA_COSTS.get(skill_id, 10)
        if player.mana < cost:
            return False

        if skill_id == "aoe":
            return self._cast_aoe(player, enemies)
        if skill_id == "fireball":
            return self._cast_fireball(player, enemies, mouse_world)
        if skill_id == "summon":
            return self._cast_summon(player, game_map)
        if skill_id == "pulse":
            return self._cast_pulse(player, enemies)
        return False

    def _spend(self, player: PlayerEntity, skill_id: str) -> bool:
        cost = self.MANA_COSTS[skill_id]
        if player.mana < cost:
            return False
        player.stats.mana -= cost
        self.cooldowns[skill_id] = self.COOLDOWNS[skill_id]
        return True

    def _cast_aoe(self, player: PlayerEntity, enemies: list[EnemyEntity]) -> bool:
        if not self._spend(player, "aoe"):
            return False
        dmg = self.skill_damage(player, 32.0)
        radius = 2.2 * self.skill_radius_mult(player)
        self.effects.spawn_aoe_ring(player.x, player.y, 90.0 * self.skill_radius_mult(player), (255, 160, 60))
        hits = 0
        for e in enemies:
            if not e.alive:
                continue
            if player.distance_to(e) <= radius + e.current_radius:
                self._damage_enemy(e, dmg, player)
                hits += 1
        self.events.emit("skill_cast", skill="aoe", hits=hits)
        return True

    def _cast_pulse(self, player: PlayerEntity, enemies: list[EnemyEntity]) -> bool:
        if not self._spend(player, "pulse"):
            return False
        dmg = self.skill_damage(player, 22.0)
        radius = 1.8 * self.skill_radius_mult(player)
        ring_size = 70.0 * self.skill_radius_mult(player)
        self.effects.spawn_aoe_ring(player.x, player.y, ring_size, (140, 200, 255))
        for e in enemies:
            if e.alive and player.distance_to(e) <= radius + e.current_radius:
                self._damage_enemy(e, dmg, player)
        return True

    def _cast_fireball(self, player: PlayerEntity, enemies: list[EnemyEntity], mouse_world: tuple[float, float]) -> bool:
        if not self._spend(player, "fireball"):
            return False
        dx = mouse_world[0] - player.x
        dy = mouse_world[1] - player.y
        dist = math.hypot(dx, dy)
        if dist < 0.05:
            angle = player.facing_angle
        else:
            angle = math.atan2(dy, dx)
            player.facing_angle = angle
        speed = 9.0
        self.projectiles.append(
            SkillProjectile(
                player.x,
                player.y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                self.skill_damage(player, 28.0),
            )
        )
        return True

    def _cast_summon(self, player: PlayerEntity, game_map: GameMap) -> bool:
        if not self._spend(player, "summon"):
            return False
        if len(self.minions) >= 3:
            return False
        ox = player.x + self.rng.uniform(-0.5, 0.5)
        oy = player.y + self.rng.uniform(-0.5, 0.5)
        if not can_occupy(game_map, ox, oy):
            ox, oy = player.x, player.y
        dmg = self.skill_damage(player, 10.0)
        self.minions.append(
            MinionEntity(
                x=ox,
                y=oy,
                hp=35 + player.experience.level * 4,
                max_hp=35 + player.experience.level * 4,
                damage=dmg,
                life=20.0,
            )
        )
        self.effects.spawn_aoe_ring(ox, oy, 40.0, (120, 255, 160))
        return True

    def update_whirlwind(self, player: PlayerEntity, enemies: list[EnemyEntity], held: bool, dt: float) -> None:
        if not held:
            return
        mana_tick = self.MANA_COSTS["whirlwind"] * dt
        if player.mana < mana_tick:
            return
        player.stats.mana -= mana_tick
        self.whirlwind_angle += dt * 9.0
        self.whirlwind_tick -= dt
        if self.whirlwind_tick > 0:
            return
        self.whirlwind_tick = 0.14
        dmg = self.skill_damage(player, 11.0)
        radius = 1.35 * self.skill_radius_mult(player)
        for e in enemies:
            if not e.alive:
                continue
            if player.distance_to(e) <= radius + e.current_radius:
                self._damage_enemy(e, dmg, player)

    def _damage_enemy(self, enemy: EnemyEntity, damage: float, player: PlayerEntity) -> None:
        enemy.take_damage(damage)
        self.events.emit("enemy_hit", enemy=enemy, damage=damage)
        if enemy.hp <= 0:
            enemy.alive = False
            self.events.emit("enemy_killed", enemy=enemy, killer=player)

    def update(
        self,
        dt: float,
        player: PlayerEntity,
        enemies: list[EnemyEntity],
        game_map: GameMap,
        whirlwind_held: bool,
        mouse_world: tuple[float, float],
    ) -> None:
        for k in self.cooldowns:
            self.cooldowns[k] = max(0.0, self.cooldowns[k] - dt)

        self.update_whirlwind(player, enemies, whirlwind_held, dt)
        self._update_projectiles(dt, player, enemies)
        self._update_minions(dt, player, enemies, game_map)

    def _update_projectiles(self, dt: float, player: PlayerEntity, enemies: list[EnemyEntity]) -> None:
        alive: list[SkillProjectile] = []
        for p in self.projectiles:
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            if p.life <= 0:
                continue
            hit = False
            for e in enemies:
                if not e.alive:
                    continue
                if math.hypot(e.x - p.x, e.y - p.y) <= p.radius + e.current_radius:
                    self._damage_enemy(e, p.damage, player)
                    hit = True
                    break
            if not hit:
                alive.append(p)
        self.projectiles = alive

    def _update_minions(self, dt: float, player: PlayerEntity, enemies: list[EnemyEntity], game_map: GameMap) -> None:
        alive_minions: list[MinionEntity] = []
        for m in self.minions:
            m.life -= dt
            if m.hp <= 0 or m.life <= 0:
                continue
            if m.hit_flash > 0:
                m.hit_flash -= dt

            target = None
            best_d = 999.0
            for e in enemies:
                if e.alive and m.distance_to(e) < best_d:
                    best_d = m.distance_to(e)
                    target = e

            if target:
                dx = target.x - m.x
                dy = target.y - m.y
                dist = math.hypot(dx, dy)
                if dist > 0.5:
                    step = min(m.speed * dt * 0.011, dist)
                    m.x, m.y = move_slide(game_map, m.x, m.y, (dx / dist) * step, (dy / dist) * step)
                m.attack_timer -= dt
                if m.attack_timer <= 0 and dist < 0.55:
                    m.attack_timer = m.attack_cooldown
                    self._damage_enemy(target, m.damage, player)
            else:
                dx = player.x - m.x
                dy = player.y - m.y
                dist = math.hypot(dx, dy)
                if dist > 1.2 and dist > 0.05:
                    step = min(m.speed * dt * 0.008, dist - 1.0)
                    m.x, m.y = move_slide(game_map, m.x, m.y, (dx / dist) * step, (dy / dist) * step)

            alive_minions.append(m)
        self.minions = alive_minions
