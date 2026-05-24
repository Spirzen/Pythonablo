"""Player skills: AOE, fireball, summon, whirlwind (RMB), legendary overrides."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from core.event_bus import EventBus
from entities.enemy import EnemyEntity
from entities.minion import MinionEntity
from entities.player import PlayerEntity
from systems.effects import EffectSystem
from systems.enemy_status import apply_damage_with_curse
from systems.legendary_skills import LegendarySkillCaster
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


class SkillSystem(LegendarySkillCaster):
    COOLDOWNS = {"aoe": 4.0, "fireball": 1.2, "summon": 12.0, "pulse": 6.0}
    MANA_COSTS = {"aoe": 18.0, "fireball": 10.0, "summon": 28.0, "pulse": 14.0, "whirlwind": 6.0}

    OVERRIDE_COOLDOWNS = {
        "power_strike": 5.0, "knife_fan": 2.5, "meteor": 6.0, "ice_wave": 5.0,
        "chain_lightning": 4.0, "poison": 5.0, "burning": 5.0, "bleeding": 4.5,
        "curse": 6.0, "battle_cry": 10.0, "mana_shield": 8.0, "ice_armor": 8.0,
        "vampirism": 10.0, "reflect": 10.0,
    }
    OVERRIDE_MANA = {
        "power_strike": 22.0, "knife_fan": 14.0, "meteor": 24.0, "ice_wave": 18.0,
        "chain_lightning": 16.0, "poison": 14.0, "burning": 14.0, "bleeding": 12.0,
        "curse": 16.0, "battle_cry": 12.0, "mana_shield": 10.0, "ice_armor": 10.0,
        "vampirism": 14.0, "reflect": 12.0,
    }

    def __init__(self, events: EventBus, effects: EffectSystem) -> None:
        self.events = events
        self.effects = effects
        self.projectiles: list[SkillProjectile] = []
        self.minions: list[MinionEntity] = []
        self.cooldowns: dict[str, float] = {k: 0.0 for k in self.COOLDOWNS}
        self.whirlwind_angle: float = 0.0
        self.whirlwind_tick: float = 0.0
        self.ice_waves: list[dict] = []
        self.rng = random.Random()

    def skill_damage(self, player: PlayerEntity, base: float) -> float:
        lvl = player.experience.level
        dmg = base * (1.0 + (lvl - 1) * 0.14) + player.damage * 0.35
        dmg += player.skill_damage_bonus
        dmg_mult, _ = player.equipment.skill_bonuses()
        mult = player.skill_tree.skill_damage_mult()
        if player.buffs.has("battle_cry"):
            mult *= 1.25
        return dmg * dmg_mult * mult

    def skill_radius_mult(self, player: PlayerEntity, skill_id: str = "aoe") -> float:
        _, radius_mult = player.equipment.skill_bonuses()
        return radius_mult * player.skill_upgrades.radius_mult(skill_id)

    def try_skill(self, skill_id: str, player: PlayerEntity, enemies: list[EnemyEntity], game_map: GameMap, mouse_world: tuple[float, float]) -> bool:
        effective = player.equipment.effective_skill(skill_id)
        cd_key = skill_id
        if self.cooldowns.get(cd_key, 0) > 0:
            return False

        if effective != skill_id:
            cost = self.OVERRIDE_MANA.get(effective, 14.0)
            if player.mana < cost:
                return False
            player.stats.mana -= cost
            cd = self.OVERRIDE_COOLDOWNS.get(effective, 5.0) * player.skill_tree.cooldown_mult()
            self.cooldowns[cd_key] = cd
            return self.cast_override(effective, player, enemies, mouse_world)

        if skill_id == "fireball":
            return self._cast_fireball(player, enemies, mouse_world)
        if skill_id == "aoe":
            return self._cast_aoe(player, enemies)
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
        cd_mult = player.skill_tree.cooldown_mult()
        self.cooldowns[skill_id] = self.COOLDOWNS[skill_id] * cd_mult
        return True

    def _cast_aoe(self, player: PlayerEntity, enemies: list[EnemyEntity]) -> bool:
        if not self._spend(player, "aoe"):
            return False
        dmg = self.skill_damage(player, 32.0)
        radius = 2.2 * self.skill_radius_mult(player, "aoe")
        ring_size = 90.0 * self.skill_radius_mult(player, "aoe")
        self.effects.spawn_aoe_ring(player.x, player.y, ring_size, (255, 160, 60))
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
        radius = 1.8 * self.skill_radius_mult(player, "pulse")
        ring_size = 70.0 * self.skill_radius_mult(player, "pulse")
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
        if math.hypot(dx, dy) < 0.05:
            angle = player.facing_angle
        else:
            angle = math.atan2(dy, dx)
            player.facing_angle = angle
        speed = 9.0
        fb_radius = 0.22 * player.skill_upgrades.fireball_radius_mult()
        self.projectiles.append(
            SkillProjectile(
                player.x, player.y,
                math.cos(angle) * speed, math.sin(angle) * speed,
                self.skill_damage(player, 28.0),
                radius=fb_radius,
            )
        )
        return True

    def _fireball_explosion(self, player: PlayerEntity, enemies: list[EnemyEntity], x: float, y: float, base_dmg: float) -> None:
        splash = base_dmg * 0.75
        radius = 2.4
        self.effects.spawn_death_explosion(x, y, big=True)
        self.effects.spawn_aoe_ring(x, y, 110.0, (255, 120, 40))
        for e in enemies:
            if not e.alive:
                continue
            if math.hypot(e.x - x, e.y - y) <= radius + e.current_radius:
                apply_damage_with_curse(e, splash)
                self.events.emit("enemy_hit", enemy=e, damage=splash)
                if e.hp <= 0:
                    e.alive = False
                    self.events.emit("enemy_killed", enemy=e, killer=player)

    def _cast_summon(self, player: PlayerEntity, game_map: GameMap) -> bool:
        if not self._spend(player, "summon"):
            return False
        if len(self.minions) >= player.skill_upgrades.max_minions():
            return False
        ox = player.x + self.rng.uniform(-0.5, 0.5)
        oy = player.y + self.rng.uniform(-0.5, 0.5)
        if not can_occupy(game_map, ox, oy):
            ox, oy = player.x, player.y
        hp_mult = player.skill_upgrades.minion_hp_mult()
        mhp = (35 + player.experience.level * 4) * hp_mult
        dmg = self.skill_damage(player, 10.0)
        self.minions.append(MinionEntity(x=ox, y=oy, hp=mhp, max_hp=mhp, damage=dmg, life=20.0))
        self.effects.spawn_aoe_ring(ox, oy, 40.0, (120, 255, 160))
        return True

    def update_whirlwind(self, player: PlayerEntity, enemies: list[EnemyEntity], held: bool, dt: float) -> None:
        if not held:
            return
        mana_tick = self.MANA_COSTS["whirlwind"] * dt
        if player.mana < mana_tick:
            return
        player.stats.mana -= mana_tick
        self.whirlwind_angle += dt * 9.0 * player.attack_speed_mult
        self.whirlwind_tick -= dt
        if self.whirlwind_tick > 0:
            return
        self.whirlwind_tick = 0.14
        dmg = self.skill_damage(player, 11.0) * player.skill_upgrades.whirlwind_damage_mult()
        radius = 1.35 * self.skill_radius_mult(player, "whirlwind")
        for e in enemies:
            if not e.alive:
                continue
            if player.distance_to(e) <= radius + e.current_radius:
                self._damage_enemy(e, dmg, player)
                self.apply_whirlwind_element(player, e, dmg)

    def _heal_from_damage(self, player: PlayerEntity, damage: float) -> None:
        if player.buffs.has("vampirism_skill"):
            player.stats.hp = min(player.max_hp, player.stats.hp + damage * 0.15)
        ls = player.equipment.legendary_bonus("lifesteal")
        if ls > 0:
            player.stats.hp = min(player.max_hp, player.stats.hp + damage * 0.03 * ls)

    def _damage_enemy(self, enemy: EnemyEntity, damage: float, player: PlayerEntity) -> None:
        apply_damage_with_curse(enemy, damage)
        self.events.emit("enemy_hit", enemy=enemy, damage=damage)
        self._heal_from_damage(player, damage)
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
        self.update_ice_waves(dt, player, enemies)
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
                    if p.kind == "fireball":
                        self._fireball_explosion(player, enemies, p.x, p.y, p.damage)
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
