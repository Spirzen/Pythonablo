"""Main game loop and state machine."""

from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path
from typing import Optional

import pygame

from core.config import (
    ASSETS_DIR,
    DIFFICULTY_MULT,
    Difficulty,
    FPS,
    GameState,
    MAP_HEIGHT,
    MAP_WIDTH,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    TITLE,
    TileType,
)
from core.event_bus import EventBus
from engine.audio import AudioSystem
from engine.camera import Camera
from engine.input_handler import InputHandler
from engine.renderer import Renderer, screen_to_world
from entities.enemy import EnemyEntity
from entities.item import GroundItem
from entities.player import PlayerEntity
from player.equipment import Equipment
from player.experience import Experience
from player.inventory import Inventory
from player.stats import Stats
from save.save_manager import SaveData, SaveManager
from systems.ai_system import AISystem
from systems.combat_system import CombatSystem
from systems.effects import EffectSystem
from systems.loot_system import LootSystem
from systems.movement_system import MovementSystem
from systems.skill_system import SkillSystem
from ui.hud import HUD
from ui.inventory_ui import InventoryUI
from ui.menu import GameOverUI, MenuUI
from world.map import GameMap


class Game:
    def __init__(self) -> None:
        pygame.init()
        self._ensure_assets()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True

        self.events = EventBus()
        self.renderer = Renderer(self.screen)
        self.camera = Camera()
        self.input = InputHandler()
        self.audio = AudioSystem()
        self.save_manager = SaveManager()

        self.movement = MovementSystem()
        self.combat = CombatSystem(self.events)
        self.effects = EffectSystem()
        self.skills = SkillSystem(self.events, self.effects)
        self.ai = AISystem(self.effects)
        self.loot = LootSystem(self.events)

        self.menu_ui = MenuUI(self.renderer)
        self.hud = HUD(self.renderer)
        self.inventory_ui = InventoryUI(self.renderer)
        self.inventory_ui.set_loot_system(self.loot)
        self.game_over_ui = GameOverUI(self.renderer)

        self.state = GameState.MENU
        self.difficulty = Difficulty.NORMAL
        self.portal_hint: str | None = None
        self.player: PlayerEntity | None = None
        self.game_map: GameMap | None = None
        self.enemies: list[EnemyEntity] = []
        self.ground_items: list[GroundItem] = []
        self.floor = 1
        self.kills = 0
        self.floor_cache: dict[int, GameMap] = {}
        self.came_from_above = False
        self.anim_time = 0.0

        self.player_sprite: Optional[pygame.Surface] = None
        self.enemy_sprite: Optional[pygame.Surface] = None
        self.enemy_tank_sprite: Optional[pygame.Surface] = None
        self.bg_sprite: Optional[pygame.Surface] = None
        self._load_sprites()

        self.events.subscribe("enemy_killed", self._on_enemy_killed)
        self.events.subscribe("item_dropped", self._on_item_dropped)
        self.events.subscribe("player_died", self._on_player_died)
        self.events.subscribe("enemy_hit", self._on_enemy_hit)
        self.events.subscribe("attack_swung", self._on_attack_swung)

    def _ensure_assets(self) -> None:
        ASSETS_DIR.mkdir(exist_ok=True)
        survivors = Path(r"F:\Projects\Python\Python Survivors")
        for src in (survivors / "assets", survivors / "Java Survivors" / "assets"):
            if src.is_dir():
                for f in src.iterdir():
                    if f.is_file():
                        dst = ASSETS_DIR / f.name
                        if not dst.exists():
                            shutil.copy2(f, dst)

    def _load_sprites(self) -> None:
        def load(name: str) -> Optional[pygame.Surface]:
            path = ASSETS_DIR / name
            if path.exists():
                try:
                    return pygame.image.load(str(path)).convert_alpha()
                except pygame.error:
                    return None
            return None

        self.player_sprite = load("player.png")
        self.enemy_sprite = load("enemy_normal.png")
        self.enemy_tank_sprite = load("enemy_tank.png")
        bg = ASSETS_DIR / "background.jpg"
        if bg.exists():
            try:
                self.bg_sprite = pygame.image.load(str(bg)).convert()
            except pygame.error:
                pass

    def run(self) -> None:
        while self.running:
            dt = min(self.clock.tick(FPS) / 1000.0, 0.05)
            self._handle_events()
            self._update(dt)
            self._draw()
            pygame.display.flip()
        pygame.quit()
        sys.exit()

    def _handle_events(self) -> None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.input.on_key_down(event.key)
                self._on_key_down(event.key)
            elif event.type == pygame.KEYUP:
                self.input.on_key_up(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.input.on_mouse_down(event.button, event.pos)
                if self.state == GameState.MENU and event.button == 1:
                    self.menu_ui.handle_difficulty_click(event.pos)
                    action = self.menu_ui.handle_click(event.pos, self.save_manager.exists())
                    if action == "new":
                        self._start_new_game()
                    elif action == "continue":
                        self._load_game()
                    elif action == "quit":
                        self.running = False
                elif self.state == GameState.PLAYING:
                    if event.button == 1:
                        if self.hud.inventory_clicked(event.pos):
                            self.state = GameState.INVENTORY
                        else:
                            mw = screen_to_world(*event.pos, self.camera.x, self.camera.y)
                            self.combat.try_attack(self.player, self.enemies, mw, event.pos, self.camera)
                if self.state == GameState.INVENTORY:
                    self.inventory_ui.handle_click(
                        event.pos, self.player, button=event.button
                    )
            elif event.type == pygame.MOUSEBUTTONUP:
                self.input.on_mouse_up(event.button)
            elif event.type == pygame.MOUSEMOTION:
                self.input.on_mouse_move(event.pos)

    def _on_key_down(self, key: int) -> None:
        import pygame

        inp = self.input.state
        if self.state == GameState.MENU:
            action = self.menu_ui.handle_input(
                inp.menu_up, inp.menu_down, inp.menu_confirm, self.save_manager.exists(),
                left=inp.menu_left, right=inp.menu_right,
            )
            if action == "new":
                self._start_new_game()
            elif action == "continue":
                self._load_game()
            elif action == "quit":
                self.running = False
            elif inp.menu_back:
                self.running = False
            return

        if self.state == GameState.GAME_OVER and inp.menu_confirm:
            self.state = GameState.MENU
            return

        if self.state == GameState.PLAYING:
            if inp.dash_pressed:
                self.movement.try_dash(self.player, self.game_map, inp)
            if inp.inventory_pressed:
                self.state = GameState.INVENTORY
            if inp.interact_pressed:
                self.loot.pickup(self.player, self.ground_items)
                self._try_portal_transition()
            if inp.skill_pressed:
                mw = screen_to_world(*inp.mouse_pos, self.camera.x, self.camera.y)
                self.skills.try_skill(inp.skill_pressed, self.player, self.enemies, self.game_map, mw)

        if self.state == GameState.INVENTORY:
            if inp.menu_back or inp.inventory_pressed:
                self.state = GameState.PLAYING
            return

    def _start_new_game(self) -> None:
        self.save_manager.delete()
        self.floor = 1
        self.kills = 0
        self.difficulty = self.menu_ui.difficulty
        self.floor_cache.clear()
        self.player = PlayerEntity(x=0, y=0, stats=Stats(), inventory=Inventory(), equipment=Equipment(), experience=Experience())
        self._apply_difficulty_to_player()
        self.ai.set_difficulty(DIFFICULTY_MULT[self.difficulty])
        self._load_floor(1, spawn_at_start=True)
        self.state = GameState.PLAYING

    def _apply_difficulty_to_player(self) -> None:
        mult = DIFFICULTY_MULT[self.difficulty]
        self.player.stats.max_hp = int(self.player.stats.max_hp * mult["player_hp"])
        self.player.stats.hp = self.player.stats.max_hp
        self.player.stats.damage = int(self.player.stats.damage * mult["player_dmg"])

    def _load_game(self) -> None:
        data = self.save_manager.load()
        if not data:
            self._start_new_game()
            return
        self.floor = data.floor
        self.kills = data.kills
        self.player = PlayerEntity(x=0, y=0)
        pd = data.player_data
        if pd:
            s = pd.get("stats", {})
            self.player.stats = Stats(
                max_hp=s.get("max_hp", 150),
                hp=s.get("hp", 150),
                max_mana=s.get("max_mana", 80),
                mana=s.get("mana", 80),
                damage=s.get("damage", 18),
                armor=s.get("armor", 5),
                regen=s.get("regen", 1.5),
            )
            self.player.inventory = Inventory.from_dict(pd.get("inventory", {}))
            self.player.equipment = Equipment.from_dict(pd.get("equipment", {}))
            exp = pd.get("experience", {})
            self.player.experience = Experience(
                level=exp.get("level", 1),
                xp=exp.get("xp", 0),
                xp_to_next=exp.get("xp_to_next", 12),
            )
        self.floor_cache.clear()
        self.difficulty = Difficulty.NORMAL
        self.ai.set_difficulty(DIFFICULTY_MULT[self.difficulty])
        self._load_floor(self.floor, spawn_at_start=True)
        self.state = GameState.PLAYING

    def _load_floor(self, floor: int, *, spawn_at_start: bool = True, from_above: bool = False) -> None:
        self.floor = floor
        self.came_from_above = from_above
        if floor in self.floor_cache:
            self.game_map = self.floor_cache[floor]
            if from_above:
                self.game_map.respawn_enemies_flag()
        else:
            self.game_map = GameMap(floor=floor, seed=floor * 7919)
            self.floor_cache[floor] = self.game_map

        sx, sy = self.game_map.spawn_x + 0.5, self.game_map.spawn_y + 0.5
        if from_above and self.game_map.stairs_up_tile:
            ux, uy = self.game_map.stairs_up_tile
            sx, sy = ux + 0.5, uy + 0.5
        elif not spawn_at_start and self.game_map.exit_tile:
            ex, ey = self.game_map.exit_tile
            sx, sy = ex + 0.5, ey + 0.5

        self.player.x = sx
        self.player.y = sy
        self.enemies.clear()
        self.ground_items.clear()
        self.enemies = self.ai.spawn_enemies(self.game_map, floor)

    def _on_enemy_killed(self, enemy: EnemyEntity, **_) -> None:
        self.kills += 1
        self.effects.spawn_death_explosion(enemy.x, enemy.y, big=enemy.is_boss)
        ups = self.player.experience.add_xp(enemy.xp_value)
        for _ in range(ups):
            self.player.stats.on_level_up()
        if enemy in self.enemies:
            self.enemies.remove(enemy)

    def _on_item_dropped(self, ground: GroundItem, **_) -> None:
        self.ground_items.append(ground)

    def _on_player_died(self, **_) -> None:
        self.state = GameState.GAME_OVER
        self._autosave()

    def _on_enemy_hit(self, **_) -> None:
        self.camera.add_shake(power=7.5, duration=0.06)

    def _on_attack_swung(self, hit_count: int = 0, **_) -> None:
        base_power = 2.8 if hit_count <= 0 else 4.0
        self.camera.add_shake(power=base_power, duration=0.04)

    def _autosave(self) -> None:
        if not self.player:
            return
        data = SaveData(
            floor=self.floor,
            kills=self.kills,
            player_data=self._player_to_dict(),
            floors_visited=list(self.floor_cache.keys()),
        )
        self.save_manager.save(data)

    def _player_to_dict(self) -> dict:
        p = self.player
        return {
            "x": p.x,
            "y": p.y,
            "stats": {
                "max_hp": p.stats.max_hp,
                "hp": p.stats.hp,
                "max_mana": p.stats.max_mana,
                "mana": p.stats.mana,
                "damage": p.stats.damage,
                "armor": p.stats.armor,
                "regen": p.stats.regen,
            },
            "inventory": p.inventory.to_dict(),
            "equipment": p.equipment.to_dict(),
            "experience": {
                "level": p.experience.level,
                "xp": p.experience.xp,
                "xp_to_next": p.experience.xp_to_next,
            },
        }

    def _update(self, dt: float) -> None:
        if self.state not in (GameState.PLAYING, GameState.INVENTORY):
            self.input.end_frame()
            return

        if self.state == GameState.PLAYING:
            self._update_playing(dt)

        self.input.end_frame()

    def _update_playing(self, dt: float) -> None:
        p = self.player
        gm = self.game_map
        inp = self.input.state

        self.movement.update(p, gm, inp, dt)
        p.heal_over_time(dt)
        self.camera.follow(p.x, p.y, dt)
        self.combat.update(dt, p, self.enemies)
        mw = screen_to_world(*inp.mouse_pos, self.camera.x, self.camera.y)
        self.skills.update(dt, p, self.enemies, gm, inp.whirlwind, mw)
        self.effects.update(dt)
        self.anim_time += dt

        for enemy in list(self.enemies):
            if enemy.alive:
                self.combat.enemy_attack_player(p, enemy, dt)

        self.ai.update(self.enemies, p, gm, dt, self.events)
        self.loot.pickup(p, self.ground_items)

        if inp.attack and p.attack_timer <= 0:
            mw = screen_to_world(*inp.mouse_pos, self.camera.x, self.camera.y)
            self.combat.try_attack(p, self.enemies, mw, inp.mouse_pos, self.camera)

        self._update_portal_hint()

        if p.hp <= 0:
            self.events.emit("player_died")

        if self.kills > 0 and self.kills % 5 == 0:
            self._autosave()

    def _update_portal_hint(self) -> None:
        p = self.player
        tx, ty = int(p.x), int(p.y)
        tt = self.game_map.tile_type_at(tx, ty)
        if tt == TileType.EXIT:
            self.portal_hint = "[E] Спуститься вниз"
        elif tt == TileType.STAIRS_UP and self.floor > 1:
            self.portal_hint = "[E] Подняться назад"
        else:
            self.portal_hint = None

    def _try_portal_transition(self) -> None:
        p = self.player
        tx, ty = int(p.x), int(p.y)
        tt = self.game_map.tile_type_at(tx, ty)
        if tt == TileType.EXIT:
            self._go_floor_down()
        elif tt == TileType.STAIRS_UP and self.floor > 1:
            self._go_floor_up()

    def _go_floor_down(self) -> None:
        self._autosave()
        next_floor = self.floor + 1
        self._load_floor(next_floor, spawn_at_start=True, from_above=False)

    def _go_floor_up(self) -> None:
        prev = max(1, self.floor - 1)
        self._load_floor(prev, from_above=True)

    def _draw(self) -> None:
        self.screen.fill((12, 14, 22))
        if self.state == GameState.MENU:
            self.menu_ui.draw(self.save_manager.exists())
            return
        if self.state == GameState.GAME_OVER:
            self._draw_world()
            self.game_over_ui.draw(self.floor, self.player.experience.level, self.kills)
            return

        self._draw_world()
        mouse = self.input.state.mouse_pos
        self.hud.draw(
            self.player,
            self.floor,
            self.kills,
            self.player.dash_cooldown_timer,
            skill_cooldowns=self.skills.cooldowns,
            whirlwind=self.input.state.whirlwind,
            inventory_open=(self.state == GameState.INVENTORY),
            mouse_pos=mouse,
            portal_hint=self.portal_hint,
        )
        if self.state == GameState.INVENTORY:
            self.inventory_ui.draw(self.player, mouse_pos=mouse)

    def _draw_world(self) -> None:
        cam = self.camera
        r = self.renderer
        t = self.anim_time

        # Background
        if self.bg_sprite:
            scaled = pygame.transform.scale(self.bg_sprite, (SCREEN_WIDTH, SCREEN_HEIGHT))
            self.screen.blit(scaled, (0, 0))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((8, 10, 18, 165))
            self.screen.blit(overlay, (0, 0))
        else:
            self.screen.fill((10, 12, 20))
            grad = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            for y in range(0, SCREEN_HEIGHT, 4):
                a = int(30 * y / SCREEN_HEIGHT)
                grad.fill((18, 22, 38, a), (0, y, SCREEN_WIDTH, 4))
            self.screen.blit(grad, (0, 0))

        tiles_drawn = []
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile = self.game_map.grid[y][x]
                if tile.type == TileType.VOID:
                    continue
                tiles_drawn.append((x + y, x, y, tile))

        tiles_drawn.sort(key=lambda item: item[0])
        for _, x, y, tile in tiles_drawn:
            color = tile.color()
            pulse = 0.0
            accent = None
            if tile.type == TileType.START:
                color = (46, 118, 82)
                pulse = 0.5 + 0.5 * math.sin(t * 2.5 + x)
                accent = (80, 200, 120)
            elif tile.type == TileType.EXIT:
                color = (158, 62, 48)
                pulse = 0.5 + 0.5 * math.sin(t * 3.0 + y)
                accent = (255, 120, 70)
            elif tile.type == TileType.STAIRS_UP:
                color = (72, 102, 162)
                pulse = 0.5 + 0.5 * math.sin(t * 2.8)
                accent = (130, 170, 255)
            elif tile.type == TileType.FLOOR and (x + y) % 7 == 0:
                color = (44, 50, 66)
            r.draw_iso_tile(x, y, cam.x, cam.y, color, pulse=pulse, accent=accent)

        for g in self.ground_items:
            sx, sy = cam.world_to_screen(g.x, g.y)
            r.draw_loot_orb(sx, sy, g.color(), t + g.x)

        for ring in self.effects.rings:
            sx, sy = cam.world_to_screen(ring.x, ring.y)
            rad = int(ring.max_radius * (1.0 - ring.life / ring.max_life))
            fade = ring.life / max(ring.max_life, 0.001)
            r.draw_aoe_ring_world(sx, sy, rad, ring.color, int(90 * fade + 40), width=4)

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            sx, sy = cam.world_to_screen(enemy.x, enemy.y)
            scale = enemy.draw_scale
            r.draw_entity_shadow(sx, sy, 16 * scale)
            sprite = self.enemy_tank_sprite if enemy.kind.name == "BRUTE" else self.enemy_sprite
            glow = (255, 80, 60) if enemy.is_boss else (200, 70, 70) if enemy.kind.name == "CASTER" else None
            if not r.blit_sprite(sprite, sx, sy, hit_flash=enemy.hit_flash > 0, scale=scale, glow_color=glow):
                body = (190, 75, 75) if enemy.hit_flash <= 0 else (255, 255, 255)
                if enemy.is_boss:
                    body = (220, 60, 60)
                elif enemy.kind.name == "CASTER":
                    body = (140, 80, 200)
                elif enemy.kind.name == "RUNNER":
                    body = (210, 100, 70)
                r.draw_character_orb(sx, sy, 18 * scale, body, accent=glow, hit_flash=enemy.hit_flash > 0)
            if enemy.casting > 0:
                cast_t = min(1.0, enemy.casting / 0.5)
                cast_r = int(20 * scale + 12 * cast_t)
                r.draw_aoe_ring_world(sx, sy, cast_r, (180, 90, 255), int(100 + 80 * cast_t), width=2)
            if enemy.is_boss:
                r.blit_text_outlined(r.font_label, "БОСС", (255, 90, 80), (int(sx) - 22, int(sy) - int(34 * scale)))
            r.draw_hp_bar_world(sx, sy - int(28 * scale), enemy.hp / max(enemy.max_hp, 1), width=int(38 * scale))

        for exp in self.effects.explosions:
            sx, sy = cam.world_to_screen(exp.x, exp.y)
            rad = int(exp.radius)
            surf = pygame.Surface((rad * 2 + 4, rad * 2 + 4), pygame.SRCALPHA)
            alpha = int(240 * (exp.life / max(exp.max_life, 0.001)))
            pygame.draw.circle(surf, (*exp.color, alpha), (rad + 2, rad + 2), rad)
            pygame.draw.circle(surf, (255, 220, 180, alpha // 2), (rad + 2, rad + 2), max(1, rad // 2))
            self.screen.blit(surf, (int(sx) - rad - 2, int(sy) - rad - 2))

        for p in self.effects.particles:
            sx, sy = cam.world_to_screen(p.x, p.y)
            fade = max(0.0, min(1.0, p.life / max(p.max_life, 0.001)))
            pr, pg, pb = p.color
            col = (int(pr * fade), int(pg * fade), int(pb * fade))
            size = max(1, int(p.size * fade))
            if size > 2:
                glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*col, int(80 * fade)), (size * 2, size * 2), size + 2)
                self.screen.blit(glow, glow.get_rect(center=(int(sx), int(sy - 8))))
            pygame.draw.circle(self.screen, col, (int(sx), int(sy - 8)), size)

        for proj in self.skills.projectiles:
            sx, sy = cam.world_to_screen(proj.x, proj.y)
            r.draw_fireball(sx, sy, t + proj.x)

        for m in self.skills.minions:
            sx, sy = cam.world_to_screen(m.x, m.y)
            r.draw_entity_shadow(sx, sy, 12)
            col = (100, 255, 160) if m.hit_flash <= 0 else (255, 255, 255)
            r.draw_character_orb(sx, sy, 14, col, accent=(80, 220, 140), hit_flash=m.hit_flash > 0)

        for sx_w, sy_w, val, alpha in self.combat.damage_numbers:
            sx, sy = cam.world_to_screen(sx_w, sy_w)
            r.blit_text_outlined(
                r.font_damage,
                str(val),
                (255, 230, 130),
                (int(sx) - 8, int(sy) - 24),
                outline=(80, 40, 10),
                alpha=int(alpha * 255),
            )

        px, py = cam.world_to_screen(self.player.x, self.player.y)
        r.draw_entity_shadow(px, py, 18)
        if self.player.is_dashing:
            r.draw_dash_trail(px, py, t)
        if not r.blit_sprite(self.player_sprite, px, py, hit_flash=self.player.hit_flash > 0, glow_color=(80, 220, 140)):
            r.draw_character_orb(px, py, 18, (80, 230, 120), accent=(100, 255, 180), hit_flash=self.player.hit_flash > 0)

        if self.input.state.whirlwind and self.state == GameState.PLAYING:
            sx, sy = cam.world_to_screen(self.player.x, self.player.y)
            r.draw_whirlwind(sx, sy, 62, self.skills.whirlwind_angle)

        for slash in self.combat.slashes:
            sx, sy = cam.world_to_screen(slash.x, slash.y)
            r.draw_arc_slash(sx, sy, 68, slash.angle, slash.arc, slash.progress)

        ex, ey = self.game_map.exit_tile
        sx, sy = cam.world_to_screen(ex + 0.5, ey + 0.5)
        r.draw_portal_marker(sx, sy, "ВНИЗ", (255, 170, 110), t, direction="down")
        if self.game_map.stairs_up_tile:
            ux, uy = self.game_map.stairs_up_tile
            sx2, sy2 = cam.world_to_screen(ux + 0.5, uy + 0.5)
            r.draw_portal_marker(sx2, sy2, "НАЗАД", (140, 175, 255), t + 1.5, direction="up")

        r.draw_vignette(0.85)
