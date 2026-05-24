"""Combat system — melee slash or homing magic arrow."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from core.config import ATTACK_ARC, ATTACK_DAMAGE_BASE
from core.event_bus import EventBus
from entities.enemy import EnemyEntity
from entities.player import PlayerEntity
from systems.enemy_status import apply_slow


@dataclass
class SlashEffect:
    x: float
    y: float
    angle: float
    progress: float = 0.0
    duration: float = 0.16
    arc: float = math.pi
    hit_ids: set[str] | None = None

    def __post_init__(self) -> None:
        if self.hit_ids is None:
            self.hit_ids = set()


@dataclass
class HomingArrow:
    x: float
    y: float
    damage: float
    life: float = 2.8
    speed: float = 11.0
    turn_rate: float = 7.0
    radius: float = 0.18


class CombatSystem:
    SLASH_RANGE = 1.95

    def __init__(self, events: EventBus) -> None:
        self.events = events
        self.slashes: list[SlashEffect] = []
        self.arrows: list[HomingArrow] = []
        self.damage_numbers: list[tuple[float, float, int, float]] = []

    def try_attack(
        self,
        player: PlayerEntity,
        enemies: list[EnemyEntity],
        mouse_world: tuple[float, float],
        screen_pos: tuple[float, float],
        cam,
    ) -> bool:
        if player.attack_timer > 0 or player.is_dashing:
            return False
        dx = mouse_world[0] - player.x
        dy = mouse_world[1] - player.y
        if abs(dx) < 0.01 and abs(dy) < 0.01:
            angle = player.facing_angle
        else:
            angle = math.atan2(dy, dx)
            player.facing_angle = angle

        player.attack_timer = player.effective_attack_cooldown

        if player.equipment.has_homing_arrow():
            dmg = player.damage + ATTACK_DAMAGE_BASE * 0.65
            self.arrows.append(HomingArrow(player.x, player.y, dmg))
            self.events.emit("attack_swung", player=player, hit_count=0)
            return True

        self.slashes.append(SlashEffect(player.x, player.y, angle, arc=ATTACK_ARC, duration=0.15))
        hit_count = self._apply_slash_damage(player, enemies, angle)
        self.events.emit("attack_swung", player=player, hit_count=hit_count)
        return True

    def _apply_slash_damage(self, player: PlayerEntity, enemies: list[EnemyEntity], angle: float) -> int:
        damage = player.damage + ATTACK_DAMAGE_BASE * 0.5
        half_arc = ATTACK_ARC / 2
        hits = 0
        for enemy in enemies:
            if not enemy.alive or enemy.hp <= 0:
                continue
            dx = enemy.x - player.x
            dy = enemy.y - player.y
            dist = math.hypot(dx, dy)
            if dist > self.SLASH_RANGE + enemy.current_radius:
                continue
            ea = math.atan2(dy, dx)
            diff = (ea - angle + math.pi) % (2 * math.pi) - math.pi
            if abs(diff) <= half_arc:
                hit_dmg = damage
                crit = player.equipment.bonus("crit_chance")
                if crit > 0 and random.random() < min(0.45, crit * 0.018):
                    hit_dmg *= 1.75
                enemy.take_damage(hit_dmg)
                self.damage_numbers.append((enemy.x, enemy.y, int(hit_dmg), 1.0))
                self.events.emit("enemy_hit", enemy=enemy, damage=hit_dmg)
                hits += 1
                explosive = player.equipment.legendary_bonus("explosive")
                if explosive > 0 and random.random() < 0.15 * explosive:
                    self.events.emit("legendary_proc", kind="explosive", x=enemy.x, y=enemy.y, damage=hit_dmg * 0.6)
                self._lifesteal(player, hit_dmg)
                if enemy.is_treasure_goblin:
                    self.events.emit("goblin_hit", enemy=enemy, player=player)
                if enemy.hp <= 0:
                    enemy.alive = False
                    self.events.emit("enemy_killed", enemy=enemy, killer=player)
        return hits

    @staticmethod
    def _lifesteal(player: PlayerEntity, damage: float) -> None:
        if player.buffs.has("vampirism_skill"):
            player.stats.hp = min(player.max_hp, player.stats.hp + damage * 0.15)
        ls = player.equipment.legendary_bonus("lifesteal")
        if ls > 0:
            player.stats.hp = min(player.max_hp, player.stats.hp + damage * 0.03 * ls)
        loh = player.equipment.bonus("life_on_hit")
        if loh > 0:
            player.stats.hp = min(player.max_hp, player.stats.hp + loh * 0.15)

    def update(self, dt: float, player: PlayerEntity, enemies: list[EnemyEntity]) -> None:
        player.attack_timer = max(0.0, player.attack_timer - dt)
        alive_slash = []
        for slash in self.slashes:
            slash.progress += dt / slash.duration
            if slash.progress < 1.0:
                alive_slash.append(slash)
        self.slashes = alive_slash

        alive_arrows: list[HomingArrow] = []
        for arr in self.arrows:
            arr.life -= dt
            if arr.life <= 0:
                continue
            target = None
            best = 999.0
            for e in enemies:
                if e.alive and arr.x is not None:
                    d = math.hypot(e.x - arr.x, e.y - arr.y)
                    if d < best:
                        best = d
                        target = e
            if target:
                dx = target.x - arr.x
                dy = target.y - arr.y
                dist = math.hypot(dx, dy) or 1.0
                desired = math.atan2(dy, dx)
                arr.x += math.cos(desired) * arr.speed * dt
                arr.y += math.sin(desired) * arr.speed * dt
                if dist <= arr.radius + target.current_radius:
                    target.take_damage(arr.damage)
                    self.damage_numbers.append((target.x, target.y, int(arr.damage), 1.0))
                    self.events.emit("enemy_hit", enemy=target, damage=arr.damage)
                    self._lifesteal(player, arr.damage)
                    if target.is_treasure_goblin:
                        self.events.emit("goblin_hit", enemy=target, player=player)
                    if target.hp <= 0:
                        target.alive = False
                        self.events.emit("enemy_killed", enemy=target, killer=player)
                    continue
            alive_arrows.append(arr)
        self.arrows = alive_arrows

        alive_dn = []
        for x, y, val, alpha in self.damage_numbers:
            alpha -= dt * 2.5
            y -= dt * 2.0
            if alpha > 0:
                alive_dn.append((x, y, val, alpha))
        self.damage_numbers = alive_dn

    def enemy_attack_player(self, player: PlayerEntity, enemy: EnemyEntity, dt: float) -> None:
        if not enemy.alive or player.is_dashing:
            return
        dist = player.distance_to(enemy)
        if dist > enemy.current_radius + player.radius + 0.15:
            return
        enemy.attack_timer -= dt
        if enemy.attack_timer <= 0:
            enemy.attack_timer = enemy.attack_cooldown
            dmg_mult = 1.5 if enemy.enraged else 1.0
            if enemy.shield_timer > 0:
                dmg_mult *= 0.5
            raw = enemy.damage * dmg_mult
            dmg = player.take_damage(raw)
            if player.buffs.has("ice_armor") or "ice_armor" in player.equipment.passive_skill_affixes():
                apply_slow(enemy, 1.2, 0.55)
            reflect_pct = 0.0
            if player.buffs.has("reflect_skill"):
                reflect_pct = 0.5
            thorns = player.equipment.legendary_bonus("thorns")
            reflect_pct = max(reflect_pct, min(0.35, thorns * 0.25))
            if reflect_pct > 0:
                enemy.take_damage(dmg * reflect_pct)
            if player.pending_thorns_damage > 0:
                enemy.take_damage(player.pending_thorns_damage)
                player.pending_thorns_damage = 0.0
            self.damage_numbers.append((player.x, player.y, int(dmg), 1.0))
            if player.hp <= 0:
                self.events.emit("player_died", killer=enemy)
