"""Legendary skill override implementations."""

from __future__ import annotations

import math
import random

from entities.enemy import EnemyEntity
from entities.player import PlayerEntity
from systems.enemy_status import (
    apply_bleed,
    apply_burn,
    apply_curse,
    apply_damage_with_curse,
    apply_poison,
    apply_slow,
)


class LegendarySkillCaster:
    """Mixin-style helper; expects host with skill_damage, effects, events, rng, _damage_enemy."""

    def cast_override(
        self,
        override_id: str,
        player: PlayerEntity,
        enemies: list[EnemyEntity],
        mouse_world: tuple[float, float],
    ) -> bool:
        fn = {
            "power_strike": self._power_strike,
            "knife_fan": self._knife_fan,
            "meteor": self._meteor,
            "ice_wave": self._ice_wave,
            "chain_lightning": self._chain_lightning,
            "poison": self._poison_skill,
            "burning": self._burning_skill,
            "bleeding": self._bleeding_skill,
            "curse": self._curse_skill,
            "battle_cry": self._battle_cry,
            "mana_shield": self._mana_shield_pulse,
            "ice_armor": self._ice_armor_pulse,
            "vampirism": self._vampirism_pulse,
            "reflect": self._reflect_pulse,
        }.get(override_id)
        if not fn:
            return False
        return fn(player, enemies, mouse_world)

    def _power_strike(self, player, enemies, mouse_world) -> bool:
        dmg = self.skill_damage(player, 55.0)
        radius = 4.5
        self.effects.spawn_aoe_ring(player.x, player.y, 160.0, (255, 200, 80))
        hits = 0
        for e in enemies:
            if e.alive and player.distance_to(e) <= radius + e.current_radius:
                apply_damage_with_curse(e, dmg)
                self.events.emit("enemy_hit", enemy=e, damage=dmg)
                if e.hp <= 0:
                    e.alive = False
                    self.events.emit("enemy_killed", enemy=e, killer=player)
                hits += 1
        self.events.emit("skill_cast", skill="power_strike", hits=hits)
        return True

    def _knife_fan(self, player, enemies, mouse_world) -> bool:
        dx = mouse_world[0] - player.x
        dy = mouse_world[1] - player.y
        base_angle = math.atan2(dy, dx) if math.hypot(dx, dy) > 0.05 else player.facing_angle
        dmg = self.skill_damage(player, 18.0)
        for i in range(7):
            spread = (i - 3) * 0.18
            angle = base_angle + spread
            self.projectiles.append(
                self._make_proj(player, angle, dmg, kind="knife", radius=0.15)
            )
        return True

    def _meteor(self, player, enemies, mouse_world) -> bool:
        tx, ty = mouse_world[0], mouse_world[1]
        dmg = self.skill_damage(player, 24.0)
        for i in range(6):
            ox = tx + self.rng.uniform(-1.5, 1.5)
            oy = ty + self.rng.uniform(-1.5, 1.5)
            self.effects.spawn_aoe_ring(ox, oy, 55.0, (255, 120, 40))
            for e in enemies:
                if e.alive and math.hypot(e.x - ox, e.y - oy) <= 1.4 + e.current_radius:
                    apply_damage_with_curse(e, dmg)
                    self.events.emit("enemy_hit", enemy=e, damage=dmg)
                    if e.hp <= 0:
                        e.alive = False
                        self.events.emit("enemy_killed", enemy=e, killer=player)
        return True

    def _ice_wave(self, player, enemies, mouse_world) -> bool:
        self.ice_waves.append({"x": player.x, "y": player.y, "r": 0.4, "max_r": 4.0, "dmg": self.skill_damage(player, 20.0), "hit": set()})
        self.effects.spawn_aoe_ring(player.x, player.y, 70.0, (100, 200, 255))
        return True

    def _chain_lightning(self, player, enemies, mouse_world) -> bool:
        alive = [e for e in enemies if e.alive]
        if not alive:
            return True
        start = min(alive, key=lambda e: player.distance_to(e))
        chain = [start]
        remaining = [e for e in alive if e is not start]
        while remaining and len(chain) < 5:
            last = chain[-1]
            nxt = min(remaining, key=lambda e: last.distance_to(e))
            if last.distance_to(nxt) > 3.5:
                break
            chain.append(nxt)
            remaining.remove(nxt)
        dmg = self.skill_damage(player, 26.0)
        for i, e in enumerate(chain):
            d = dmg * (0.85 ** i)
            apply_damage_with_curse(e, d)
            self.effects.spawn_aoe_ring(e.x, e.y, 45.0, (180, 220, 255))
            self.events.emit("enemy_hit", enemy=e, damage=d)
            if e.hp <= 0:
                e.alive = False
                self.events.emit("enemy_killed", enemy=e, killer=player)
        return True

    def _poison_skill(self, player, enemies, mouse_world) -> bool:
        radius = 2.8
        dps = self.skill_damage(player, 8.0) * 0.35
        self.effects.spawn_aoe_ring(player.x, player.y, 80.0, (80, 220, 80))
        for e in enemies:
            if e.alive and player.distance_to(e) <= radius:
                apply_poison(e, dps, 6.0)
        return True

    def _burning_skill(self, player, enemies, mouse_world) -> bool:
        radius = 2.5
        dps = self.skill_damage(player, 10.0) * 0.4
        self.effects.spawn_aoe_ring(player.x, player.y, 75.0, (255, 140, 40))
        for e in enemies:
            if e.alive and player.distance_to(e) <= radius:
                apply_burn(e, dps, 5.0)
        return True

    def _bleeding_skill(self, player, enemies, mouse_world) -> bool:
        radius = 2.2
        dps = self.skill_damage(player, 9.0) * 0.35
        for e in enemies:
            if e.alive and player.distance_to(e) <= radius:
                apply_bleed(e, dps, 5.0)
        return True

    def _curse_skill(self, player, enemies, mouse_world) -> bool:
        radius = 3.2
        self.effects.spawn_aoe_ring(player.x, player.y, 90.0, (160, 60, 200))
        for e in enemies:
            if e.alive and player.distance_to(e) <= radius:
                apply_curse(e, 8.0)
        return True

    def _battle_cry(self, player, enemies, mouse_world) -> bool:
        player.buffs.add("damage", 10.0, magnitude=1.0)
        player.buffs.add("speed", 10.0, magnitude=1.0)
        player.buffs.add("battle_cry", 10.0, magnitude=1.0)
        self.effects.spawn_aoe_ring(player.x, player.y, 65.0, (255, 200, 60))
        return True

    def _mana_shield_pulse(self, player, enemies, mouse_world) -> bool:
        player.buffs.add("mana_shield", 12.0, magnitude=1.0)
        self.effects.spawn_aoe_ring(player.x, player.y, 55.0, (110, 180, 255))
        return True

    def _ice_armor_pulse(self, player, enemies, mouse_world) -> bool:
        player.buffs.add("ice_armor", 12.0, magnitude=1.0)
        self.effects.spawn_aoe_ring(player.x, player.y, 55.0, (100, 200, 255))
        return True

    def _vampirism_pulse(self, player, enemies, mouse_world) -> bool:
        player.buffs.add("vampirism_skill", 8.0, magnitude=1.0)
        self.effects.spawn_aoe_ring(player.x, player.y, 55.0, (200, 60, 80))
        return True

    def _reflect_pulse(self, player, enemies, mouse_world) -> bool:
        player.buffs.add("reflect_skill", 8.0, magnitude=1.0)
        self.effects.spawn_aoe_ring(player.x, player.y, 55.0, (200, 200, 255))
        return True

    def _make_proj(self, player, angle, dmg, kind="knife", radius=0.15):
        from systems.skill_system import SkillProjectile
        speed = 10.0
        return SkillProjectile(
            player.x, player.y,
            math.cos(angle) * speed, math.sin(angle) * speed,
            dmg, radius=radius, kind=kind,
        )

    def update_ice_waves(self, dt: float, player, enemies) -> None:
        alive = []
        for wave in self.ice_waves:
            wave["r"] += dt * 3.5
            r = wave["r"]
            if r > wave["max_r"]:
                continue
            self.effects.spawn_aoe_ring(wave["x"], wave["y"], int(r * 28), (120, 200, 255))
            for e in enemies:
                if not e.alive or id(e) in wave["hit"]:
                    continue
                if math.hypot(e.x - wave["x"], e.y - wave["y"]) <= r + e.current_radius:
                    if math.hypot(e.x - wave["x"], e.y - wave["y"]) >= r - 0.5:
                        apply_damage_with_curse(e, wave["dmg"] * dt * 3)
                        wave["hit"].add(id(e))
            alive.append(wave)
        self.ice_waves = alive

    def apply_whirlwind_element(self, player, enemy, dmg: float) -> None:
        elem = player.equipment.whirlwind_element()
        if elem == "fire":
            apply_burn(enemy, dmg * 0.15, 3.0)
        elif elem == "ice":
            apply_slow(enemy, 1.5, 0.45)
        elif elem == "poison":
            apply_poison(enemy, dmg * 0.12, 4.0)
