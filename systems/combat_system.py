"""Combat system — wide semicircle melee slash."""

from __future__ import annotations

import math
from dataclasses import dataclass

from core.config import ATTACK_ARC, ATTACK_DAMAGE_BASE
from core.event_bus import EventBus
from entities.enemy import EnemyEntity
from entities.player import PlayerEntity


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


class CombatSystem:
    SLASH_RANGE = 1.95

    def __init__(self, events: EventBus) -> None:
        self.events = events
        self.slashes: list[SlashEffect] = []
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

        player.attack_timer = player.attack_cooldown
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
                enemy.take_damage(damage)
                self.damage_numbers.append((enemy.x, enemy.y, int(damage), 1.0))
                self.events.emit("enemy_hit", enemy=enemy, damage=damage)
                hits += 1
                if enemy.hp <= 0:
                    enemy.alive = False
                    self.events.emit("enemy_killed", enemy=enemy, killer=player)
        return hits

    def update(self, dt: float, player: PlayerEntity, enemies: list[EnemyEntity]) -> None:
        player.attack_timer = max(0.0, player.attack_timer - dt)
        alive_slash = []
        for slash in self.slashes:
            slash.progress += dt / slash.duration
            if slash.progress < 1.0:
                alive_slash.append(slash)
        self.slashes = alive_slash

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
            dmg = player.take_damage(enemy.damage)
            self.damage_numbers.append((player.x, player.y, int(dmg), 1.0))
            if player.hp <= 0:
                self.events.emit("player_died")
