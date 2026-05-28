"""Enemy AI with pathfinding, abilities, and tile collision."""

from __future__ import annotations

import json
import math
import random

from core.config import DATA_DIR, ENEMIES_PER_FLOOR, ENEMY_DAMAGE_GLOBAL_MULT, GameMode, SPEED_MODE_MULT
from core.legendary_defs import FLOOR_ELITE_COUNT, FLOOR_ELITE_SPAWN_CHANCE
from entities.enemy import EnemyEntity, EnemyKind
from entities.player import PlayerEntity
from systems.effects import EffectSystem
from systems.enemy_status import effective_enemy_speed
from world.collision import can_occupy, move_slide
from world.map import GameMap
from world.pathfinding import find_path


ENEMY_SPECIAL_ABILITIES = (
    "dash", "poison", "shield", "teleport", "regen", "enrage", "volley", "slow",
)


class AISystem:
    def __init__(self, effects: EffectSystem | None = None) -> None:
        self.rng = random.Random()
        self.effects = effects
        self.difficulty_mult: dict[str, float] = {"enemy_hp": 1.0, "enemy_dmg": 1.0, "enemy_count": 1.0}
        self.game_mode = GameMode.CLASSIC

    def set_difficulty(self, mult: dict[str, float]) -> None:
        self.difficulty_mult = mult

    def set_game_mode(self, mode: GameMode) -> None:
        self.game_mode = mode

    def _speed_mult(self) -> float:
        return SPEED_MODE_MULT if self.game_mode == GameMode.SPEED else 1.0

    def _apply_speed_to_enemy(self, enemy: EnemyEntity) -> None:
        mult = self._speed_mult()
        if mult != 1.0:
            enemy.speed *= mult
            enemy.attack_cooldown = max(0.15, enemy.attack_cooldown / mult)

    def spawn_enemies(self, game_map: GameMap, floor: int, *, horde_mult: float = 1.0) -> list[EnemyEntity]:
        templates = []
        path = DATA_DIR / "enemies.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                templates = json.load(f).get("enemies", [])

        enemies: list[EnemyEntity] = []
        area_level = game_map.area_level
        count = int((ENEMIES_PER_FLOOR + floor // 2) * self.difficulty_mult.get("enemy_count", 1.0) * horde_mult)
        attempts = 0
        max_attempts = max(count * 40, 400)
        while len(enemies) < count and attempts < max_attempts:
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
            tmpl = self._pick_template(templates) if templates else None
            enemies.append(self._make_enemy(wx, wy, area_level, tmpl))

        if floor % 3 == 0:
            boss = self._spawn_boss(game_map, area_level, templates)
            if boss:
                enemies.append(boss)

        for enemy in enemies:
            self._apply_speed_to_enemy(enemy)

        game_map.enemies_spawned = True
        return enemies

    def spawn_floor_elites(self, game_map: GameMap, floor: int, templates: list) -> list[EnemyEntity]:
        """Once per floor: up to 3 special elites with 3x HP, ranged + AOE."""
        if self.rng.random() > FLOOR_ELITE_SPAWN_CHANCE:
            return []
        elites: list[EnemyEntity] = []
        area_level = game_map.area_level
        for _ in range(FLOOR_ELITE_COUNT):
            for _attempt in range(60):
                tx = self.rng.randint(2, len(game_map.grid[0]) - 3)
                ty = self.rng.randint(2, len(game_map.grid) - 3)
                wx, wy = tx + 0.5, ty + 0.5
                if not can_occupy(game_map, wx, wy):
                    continue
                if (tx, ty) in (game_map.start_tile, game_map.exit_tile):
                    continue
                tmpl = self._pick_template(templates) if templates else None
                e = self._make_enemy(wx, wy, area_level, tmpl)
                e.is_floor_elite = True
                e.max_hp *= 3.0
                e.hp = e.max_hp
                e.damage *= 1.35
                e.xp_value = int(e.xp_value * 2.5)
                e.visual_scale = 1.35
                e.special_abilities = ["volley", "elite_aoe"]
                e.ability_cooldowns = {"volley": 2.0, "elite_aoe": 4.0}
                e.enemy_id = "elite_" + e.enemy_id
                elites.append(e)
                break
        for e in elites:
            self._apply_speed_to_enemy(e)
        return elites

    def spawn_arena_wave(
        self,
        game_map: GameMap,
        floor: int,
        templates: list,
        count: int = 5,
        *,
        difficulty_mult: float = 1.0,
        bosses_only: bool = False,
        speed_mult: float = 1.0,
    ) -> list[EnemyEntity]:
        """Spawn enemies at arena map edges."""
        spawned: list[EnemyEntity] = []
        area_level = game_map.area_level
        points = game_map.edge_spawn_points(max(count * 3, 12))
        for i in range(min(count, len(points))):
            wx, wy = points[i]
            if not can_occupy(game_map, wx, wy):
                continue
            tmpl = self._pick_template(templates) if templates else None
            if bosses_only:
                e = self._make_boss(wx, wy, area_level, tmpl)
            else:
                e = self._make_enemy(wx, wy, area_level, tmpl)
            if difficulty_mult != 1.0:
                e.max_hp *= difficulty_mult
                e.hp = e.max_hp
                e.damage *= difficulty_mult
            if speed_mult != 1.0:
                e.speed *= speed_mult
                e.attack_cooldown = max(0.15, e.attack_cooldown / speed_mult)
            spawned.append(e)
        return spawned

    def make_treasure_goblin(self, x: float, y: float, area_level: int) -> EnemyEntity:
        hp_mult = self.difficulty_mult.get("enemy_hp", 1.0)
        scale = 1.0 + (area_level - 1) * 0.12
        hp = 220 * scale * hp_mult
        goblin = EnemyEntity(
            x=x,
            y=y,
            kind=EnemyKind.RUNNER,
            max_hp=hp,
            hp=hp,
            damage=4.0,
            speed=115.0,
            xp_value=int(8 + area_level * 2),
            area_level=area_level,
            enemy_id="treasure_goblin",
            sprite_name="enemy_normal.png",
            visual_scale=0.85,
            is_treasure_goblin=True,
            display_name="Сокровищник",
        )
        return goblin

    def spawn_treasure_goblins(self, game_map: GameMap, floor: int, count: int = 2) -> list[EnemyEntity]:
        spawned: list[EnemyEntity] = []
        for _ in range(count):
            for _attempt in range(50):
                tx = self.rng.randint(3, len(game_map.grid[0]) - 4)
                ty = self.rng.randint(3, len(game_map.grid) - 4)
                wx, wy = tx + 0.5, ty + 0.5
                if not can_occupy(game_map, wx, wy):
                    continue
                if (tx, ty) in (game_map.start_tile, game_map.exit_tile):
                    continue
                spawned.append(self.make_treasure_goblin(wx, wy, game_map.area_level))
                break
        return spawned

    def _pick_template(self, templates: list) -> dict:
        weights = [max(1, t.get("weight", 1)) for t in templates]
        return self.rng.choices(templates, weights=weights, k=1)[0]

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
            tmpl = self._pick_template(templates) if templates else None
            return self._make_boss(wx, wy, area_level, tmpl)
        return None

    def _make_boss(self, x: float, y: float, area_level: int, tmpl: dict | None) -> EnemyEntity:
        demon_tmpl = {"id": "demon", "sprite": "demon.png", "kind": "brute", "base_hp": 90, "base_damage": 16, "base_speed": 70, "xp": 30}
        enemy = self._make_enemy(x, y, area_level, demon_tmpl)
        enemy.is_boss = True
        enemy.sprite_name = "demon.png"
        enemy.visual_scale = 2.0
        enemy.max_hp = enemy.max_hp * 3.5
        enemy.hp = enemy.max_hp
        enemy.speed *= 0.88
        enemy.xp_value = int(enemy.xp_value * 4)
        enemy.ability_cooldown = 3.0
        enemy.special_abilities = self._roll_special_abilities(area_level, is_boss=True) or ["volley", "enrage", "shield"]
        enemy.ability_cooldowns = {a: 2.5 for a in enemy.special_abilities}
        self._apply_speed_to_enemy(enemy)
        return enemy

    def _make_enemy(self, x: float, y: float, area_level: int, tmpl: dict | None) -> EnemyEntity:
        hp_mult = self.difficulty_mult.get("enemy_hp", 1.0)
        dmg_mult = self.difficulty_mult.get("enemy_dmg", 1.0)
        scale = 1.0 + (area_level - 1) * 0.18
        display_name = ""
        if tmpl:
            kind = EnemyKind[tmpl.get("kind", "grunt").upper()]
            eid = tmpl.get("id", "mob")
            display_name = tmpl.get("name", "")
            sprite_name = tmpl.get("sprite", "enemy_normal.png")
            base_hp = tmpl.get("base_hp", 40) * scale * hp_mult
            base_dmg = tmpl.get("base_damage", 8) * scale * dmg_mult * ENEMY_DAMAGE_GLOBAL_MULT
            base_spd = tmpl.get("base_speed", 85) * (1.0 + (area_level - 1) * 0.05)
            xp_scale = 0.88 + area_level * 0.08
            xp = int(tmpl.get("xp", 12) * xp_scale)
        else:
            kind = self.rng.choice(list(EnemyKind))
            eid = "fallen"
            sprite_name = "enemy_normal.png"
            base_hp = 40 * scale * hp_mult
            base_dmg = 8 * scale * dmg_mult * ENEMY_DAMAGE_GLOBAL_MULT
            base_spd = 85
            xp = int(12 * (0.88 + area_level * 0.08))
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

        special = self._roll_special_abilities(area_level, is_boss=False)

        enemy = EnemyEntity(
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
            display_name=display_name,
            sprite_name=sprite_name,
            ability_cooldown=ability_cd,
            ability_timer=ability_cd * 0.5 + self.rng.random() * ability_cd,
            special_abilities=special,
            ability_cooldowns={a: self.rng.uniform(2.0, 5.0) for a in special},
        )
        self._apply_speed_to_enemy(enemy)
        return enemy

    def _roll_special_abilities(self, area_level: int, *, is_boss: bool) -> list[str]:
        pool = list(ENEMY_SPECIAL_ABILITIES)
        count = 1 if area_level < 3 else 2
        if is_boss or area_level >= 6:
            count = min(3, len(pool))
        if self.rng.random() < 0.25:
            return []
        return self.rng.sample(pool, k=min(count, len(pool)))

    def update(
        self,
        enemies: list[EnemyEntity],
        player: PlayerEntity,
        game_map: GameMap,
        dt: float,
        events=None,
        *,
        protect_target=None,
    ) -> None:
        px, py = int(player.x), int(player.y)

        for enemy in enemies:
            if not enemy.alive:
                continue
            enemy.update_anim(dt)
            if enemy.is_treasure_goblin:
                enemy.goblin_loot_cd = max(0.0, enemy.goblin_loot_cd - dt)

            if enemy.casting > 0:
                enemy.casting -= dt
                continue

            if enemy.shield_timer > 0:
                enemy.shield_timer -= dt

            if enemy.hp < enemy.max_hp * 0.35 and "enrage" in enemy.special_abilities:
                enemy.enraged = True

            ex, ey = int(enemy.x), int(enemy.y)
            dist_to_player = enemy.distance_to(player)

            if enemy.is_treasure_goblin:
                dx = enemy.x - player.x
                dy = enemy.y - player.y
                dist = math.hypot(dx, dy) or 1.0
                flee_speed = enemy.speed * 1.35
                step = min(flee_speed * dt * 0.011, 1.2)
                enemy.x, enemy.y = move_slide(
                    game_map, enemy.x, enemy.y, (dx / dist) * step, (dy / dist) * step
                )
                continue

            enemy.ability_timer -= dt
            if enemy.ability_timer <= 0 and dist_to_player < 8.0:
                if self._try_ability(enemy, player, game_map, events):
                    continue
            if enemy.special_abilities:
                if self._try_special_abilities(enemy, player, game_map, dt, events):
                    continue

            chase_x, chase_y = player.x, player.y
            if protect_target and protect_target.alive:
                if enemy.distance_to(protect_target) < dist_to_player * 1.15:
                    chase_x, chase_y = protect_target.x, protect_target.y

            dx = chase_x - enemy.x
            dy = chase_y - enemy.y
            if dist_to_player < 4.0:
                step = min(enemy.speed * dt * 0.011, 1.2)
                dist = math.hypot(dx, dy) or 1.0
                enemy.x, enemy.y = move_slide(
                    game_map, enemy.x, enemy.y, (dx / dist) * step, (dy / dist) * step
                )
                continue

            enemy.path_timer -= dt
            if enemy.path_timer <= 0 or not enemy.path:
                if dist_to_player > 18:
                    enemy.path_timer = 0.75 + self.rng.random() * 0.35
                else:
                    enemy.path = find_path(game_map, (ex, ey), (int(chase_x), int(chase_y)))
                    enemy.path_timer = 0.35 + self.rng.random() * 0.25

            target_x, target_y = chase_x, chase_y
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
                if protect_target and protect_target.alive and enemy.distance_to(protect_target) < 1.0:
                    protect_target.take_damage(enemy.damage * 0.8)
                continue

            step = min(effective_enemy_speed(enemy) * dt * 0.011, dist)
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
            dmg = enemy.damage * (1.5 if enemy.enraged else 1.0) * 1.8
            if self.effects:
                self.effects.spawn_aoe_ring(enemy.x, enemy.y, 55.0, (180, 80, 255))
            if dist < 2.8:
                player.stats.hp -= max(1, dmg - player.armor * 0.3)
                player.hit_flash = 0.15
            return True

        if enemy.kind == EnemyKind.BRUTE and dist < 2.2:
            enemy.ability_timer = enemy.ability_cooldown
            enemy.casting = 0.35
            slam_dmg = enemy.damage * (1.5 if enemy.enraged else 1.0) * 2.2
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

    def _try_special_abilities(
        self,
        enemy: EnemyEntity,
        player: PlayerEntity,
        game_map: GameMap,
        dt: float,
        events,
    ) -> bool:
        dist = enemy.distance_to(player)
        for ability in enemy.special_abilities:
            cd = enemy.ability_cooldowns.get(ability, 4.0)
            cd -= dt
            enemy.ability_cooldowns[ability] = cd
            if cd > 0:
                continue

            if ability == "dash" and 2.5 < dist < 7.0:
                enemy.ability_cooldowns[ability] = 4.0
                enemy.casting = 0.2
                dx = player.x - enemy.x
                dy = player.y - enemy.y
                d = math.hypot(dx, dy) or 1.0
                step = min(1.2, dist * 0.4)
                enemy.x, enemy.y = move_slide(game_map, enemy.x, enemy.y, (dx / d) * step, (dy / d) * step)
                if self.effects:
                    self.effects.spawn_aoe_ring(enemy.x, enemy.y, 35.0, (255, 200, 80))
                return True

            if ability == "teleport" and dist > 4.0 and dist < 10.0:
                enemy.ability_cooldowns[ability] = 6.0
                enemy.casting = 0.35
                tx = player.x + self.rng.uniform(-1.5, 1.5)
                ty = player.y + self.rng.uniform(-1.5, 1.5)
                if can_occupy(game_map, tx, ty):
                    enemy.x, enemy.y = tx, ty
                if self.effects:
                    self.effects.spawn_aoe_ring(enemy.x, enemy.y, 45.0, (140, 80, 255))
                return True

            if ability == "shield" and enemy.shield_timer <= 0 and dist < 5.0:
                enemy.ability_cooldowns[ability] = 8.0
                enemy.shield_timer = 3.0
                enemy.casting = 0.3
                if self.effects:
                    self.effects.spawn_aoe_ring(enemy.x, enemy.y, 50.0, (100, 180, 255))
                return True

            if ability == "volley" and dist < 7.0:
                enemy.ability_cooldowns[ability] = 5.0
                enemy.casting = 0.4
                if self.effects:
                    self.effects.spawn_aoe_ring(enemy.x, enemy.y, 55.0, (180, 80, 255))
                if dist < 3.5:
                    mult = 0.5 if enemy.shield_timer > 0 else 1.0
                    player.stats.hp -= max(1, enemy.damage * 1.4 * mult - player.armor * 0.25)
                    player.hit_flash = 0.15
                return True

            if ability == "poison" and dist < 2.5:
                enemy.ability_cooldowns[ability] = 5.5
                mult = 0.5 if enemy.shield_timer > 0 else 1.0
                player.stats.hp -= max(1, enemy.damage * 0.8 * mult - player.armor * 0.2)
                player.hit_flash = 0.12
                return True

            if ability == "slow" and dist < 4.0:
                enemy.ability_cooldowns[ability] = 7.0
                enemy.casting = 0.25
                if self.effects:
                    self.effects.spawn_aoe_ring(enemy.x, enemy.y, 40.0, (80, 120, 200))
                return True

            if ability == "elite_aoe" and dist < 5.5:
                enemy.ability_cooldowns[ability] = 5.0
                enemy.casting = 0.45
                if self.effects:
                    self.effects.spawn_aoe_ring(enemy.x, enemy.y, 85.0, (255, 80, 40))
                if dist < 3.2:
                    mult = 0.5 if enemy.shield_timer > 0 else 1.0
                    player.stats.hp -= max(1, enemy.damage * 2.0 * mult - player.armor * 0.2)
                    player.hit_flash = 0.2
                return True

            if ability == "regen" and enemy.hp < enemy.max_hp * 0.6:
                enemy.ability_cooldowns[ability] = 6.0
                heal = enemy.max_hp * 0.08
                enemy.hp = min(enemy.max_hp, enemy.hp + heal)
                if self.effects:
                    self.effects.spawn_aoe_ring(enemy.x, enemy.y, 35.0, (80, 255, 120))
                return True

        return False
