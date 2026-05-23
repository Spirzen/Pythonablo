"""Enemy AI with pathfinding, abilities, and tile collision."""

from __future__ import annotations

import json
import math
import random

from core.config import DATA_DIR, ENEMIES_PER_FLOOR
from entities.enemy import EnemyEntity, EnemyKind
from entities.player import PlayerEntity
from systems.effects import EffectSystem
from world.collision import can_occupy, move_slide
from world.map import GameMap
from world.pathfinding import find_path


class AISystem:
    def __init__(self, effects: EffectSystem | None = None) -> None:
        self.rng = random.Random()
        self.effects = effects
        self.difficulty_mult: dict[str, float] = {"enemy_hp": 1.0, "enemy_dmg": 1.0, "enemy_count": 1.0}

    def set_difficulty(self, mult: dict[str, float]) -> None:
        self.difficulty_mult = mult

    def spawn_enemies(self, game_map: GameMap, floor: int) -> list[EnemyEntity]:
        templates = []
        path = DATA_DIR / "enemies.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                templates = json.load(f).get("enemies", [])

        enemies: list[EnemyEntity] = []
        area_level = game_map.area_level
        count = int((ENEMIES_PER_FLOOR + floor // 2) * self.difficulty_mult.get("enemy_count", 1.0))
        attempts = 0
        while len(enemies) < count and attempts < count * 30:
            attempts += 1
            tx = self.rng.randint(2, len(game_map.grid[0]) - 3)
            ty = self.rng.randint(2, len(game_map.grid) - 3)
            wx, wy = tx + 0.5, ty + 0.5
            if not can_occupy(game_map, wx, wy):
                continue
            if (tx, ty) in (game_map.start_tile, game_map.exit_tile):
                continue
            if game_map.stairs_up_tile and (tx, ty) == game_map.stairs_up_tile:
                continue
            tmpl = self.rng.choice(templates) if templates else None
            enemies.append(self._make_enemy(wx, wy, area_level, tmpl))

        if floor % 3 == 0:
            boss = self._spawn_boss(game_map, area_level, templates)
            if boss:
                enemies.append(boss)

        game_map.enemies_spawned = True
        return enemies

    def _spawn_boss(self, game_map: GameMap, area_level: int, templates: list) -> EnemyEntity | None:
        ex, ey = game_map.exit_tile
        for _ in range(50):
            tx = self.rng.randint(max(2, ex - 8), min(len(game_map.grid[0]) - 3, ex + 8))
            ty = self.rng.randint(max(2, ey - 8), min(len(game_map.grid) - 3, ey + 8))
            wx, wy = tx + 0.5, ty + 0.5
            if not can_occupy(game_map, wx, wy):
                continue
            if (tx, ty) in (game_map.start_tile, game_map.exit_tile):
                continue
            tmpl = self.rng.choice(templates) if templates else None
            return self._make_boss(wx, wy, area_level, tmpl)
        return None

    def _make_boss(self, x: float, y: float, area_level: int, tmpl: dict | None) -> EnemyEntity:
        enemy = self._make_enemy(x, y, area_level, tmpl)
        enemy.is_boss = True
        enemy.visual_scale = 2.0
        enemy.max_hp = enemy.max_hp * 3.5
        enemy.hp = enemy.max_hp
        enemy.speed *= 0.88
        enemy.xp_value = int(enemy.xp_value * 4)
        enemy.ability_cooldown = 3.0
        return enemy

    def _make_enemy(self, x: float, y: float, area_level: int, tmpl: dict | None) -> EnemyEntity:
        hp_mult = self.difficulty_mult.get("enemy_hp", 1.0)
        dmg_mult = self.difficulty_mult.get("enemy_dmg", 1.0)
        scale = 1.0 + (area_level - 1) * 0.18
        if tmpl:
            kind = EnemyKind[tmpl.get("kind", "grunt").upper()]
            eid = tmpl.get("id", "mob")
            base_hp = tmpl.get("base_hp", 40) * scale * hp_mult
            base_dmg = tmpl.get("base_damage", 8) * scale * dmg_mult
            base_spd = tmpl.get("base_speed", 85) * (1.0 + (area_level - 1) * 0.05)
            xp = int(tmpl.get("xp", 12) * (1 + area_level * 0.1))
        else:
            kind = self.rng.choice(list(EnemyKind))
            eid = "fallen"
            base_hp = 40 * scale * hp_mult
            base_dmg = 8 * scale * dmg_mult
            base_spd = 85
            xp = int(12 * (1 + area_level * 0.1))
            if kind == EnemyKind.RUNNER:
                base_spd *= 1.4
                base_hp *= 0.7
            elif kind == EnemyKind.BRUTE:
                base_hp *= 1.8
                base_dmg *= 1.3
                base_spd *= 0.75

        ability_cd = 5.0
        if kind == EnemyKind.CASTER:
            ability_cd = 3.5
        elif kind == EnemyKind.BRUTE:
            ability_cd = 4.5

        return EnemyEntity(
            x=x,
            y=y,
            kind=kind,
            max_hp=base_hp,
            hp=base_hp,
            damage=base_dmg,
            speed=base_spd,
            xp_value=xp,
            area_level=area_level,
            enemy_id=eid,
            ability_cooldown=ability_cd,
            ability_timer=ability_cd * 0.5 + self.rng.random() * ability_cd,
        )

    def update(
        self,
        enemies: list[EnemyEntity],
        player: PlayerEntity,
        game_map: GameMap,
        dt: float,
        events=None,
    ) -> None:
        px, py = int(player.x), int(player.y)

        for enemy in enemies:
            if not enemy.alive:
                continue
            enemy.update_anim(dt)

            if enemy.casting > 0:
                enemy.casting -= dt
                continue

            ex, ey = int(enemy.x), int(enemy.y)
            dist_to_player = enemy.distance_to(player)

            enemy.ability_timer -= dt
            if enemy.ability_timer <= 0 and dist_to_player < 8.0:
                if self._try_ability(enemy, player, game_map, events):
                    continue

            enemy.path_timer -= dt
            if enemy.path_timer <= 0 or not enemy.path:
                enemy.path = find_path(game_map, (ex, ey), (px, py))
                enemy.path_timer = 0.35 + self.rng.random() * 0.25

            target_x, target_y = player.x, player.y
            if len(enemy.path) >= 2:
                nx, ny = enemy.path[1]
                if game_map.is_walkable(nx, ny):
                    target_x, target_y = nx + 0.5, ny + 0.5
                else:
                    enemy.path = []

            dx = target_x - enemy.x
            dy = target_y - enemy.y
            dist = math.hypot(dx, dy)
            if dist < 0.04:
                continue

            step = min(enemy.speed * dt * 0.011, dist)
            mx = (dx / dist) * step
            my = (dy / dist) * step
            enemy.x, enemy.y = move_slide(game_map, enemy.x, enemy.y, mx, my)

    def _try_ability(
        self,
        enemy: EnemyEntity,
        player: PlayerEntity,
        game_map: GameMap,
        events,
    ) -> bool:
        dist = enemy.distance_to(player)
        if enemy.kind == EnemyKind.CASTER and dist < 6.5:
            enemy.ability_timer = enemy.ability_cooldown
            enemy.casting = 0.45
            dmg = enemy.damage * 1.8
            if self.effects:
                self.effects.spawn_aoe_ring(enemy.x, enemy.y, 55.0, (180, 80, 255))
            if dist < 2.8:
                player.stats.hp -= max(1, dmg - player.armor * 0.3)
                player.hit_flash = 0.15
            return True

        if enemy.kind == EnemyKind.BRUTE and dist < 2.2:
            enemy.ability_timer = enemy.ability_cooldown
            enemy.casting = 0.35
            slam_dmg = enemy.damage * 2.2
            if self.effects:
                self.effects.spawn_aoe_ring(enemy.x, enemy.y, 65.0, (255, 80, 40))
            if dist < 1.6:
                player.stats.hp -= max(1, slam_dmg - player.armor * 0.25)
                player.hit_flash = 0.2
            return True

        if enemy.is_boss and dist < 5.0:
            enemy.ability_timer = enemy.ability_cooldown
            enemy.casting = 0.5
            if self.effects:
                self.effects.spawn_aoe_ring(enemy.x, enemy.y, 80.0, (255, 50, 30))
            for _ in range(3):
                ox = enemy.x + self.rng.uniform(-0.8, 0.8)
                oy = enemy.y + self.rng.uniform(-0.8, 0.8)
                if can_occupy(game_map, ox, oy):
                    if self.effects:
                        self.effects.spawn_aoe_ring(ox, oy, 45.0, (255, 100, 50))
            if dist < 3.0:
                player.stats.hp -= max(1, enemy.damage * 1.5 - player.armor * 0.2)
                player.hit_flash = 0.25
            return True

        if enemy.kind == EnemyKind.CASTER:
            enemy.ability_timer = enemy.ability_cooldown * 0.5
        return False
