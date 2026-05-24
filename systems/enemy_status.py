"""Enemy debuffs and DoT processing."""

from __future__ import annotations

from entities.enemy import EnemyEntity
from entities.player import PlayerEntity


def apply_damage_with_curse(enemy: EnemyEntity, amount: float) -> float:
    mult = 1.0 + enemy.curse_stacks * 0.12
    enemy.take_damage(amount * mult)
    return amount * mult


def apply_poison(enemy: EnemyEntity, dps: float, duration: float) -> None:
    enemy.poison_rem = max(enemy.poison_rem, duration)
    enemy.poison_dps = max(enemy.poison_dps, dps)


def apply_burn(enemy: EnemyEntity, dps: float, duration: float) -> None:
    enemy.burn_rem = max(enemy.burn_rem, duration)
    enemy.burn_dps = max(enemy.burn_dps, dps)


def apply_bleed(enemy: EnemyEntity, dps: float, duration: float) -> None:
    enemy.bleed_rem = max(enemy.bleed_rem, duration)
    enemy.bleed_dps = max(enemy.bleed_dps, dps)
    enemy.slow_rem = max(enemy.slow_rem, duration * 0.6)


def apply_curse(enemy: EnemyEntity, duration: float = 8.0) -> None:
    enemy.curse_rem = max(enemy.curse_rem, duration)
    enemy.curse_stacks = min(3, enemy.curse_stacks + 1)


def apply_slow(enemy: EnemyEntity, duration: float, strength: float = 0.5) -> None:
    enemy.slow_rem = max(enemy.slow_rem, duration)
    enemy.slow_strength = max(enemy.slow_strength, strength)


def update_enemy_status(
    enemy: EnemyEntity,
    dt: float,
    events,
    player: PlayerEntity | None = None,
    nearby: list[EnemyEntity] | None = None,
) -> None:
    if not enemy.alive:
        return

    tick_dmg = 0.0
    if enemy.poison_rem > 0:
        enemy.poison_rem -= dt
        tick_dmg += enemy.poison_dps * dt
    if enemy.burn_rem > 0:
        enemy.burn_rem -= dt
        tick_dmg += enemy.burn_dps * dt
    if enemy.bleed_rem > 0:
        enemy.bleed_rem -= dt
        tick_dmg += enemy.bleed_dps * dt
    if enemy.curse_rem > 0:
        enemy.curse_rem -= dt
        if enemy.curse_rem <= 0:
            enemy.curse_stacks = 0
    if enemy.slow_rem > 0:
        enemy.slow_rem -= dt

    if tick_dmg > 0:
        was_alive = enemy.alive and enemy.hp > 0
        enemy.hp -= tick_dmg
        if enemy.hp <= 0 and was_alive:
            enemy.alive = False
            if player and events:
                _try_burn_spread(enemy, nearby or [], player, events)
                events.emit("enemy_killed", enemy=enemy, killer=player)


def _try_burn_spread(
    dead: EnemyEntity,
    enemies: list[EnemyEntity],
    player: PlayerEntity,
    events,
) -> None:
    if dead.burn_rem <= 0 and dead.burn_dps <= 0:
        return
    for other in enemies:
        if not other.alive or other is dead:
            continue
        if dead.distance_to(other) <= 1.8:
            apply_burn(other, dead.burn_dps * 0.6, 4.0)


def effective_enemy_speed(enemy: EnemyEntity) -> float:
    if enemy.slow_rem > 0:
        return enemy.speed * (1.0 - enemy.slow_strength)
    return enemy.speed
