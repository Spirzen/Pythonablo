"""Main game loop and state machine."""

from __future__ import annotations

import math
import random
import shutil
import sys
from pathlib import Path
from typing import Optional

import pygame

from core.combo_defs import streak_milestone
from core.config import (
    ARENA_ROUND_DIFFICULTY_STEP,
    ARENA_ROUND_DURATION,
    ASSETS_DIR,
    DIFFICULTY_MULT,
    GAME_MODE_LABELS,
    Difficulty,
    FPS,
    GameMode,
    GameState,
    ItemQuality,
    MAP_HEIGHT,
    MAP_WIDTH,
    PORTAL_INTERACT_RADIUS,
    SCREEN_HEIGHT,
    SCREEN_WIDTH,
    SPEED_MODE_MULT,
    TITLE,
    TileType,
)
from world.collision import can_occupy, clamp_to_walkable
from core.event_bus import EventBus
from engine.audio import AudioSystem
from engine.camera import Camera
from engine.input_handler import InputHandler
from engine.motion import motion_visual, tick_motion
from engine.map_renderer import MapRenderer
from engine.renderer import Renderer, screen_to_world
from engine.screen_flash import ScreenFlash
from engine.sprite_catalog import SpriteCatalog
from systems.effects import EffectSystem
from systems.movement_system import MovementSystem
from entities.enemy import EnemyEntity
from entities.item import GroundItem
from entities.npc import NPC
from entities.pillar import Pillar
from entities.player import PlayerEntity
from entities.villager import VillagerNPC
from player.equipment import Equipment
from player.experience import Experience
from player.inventory import Inventory
from player.buffs import BONUS_COLORS
from player.settings import GameSettings
from player.skill_tree import SkillTree
from player.skill_upgrades import SkillUpgrades
from player.stats import Stats
from save.floor_state import floor_state_to_dict, restore_floor_state
from save.save_manager import SaveData, SaveManager
from systems.ai_system import AISystem
from systems.bonus_system import BonusSystem
from systems.combat_system import CombatSystem
from systems.encounter_system import EncounterSystem, EncounterType
from systems.enemy_status import update_enemy_status
from systems.loot_system import LootSystem
from systems.pillar_effects import PILLAR_EFFECTS, apply_pillar_effect, roll_pillar_effect
from systems.skill_system import SkillSystem
from ui.hud import HUD
from ui.inventory_ui import InventoryUI
from ui.menu import GameOverUI, MenuUI
from ui.merchant_ui import MerchantUI
from ui.pause_ui import PauseUI
from ui.skill_upgrade_ui import SkillUpgradeUI
from ui.skill_tree_ui import SkillTreeUI
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
        self.map_renderer = MapRenderer(self.renderer)
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
        self.bonuses = BonusSystem(self.events, self.effects)

        self.sprites = SpriteCatalog()
        self.player_sprite = self.sprites.player
        self.bg_sprite = self.sprites.bg

        self.menu_ui = MenuUI(self.renderer)
        self.menu_ui.set_logo(self.sprites.logo_menu)
        self.hud = HUD(self.renderer)
        self.hud.set_icons(
            fire=self.sprites.fireball,
            whirlwind=self.sprites.whirlwind,
            inventory=self.sprites.inventory,
        )
        self.inventory_ui = InventoryUI(self.renderer)
        self.inventory_ui.set_loot_system(self.loot)
        self.game_over_ui = GameOverUI(self.renderer)
        self.pause_ui = PauseUI(self.renderer)
        self.skill_tree_ui = SkillTreeUI(self.renderer)
        self.skill_upgrade_ui = SkillUpgradeUI(self.renderer)
        self.merchant_ui = MerchantUI(self.renderer)
        self.merchant_ui.set_loot_system(self.loot)

        self.state = GameState.MENU
        self.difficulty = Difficulty.NORMAL
        self.game_mode = GameMode.CLASSIC
        self.portal_hint: str | None = None
        self.player: PlayerEntity | None = None
        self.game_map: GameMap | None = None
        self.enemies: list[EnemyEntity] = []
        self.ground_items: list[GroundItem] = []
        self.floor = 1
        self.kills = 0
        self.floor_cache: dict[int, GameMap] = {}
        self.floor_states: dict[int, dict] = {}
        self.came_from_above = False
        self.anim_time = 0.0
        self.npcs: list[NPC] = []
        self._last_autosave_kills = 0
        self.level_up_banner: float = 0.0
        self.level_up_text: str = ""
        self.toast_message: str = ""
        self.toast_timer: float = 0.0
        self.floating_texts: list[tuple[float, float, str, tuple, float]] = []
        self.skill_upgrade_selected: int = 0
        self._set_pulse_timer: float = 0.0
        self.floor_elites_spawned: set[int] = set()
        self.next_mentor_floor: int = 3
        self.arena_active: bool = False
        self.arena_timer: float = 0.0
        self.arena_spawn_cd: float = 0.0
        self.arena_round: int = 1
        self.arena_round_difficulty: float = 1.0
        self.pillars: list[Pillar] = []
        self._prev_state: GameState | None = None
        self.encounters = EncounterSystem()
        self.villager: VillagerNPC | None = None
        self.death_killer: str | None = None
        self.encounter_wave_cd: float = 0.0
        self._villager_failed: bool = False
        self._bg_composite: pygame.Surface | None = None
        self._enemy_templates: list = self._load_enemy_templates()
        self._portal_hint_cd: float = 0.0
        self._cached_portal_hint: str | None = None
        self.kill_streak: int = 0
        self.kill_streak_timer: float = 0.0
        self.screen_flash = ScreenFlash()
        self.epic_banner_text: str = ""
        self.epic_banner_color: tuple[int, int, int] = (255, 200, 80)
        self.epic_banner_timer: float = 0.0
        self.hitstop_timer: float = 0.0

        self.events.subscribe("enemy_killed", self._on_enemy_killed)
        self.events.subscribe("item_dropped", self._on_item_dropped)
        self.events.subscribe("item_picked", self._on_item_picked)
        self.events.subscribe("bonus_picked", self._on_bonus_picked)
        self.events.subscribe("legendary_proc", self._on_legendary_proc)
        self.events.subscribe("inventory_full", self._on_inventory_full)
        self.events.subscribe("player_died", self._on_player_died)
        self.events.subscribe("goblin_hit", self._on_goblin_hit)
        self.events.subscribe("enemy_hit", self._on_enemy_hit)
        self.events.subscribe("attack_swung", self._on_attack_swung)
        self.events.subscribe("skill_cast", self._on_skill_cast)

        self.audio.play_music("menu")

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
                    mode = self._menu_action_to_mode(action)
                    if mode is not None:
                        self._start_new_game(mode)
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
                elif self.state == GameState.PAUSED:
                    action = self.pause_ui.handle_click(event.pos, self.player)
                    if action:
                        self._handle_pause_action(action)
                elif self.state == GameState.SKILL_UPGRADE:
                    if self.skill_upgrade_ui.handle_click(event.pos, self.player):
                        self.audio.play_sfx("skill")
                        if self.player.skill_upgrades.pending_points <= 0:
                            self.state = self._prev_state or GameState.PLAYING
                elif self.state == GameState.SKILLS:
                    if self.skill_tree_ui.handle_click(event.pos, self.player):
                        self.audio.play_sfx("ui")
                elif self.state == GameState.MERCHANT:
                    if self.merchant_ui.handle_click(event.pos, self.player):
                        self.audio.play_sfx("gold")
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
            mode = self._menu_action_to_mode(action)
            if mode is not None:
                self._start_new_game(mode)
            elif action == "continue":
                self._load_game()
            elif action == "quit":
                self.running = False
            elif inp.menu_back:
                self.running = False
            return

        if self.state == GameState.GAME_OVER and inp.menu_confirm:
            self.audio.play_sfx("menu")
            self.state = GameState.MENU
            self.audio.play_music("menu")
            return

        if self.state == GameState.PAUSED:
            if inp.menu_back:
                self.state = GameState.PLAYING
                return
            action = self.pause_ui.handle_input(inp.menu_up, inp.menu_down, inp.menu_confirm)
            if action == "toggle_autopickup":
                self.player.settings.auto_pickup = not self.player.settings.auto_pickup
                self.audio.play_sfx("ui")
            elif action:
                self._handle_pause_action(action)
            return

        if self.state == GameState.SKILL_UPGRADE:
            if inp.menu_back:
                self.state = self._prev_state or GameState.PLAYING
                return
            if inp.menu_up:
                self.skill_upgrade_selected = max(0, self.skill_upgrade_selected - 1)
            if inp.menu_down:
                from player.skill_upgrades import UPGRADEABLE_SKILLS
                self.skill_upgrade_selected = min(len(UPGRADEABLE_SKILLS) - 1, self.skill_upgrade_selected + 1)
            if self.skill_upgrade_ui.handle_input(inp.menu_confirm, self.player, self.skill_upgrade_selected):
                self.audio.play_sfx("skill")
                if self.player.skill_upgrades.pending_points <= 0:
                    self.state = self._prev_state or GameState.PLAYING
            return

        if self.state == GameState.SKILLS:
            if inp.menu_back:
                self.state = self._prev_state or GameState.PLAYING
                return
            if self.skill_tree_ui.handle_input(inp.menu_up, inp.menu_down, inp.menu_confirm, self.player):
                self.audio.play_sfx("ui")
            return

        if self.state == GameState.MERCHANT:
            if inp.menu_back:
                self.state = GameState.PLAYING
                return
            if self.merchant_ui.handle_input(inp.menu_up, inp.menu_down, inp.menu_confirm, self.player):
                self.audio.play_sfx("gold")
            return

        if self.state == GameState.PLAYING:
            if inp.menu_back:
                self.state = GameState.PAUSED
                self.pause_ui.selected = 0
                self.audio.play_sfx("menu")
                return
            if inp.dash_pressed:
                self.movement.try_dash(self.player, self.game_map, inp)
            if inp.inventory_pressed:
                self.state = GameState.INVENTORY
            if inp.interact_pressed:
                if self._try_npc_interact():
                    pass
                elif self._try_pillar_interact():
                    pass
                elif self.loot.pickup(self.player, self.ground_items, manual=True):
                    pass
                elif self.bonuses.try_pickup(self.player, self.enemies, threshold=1.2):
                    pass
                else:
                    self._try_portal_transition()
            if inp.skill_pressed:
                mw = screen_to_world(*inp.mouse_pos, self.camera.x, self.camera.y)
                self.skills.try_skill(inp.skill_pressed, self.player, self.enemies, self.game_map, mw)

        if self.state == GameState.INVENTORY:
            if inp.menu_back or inp.inventory_pressed:
                self.state = GameState.PLAYING
            return

    def _handle_pause_action(self, action: str) -> None:
        if action == "resume":
            self.state = GameState.PLAYING
        elif action == "save":
            self._autosave()
            self.toast_message = "Игра сохранена"
            self.toast_timer = 2.0
            self.audio.play_sfx("ui")
        elif action == "skills":
            self.toast_message = "Найдите Наставника на этаже (появляется каждые 2–4 ур.)"
            self.toast_timer = 3.0
        elif action == "skill_upgrade":
            self._prev_state = GameState.PAUSED
            self.state = GameState.SKILL_UPGRADE
            self.skill_upgrade_selected = 0
        elif action == "toggle_autopickup":
            self.audio.play_sfx("ui")
        elif action == "menu":
            self._autosave()
            self.state = GameState.MENU
            self.audio.play_music("menu")

    @staticmethod
    def _load_enemy_templates() -> list:
        import json
        from core.config import DATA_DIR
        path = DATA_DIR / "enemies.json"
        if path.exists():
            with open(path, encoding="utf-8") as f:
                return json.load(f).get("enemies", [])
        return []

    def _ensure_bg(self) -> None:
        if self._bg_composite is not None:
            return
        if self.bg_sprite:
            scaled = pygame.transform.smoothscale(self.bg_sprite, (SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((12, 8, 18, 150))
            composite = scaled.copy()
            composite.blit(overlay, (0, 0))
            warmth = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            cx, cy = SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.65)
            for ring in range(10, 0, -1):
                alpha = int(14 * (1.0 - ring / 10))
                pygame.draw.circle(warmth, (255, 140, 60, alpha), (cx, cy), ring * 60)
            composite.blit(warmth, (0, 0))
            self._bg_composite = composite.convert()
        else:
            grad = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            for y in range(SCREEN_HEIGHT):
                t = y / SCREEN_HEIGHT
                r = int(8 + t * 14)
                g = int(10 + t * 16)
                b = int(22 + t * 28)
                pygame.draw.line(grad, (r, g, b), (0, y), (SCREEN_WIDTH, y))
            # Subtle radial warmth at center-bottom (torchlight feel)
            warmth = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            cx, cy = SCREEN_WIDTH // 2, int(SCREEN_HEIGHT * 0.72)
            for ring in range(12, 0, -1):
                alpha = int(18 * (1.0 - ring / 12))
                pygame.draw.circle(warmth, (255, 160, 80, alpha), (cx, cy), ring * 55)
            grad.blit(warmth, (0, 0))
            self._bg_composite = grad.convert()

    @staticmethod
    def _menu_action_to_mode(action: str | None) -> GameMode | None:
        mapping = {
            "mode_classic": GameMode.CLASSIC,
            "mode_arena": GameMode.ARENA,
            "mode_arena_bosses": GameMode.ARENA_BOSSES,
            "mode_speed": GameMode.SPEED,
        }
        return mapping.get(action) if action else None

    def _start_new_game(self, mode: GameMode = GameMode.CLASSIC) -> None:
        self.save_manager.delete()
        self.floor = 1
        self.kills = 0
        self._last_autosave_kills = 0
        self.kill_streak = 0
        self.kill_streak_timer = 0.0
        self.epic_banner_timer = 0.0
        self.hitstop_timer = 0.0
        self.difficulty = self.menu_ui.difficulty
        self.game_mode = mode
        self.floor_cache.clear()
        self.floor_states.clear()
        self.floor_elites_spawned.clear()
        self.encounters.reset()
        self.death_killer = None
        self._villager_failed = False
        self.next_mentor_floor = random.randint(2, 4)
        self.arena_active = False
        self.arena_round = 1
        self.arena_round_difficulty = 1.0
        self.player = PlayerEntity(
            x=0, y=0, stats=Stats(), inventory=Inventory(), equipment=Equipment(),
            experience=Experience(), skill_tree=SkillTree(),
        )
        self._apply_difficulty_to_player()
        self._apply_mode_settings()
        self.ai.set_difficulty(DIFFICULTY_MULT[self.difficulty])
        self.ai.set_game_mode(mode)
        self.loot.set_game_mode(mode)
        self.bonuses.set_game_mode(mode)
        if mode in (GameMode.ARENA, GameMode.ARENA_BOSSES):
            self._load_dedicated_arena()
        else:
            self._load_floor(1, spawn_at_start=True)
        self.map_renderer.invalidate()
        self._bg_composite = None
        self.state = GameState.PLAYING
        self.audio.play_music("dungeon")

    def _apply_mode_settings(self) -> None:
        if self.game_mode == GameMode.SPEED:
            self.player.settings.auto_pickup = True
            self.player.mode_speed_mult = SPEED_MODE_MULT
        else:
            self.player.mode_speed_mult = 1.0

    def _load_dedicated_arena(self, *, restore_entities: bool = False) -> None:
        self.game_map = GameMap(floor=1, seed=random.randint(0, 999999), force_arena=True)
        self.map_renderer.invalidate()
        self.npcs.clear()
        self.pillars.clear()
        self.villager = None
        self.arena_active = True
        self.arena_timer = ARENA_ROUND_DURATION
        self.arena_spawn_cd = 0.5

        saved = self.floor_states.get(1) if restore_entities else None
        if saved:
            self.enemies, self.ground_items, bonus_data = restore_floor_state(saved)
            self.bonuses.restore_ground(bonus_data)
        else:
            self.enemies.clear()
            self.ground_items.clear()
            self.bonuses.ground_bonuses.clear()
            sx, sy = self._walkable_at_tile(self.game_map.spawn_x, self.game_map.spawn_y)
            self.player.x, self.player.y = sx, sy
            label = GAME_MODE_LABELS[self.game_mode]
            self.toast_message = f"{label}! Раунд {self.arena_round} — выживайте!"
            self.toast_timer = 4.0
            self._arena_spawn_wave()

        self.audio.play_music("boss")

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
        self._last_autosave_kills = self.kills
        try:
            self.difficulty = Difficulty(data.difficulty)
        except ValueError:
            self.difficulty = Difficulty.NORMAL
        try:
            self.game_mode = GameMode(data.game_mode)
        except ValueError:
            self.game_mode = GameMode.CLASSIC
        self.player = PlayerEntity(x=0, y=0, skill_tree=SkillTree())
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
                strength=s.get("strength", 10),
                dexterity=s.get("dexterity", 10),
                vitality=s.get("vitality", 10),
                energy=s.get("energy", 10),
            )
            self.player.x = pd.get("x", 0)
            self.player.y = pd.get("y", 0)
            self.player.inventory = Inventory.from_dict(pd.get("inventory", {}))
            self.player.equipment = Equipment.from_dict(pd.get("equipment", {}))
            exp = pd.get("experience", {})
            self.player.experience = Experience(
                level=exp.get("level", 1),
                xp=exp.get("xp", 0),
                xp_to_next=exp.get("xp_to_next", 12),
            )
            if pd.get("skill_tree"):
                self.player.skill_tree = SkillTree.from_dict(pd["skill_tree"])
            if pd.get("skill_upgrades"):
                self.player.skill_upgrades = SkillUpgrades.from_dict(pd["skill_upgrades"])
            if pd.get("settings"):
                self.player.settings = GameSettings.from_dict(pd["settings"])
            from player.buffs import BuffManager
            if pd.get("buffs"):
                self.player.buffs = BuffManager.from_dict(pd["buffs"])
            self.next_mentor_floor = pd.get("next_mentor_floor", random.randint(2, 4))
        else:
            self.next_mentor_floor = random.randint(2, 4)
        self.player.clamp_resources()
        self.floor_cache.clear()
        self.floor_states = {int(k): v for k, v in data.floor_states.items()} if data.floor_states else {}
        self._apply_mode_settings()
        self.ai.set_difficulty(DIFFICULTY_MULT[self.difficulty])
        self.ai.set_game_mode(self.game_mode)
        self.loot.set_game_mode(self.game_mode)
        self.bonuses.set_game_mode(self.game_mode)
        if self.game_mode in (GameMode.ARENA, GameMode.ARENA_BOSSES):
            self.arena_round = data.arena_round
            self.arena_round_difficulty = data.arena_round_difficulty
            self._load_dedicated_arena(restore_entities=True)
        else:
            self._load_floor(self.floor, spawn_at_start=False, restore_entities=True, keep_player_pos=True)
        self.state = GameState.PLAYING
        self.audio.play_music("dungeon")

    def _load_floor(
        self,
        floor: int,
        *,
        spawn_at_start: bool = True,
        from_above: bool = False,
        restore_entities: bool = False,
        keep_player_pos: bool = False,
    ) -> None:
        self._save_current_floor_state()
        self.floor = floor
        self.came_from_above = from_above
        prev_map = self.game_map
        if floor in self.floor_cache and self.floor_cache[floor].map_type != "arena":
            self.game_map = self.floor_cache[floor]
            if from_above:
                self.game_map.respawn_enemies_flag()
        else:
            self.game_map = GameMap(
                floor=floor,
                seed=floor * 7919,
                allow_random_arena=self.game_mode not in (GameMode.CLASSIC, GameMode.SPEED),
            )
            self.floor_cache[floor] = self.game_map
        if prev_map is not self.game_map:
            self.map_renderer.invalidate()

        saved = self.floor_states.get(floor) if restore_entities else None
        is_arena = self.game_map.map_type == "arena"
        self.arena_active = False
        self.pillars.clear()
        self.villager = None
        self.encounter_wave_cd = 0.0
        self._villager_failed = False

        encounter = self.encounters.roll_for_floor(
            floor, is_arena=is_arena, is_boss_floor=(floor % 3 == 0),
        )
        horde_mult = encounter.horde_mult

        if saved and not is_arena:
            self.enemies, self.ground_items, bonus_data = restore_floor_state(saved)
            self.bonuses.restore_ground(bonus_data)
        elif is_arena and self.game_mode == GameMode.CLASSIC:
            self.enemies.clear()
            self.ground_items.clear()
            self.bonuses.ground_bonuses.clear()
            self.arena_active = True
            self.arena_timer = ARENA_ROUND_DURATION
            self.arena_spawn_cd = 0.5
            self.toast_message = "АРЕНА! Выживите 30 секунд!"
            self.toast_timer = 4.0
            self._arena_spawn_wave()
        else:
            self.enemies.clear()
            self.ground_items.clear()
            self.bonuses.ground_bonuses.clear()
            self.enemies = self.ai.spawn_enemies(self.game_map, floor, horde_mult=horde_mult)
            if floor not in self.floor_elites_spawned and encounter.kind != EncounterType.KILL_ALL_ELITE:
                elites = self.ai.spawn_floor_elites(self.game_map, floor, self._enemy_templates)
                if elites:
                    self.enemies.extend(elites)
                    self.floor_elites_spawned.add(floor)
                    self.toast_message = f"Особые враги! ({len(elites)})"
                    self.toast_timer = 3.0
            self._apply_encounter_start(floor, encounter)
            self._spawn_pillars(floor)

        if not keep_player_pos:
            sx, sy = self._resolve_spawn(from_above=from_above, spawn_at_start=spawn_at_start)
            self.player.x, self.player.y = clamp_to_walkable(self.game_map, sx, sy)

        self._spawn_npcs(floor)
        self.audio.play_sfx("floor")
        if floor % 3 == 0:
            self.audio.play_music("boss")
            if self.game_mode == GameMode.CLASSIC and not is_arena:
                self.epic_banner_text = f"БОСС-ЭТАЖ — {floor}"
                self.epic_banner_color = (255, 80, 55)
                self.epic_banner_timer = 3.2
                self.screen_flash.trigger((180, 30, 20), 0.55, alpha=150)
                self.camera.add_shake(power=10.0, duration=0.2)
                self.audio.play_sfx("boss_alert")
        else:
            self.audio.play_music("dungeon")

    def _apply_encounter_start(self, floor: int, encounter) -> None:
        if not encounter.active:
            return
        label = encounter.label()
        if label:
            self.toast_message = label
            self.toast_timer = 4.0

        if encounter.kind == EncounterType.RANDOM_BUFF:
            kind = random.choice(["damage", "speed", "armor", "skill_boost"])
            self.player.buffs.add(kind, 18.0, magnitude=1.2)
        elif encounter.kind == EncounterType.RANDOM_DEBUFF:
            kind = random.choice(["damage", "speed", "skill_boost"])
            self.player.buffs.add(kind, 16.0, magnitude=-0.75)
            self.player.stats.hp = max(1.0, self.player.stats.hp * 0.85)
        elif encounter.kind == EncounterType.PROTECT_NPC:
            self._spawn_villager(floor)
            self.encounter_wave_cd = 8.0
        elif encounter.kind == EncounterType.TREASURE_GOBLINS and not encounter.goblins_spawned:
            goblins = self.ai.spawn_treasure_goblins(self.game_map, floor, count=random.randint(2, 3))
            self.enemies.extend(goblins)
            encounter.goblins_spawned = True

    def _spawn_villager(self, floor: int) -> None:
        for _ in range(60):
            tx = random.randint(6, MAP_WIDTH - 7)
            ty = random.randint(6, MAP_HEIGHT - 7)
            wx, wy = tx + 0.5, ty + 0.5
            if not can_occupy(self.game_map, wx, wy):
                continue
            if (tx, ty) in (self.game_map.start_tile, self.game_map.exit_tile):
                continue
            hp = 100 + floor * 15
            self.villager = VillagerNPC(x=wx, y=wy, max_hp=hp, hp=hp)
            return

    def _spawn_encounter_elite(self) -> None:
        elites = self.ai.spawn_floor_elites(self.game_map, self.floor, self._enemy_templates)
        if not elites:
            for _ in range(40):
                tx = random.randint(3, MAP_WIDTH - 4)
                ty = random.randint(3, MAP_HEIGHT - 4)
                wx, wy = tx + 0.5, ty + 0.5
                if not can_occupy(self.game_map, wx, wy):
                    continue
                e = self.ai._make_enemy(wx, wy, self.game_map.area_level, None)
                e.is_floor_elite = True
                e.max_hp *= 4.0
                e.hp = e.max_hp
                e.display_name = "Элита энкаунтера"
                elites = [e]
                break
        if elites:
            self.enemies.extend(elites[:1])
            self.encounters.mark_elite_spawned()
            self.toast_message = "Появилась элита!"
            self.toast_timer = 3.0
            self.audio.play_sfx("level_up")

    def _spawn_protect_wave(self) -> None:
        if not self.villager or not self.villager.alive:
            return
        vx, vy = self.villager.x, self.villager.y
        for _ in range(random.randint(3, 5)):
            for _attempt in range(30):
                ox = random.uniform(-6, 6)
                oy = random.uniform(-6, 6)
                wx, wy = vx + ox, vy + oy
                if not can_occupy(self.game_map, wx, wy):
                    continue
                tmpl = self.ai._pick_template(self._enemy_templates) if self._enemy_templates else None
                self.enemies.append(self.ai._make_enemy(wx, wy, self.game_map.area_level, tmpl))
                break

    def _resolve_spawn(self, *, from_above: bool, spawn_at_start: bool) -> tuple[float, float]:
        gm = self.game_map
        if from_above:
            if gm.stairs_up_tile:
                return self._walkable_at_tile(*gm.stairs_up_tile)
            if gm.exit_tile:
                return self._walkable_at_tile(*gm.exit_tile)
        if not spawn_at_start and gm.exit_tile:
            return self._walkable_at_tile(*gm.exit_tile)
        return self._walkable_at_tile(gm.spawn_x, gm.spawn_y)

    def _walkable_at_tile(self, tx: int, ty: int) -> tuple[float, float]:
        candidates = [
            (tx, ty),
            (tx + 1, ty),
            (tx - 1, ty),
            (tx, ty + 1),
            (tx, ty - 1),
            (tx + 1, ty + 1),
            (tx - 1, ty + 1),
            (tx + 1, ty - 1),
            (tx - 1, ty - 1),
        ]
        for cx, cy in candidates:
            wx, wy = cx + 0.5, cy + 0.5
            if self.game_map.is_walkable(cx, cy) and can_occupy(self.game_map, wx, wy):
                return wx, wy
        for radius in range(2, 8):
            for dy in range(-radius, radius + 1):
                for dx in range(-radius, radius + 1):
                    if abs(dx) != radius and abs(dy) != radius:
                        continue
                    cx, cy = tx + dx, ty + dy
                    wx, wy = cx + 0.5, cy + 0.5
                    if self.game_map.is_walkable(cx, cy) and can_occupy(self.game_map, wx, wy):
                        return wx, wy
        return clamp_to_walkable(self.game_map, tx + 0.5, ty + 0.5)

    def _near_tile(self, tile_type: TileType) -> bool:
        p = self.player
        r = PORTAL_INTERACT_RADIUS
        r_sq = r * r
        for ty in range(int(p.y) - 2, int(p.y) + 3):
            for tx in range(int(p.x) - 2, int(p.x) + 3):
                if self.game_map.tile_type_at(tx, ty) != tile_type:
                    continue
                wx, wy = tx + 0.5, ty + 0.5
                if p.distance_sq_to(wx, wy) <= r_sq:
                    return True
        return False

    def _save_current_floor_state(self) -> None:
        if not self.player or not self.game_map:
            return
        floor_key = 1 if self.game_mode in (GameMode.ARENA, GameMode.ARENA_BOSSES) else self.floor
        self.floor_states[floor_key] = floor_state_to_dict(
            self.enemies, self.ground_items, self.bonuses.ground_to_dict()
        )

    def _schedule_next_mentor(self) -> None:
        self.next_mentor_floor = self.floor + random.randint(2, 4)

    def _spawn_npcs(self, floor: int) -> None:
        self.npcs.clear()
        if self.game_map.map_type == "arena":
            return
        if floor % 3 == 2:
            sx = self.game_map.spawn_x + 0.5
            sy = self.game_map.spawn_y + 0.5
            self.npcs.append(NPC(x=sx + 1.2, y=sy, name="Кузнец", dialog_id="smith", sprite_name="npc1.png"))
        if floor == self.next_mentor_floor:
            sx = self.game_map.spawn_x + 0.5
            sy = self.game_map.spawn_y + 0.5
            for ox, oy in ((2.5, 0.5), (-2.0, 1.0), (0.5, -2.0)):
                wx, wy = sx + ox, sy + oy
                if can_occupy(self.game_map, wx, wy):
                    self.npcs.append(NPC(x=wx, y=wy, name="Наставник", dialog_id="mentor", sprite_name="npc2.png"))
                    break
            self._schedule_next_mentor()

    def _spawn_pillars(self, floor: int) -> None:
        self.pillars.clear()
        if self.game_map.map_type != "dungeon":
            return
        count = random.randint(2, 4)
        for i in range(count):
            for _ in range(40):
                tx = random.randint(4, MAP_WIDTH - 5)
                ty = random.randint(4, MAP_HEIGHT - 5)
                wx, wy = tx + 0.5, ty + 0.5
                if not can_occupy(self.game_map, wx, wy):
                    continue
                if (tx, ty) in (self.game_map.start_tile, self.game_map.exit_tile):
                    continue
                if self.game_map.stairs_up_tile and (tx, ty) == self.game_map.stairs_up_tile:
                    continue
                eff = roll_pillar_effect(random.Random(floor * 1000 + i))
                self.pillars.append(
                    Pillar(
                        x=wx, y=wy, pillar_id=f"p{i}",
                        effect_id=eff[0], is_buff=eff[2], label=eff[1],
                    )
                )
                break

    def _arena_spawn_wave(self) -> None:
        endless = self.game_mode in (GameMode.ARENA, GameMode.ARENA_BOSSES)
        if endless:
            count = 3 + self.arena_round + random.randint(0, 2)
            diff = self.arena_round_difficulty
            bosses_only = self.game_mode == GameMode.ARENA_BOSSES
            area_floor = self.arena_round
        else:
            count = 4 + self.floor // 2 + random.randint(0, 2)
            diff = 1.0
            bosses_only = False
            area_floor = self.floor
        wave = self.ai.spawn_arena_wave(
            self.game_map,
            area_floor,
            self._enemy_templates,
            count=count,
            difficulty_mult=diff,
            bosses_only=bosses_only,
        )
        self.enemies.extend(wave)

    def _try_pillar_interact(self) -> bool:
        for pillar in self.pillars:
            if pillar.used:
                continue
            if self.player.distance_to(pillar) < 1.5:
                pillar.used = True
                eff = next(e for e in PILLAR_EFFECTS if e[0] == pillar.effect_id)
                if not eff:
                    eff = roll_pillar_effect(random.Random())
                label = apply_pillar_effect(self.player, eff) or eff[1]
                self.toast_message = label
                self.toast_timer = 2.5
                col = (100, 255, 140) if eff[2] else (255, 100, 100)
                self.floating_texts.append((pillar.x, pillar.y, label, col, 1.0))
                self.audio.play_sfx("ui")
                return True
        return False

    def _try_npc_interact(self) -> bool:
        for npc in self.npcs:
            if self.player.distance_to(npc) < 1.4:
                if npc.dialog_id == "mentor":
                    self._prev_state = GameState.PLAYING
                    self.state = GameState.SKILLS
                    self.skill_tree_ui.scroll = 0
                    self.skill_tree_ui.selected = 0
                    self.audio.play_sfx("menu")
                    return True
                self.merchant_ui.open(self.floor)
                self.state = GameState.MERCHANT
                self.audio.play_sfx("menu")
                return True
        return False

    def _on_enemy_killed(self, enemy: EnemyEntity, **_) -> None:
        self.kills += 1
        self.effects.spawn_death_explosion(enemy.x, enemy.y, big=enemy.is_boss)
        xp_mult = 1.0 + self.player.equipment.bonus("xp_bonus") * 0.02
        if self.kill_streak >= 3:
            xp_mult *= 1.0 + min(0.25, (self.kill_streak - 2) * 0.03)
        xp_gain = int(enemy.xp_value * xp_mult)
        ups = self.player.experience.add_xp(xp_gain)
        self.effects.spawn_xp_sparkles(enemy.x, enemy.y, amount=10 + min(12, self.kill_streak))
        self.floating_texts.append((enemy.x, enemy.y, f"+{xp_gain} XP", (255, 220, 90), 1.0))
        self.kill_streak += 1
        self.kill_streak_timer = 4.0
        milestone = streak_milestone(self.kill_streak)
        if milestone:
            _, label, color = milestone
            self.epic_banner_text = label
            self.epic_banner_color = color
            self.epic_banner_timer = 1.9
            self.screen_flash.trigger(color, 0.32, alpha=110)
            self.camera.add_shake(power=5.0 + self.kill_streak * 0.25, duration=0.14)
            self.audio.play_sfx("combo")
        if enemy.is_boss:
            self.epic_banner_text = "БОСС ПОБЕЖДЁН!"
            self.epic_banner_color = (255, 200, 80)
            self.epic_banner_timer = 2.8
            self.screen_flash.trigger((255, 50, 20), 0.55, alpha=190)
            self.camera.add_shake(power=18.0, duration=0.28)
            self.hitstop_timer = max(self.hitstop_timer, 0.12)
            self.audio.play_sfx("boss_alert")
        for _ in range(ups):
            self.player.stats.on_level_up()
            self.player.skill_tree.unspent_points += 1
            self.audio.play_sfx("level_up")
            self.effects.spawn_level_up_burst(self.player.x, self.player.y)
            if self.player.experience.level % 5 == 0:
                self.player.skill_upgrades.pending_points += 1
        if ups > 0:
            self.level_up_text = f"Уровень {self.player.experience.level}!"
            self.level_up_banner = 3.0
            self.screen_flash.trigger((255, 210, 80), 0.35, alpha=130)
            self.camera.add_shake(power=14.0 if ups > 1 else 10.0, duration=0.18)
            if self.player.skill_upgrades.pending_points > 0 and self.state == GameState.PLAYING:
                self._prev_state = GameState.PLAYING
                self.state = GameState.SKILL_UPGRADE
                self.skill_upgrade_selected = 0
        self.player.clamp_resources()
        gold = random.randint(1, 4) + max(0, enemy.area_level // 2)
        fortune = self.player.equipment.legendary_bonus("fortune")
        gold_find = self.player.equipment.bonus("gold_find")
        if fortune > 0:
            gold = int(gold * (1.0 + 0.5 * fortune))
        if gold_find > 0:
            gold = int(gold * (1.0 + gold_find * 0.03))
        if enemy.is_boss:
            gold *= 5
        self.player.inventory.gold += gold
        vamp = self.player.equipment.legendary_bonus("vampiric")
        if vamp > 0:
            heal = self.player.max_hp * 0.08 * vamp
            self.player.stats.hp = min(self.player.max_hp, self.player.stats.hp + heal)
        if enemy in self.enemies:
            self.enemies.remove(enemy)
        alive = sum(1 for e in self.enemies if e.alive)
        if self.encounters.should_spawn_elite(alive):
            self._spawn_encounter_elite()
        self.audio.play_sfx("kill")

    def _on_goblin_hit(self, enemy: EnemyEntity, **_) -> None:
        if not enemy.alive or not enemy.is_treasure_goblin:
            return
        if enemy.goblin_loot_cd > 0:
            return
        enemy.goblin_loot_cd = 0.35
        drops = random.randint(1, 2)
        for _ in range(drops):
            item = self.loot.goblin_drop(enemy)
            if item:
                offset_x = enemy.x + random.uniform(-0.4, 0.4)
                offset_y = enemy.y + random.uniform(-0.4, 0.4)
                self.ground_items.append(GroundItem(offset_x, offset_y, item=item))
        self.audio.play_sfx("pickup")

    def _on_item_dropped(self, ground: GroundItem, **_) -> None:
        self.ground_items.append(ground)

    def _on_bonus_picked(self, label: str = "", bonus_type: str = "", **_) -> None:
        self.toast_message = label
        self.toast_timer = 2.0
        self.floating_texts.append((self.player.x, self.player.y, label, BONUS_COLORS.get(bonus_type, (255, 220, 80)), 1.0))
        self.audio.play_sfx("pickup")

    def _on_legendary_proc(self, kind: str = "", x: float = 0, y: float = 0, damage: float = 0, **_) -> None:
        if kind != "explosive":
            return
        self.effects.spawn_death_explosion(x, y)
        for enemy in self.enemies:
            if not enemy.alive:
                continue
            if math.hypot(enemy.x - x, enemy.y - y) <= 2.0:
                enemy.take_damage(damage)
                if enemy.hp <= 0:
                    enemy.alive = False
                    self.events.emit("enemy_killed", enemy=enemy, killer=self.player)

    def _on_item_picked(self, item=None, manual: bool = False, **_) -> None:
        if item:
            q = item.quality
            name = item.display_name()
            if q in (ItemQuality.RARE, ItemQuality.LEGENDARY, ItemQuality.SET):
                self.audio.play_sfx("rare_loot")
                self.toast_message = f"Подобран: {name}"
                self.toast_timer = 2.5
            else:
                self.audio.play_sfx("pickup")
                self.toast_message = f"Подобран: {name}"
                self.toast_timer = 1.5
            self.floating_texts.append((self.player.x, self.player.y, name, item.color, 1.0))

    def _on_inventory_full(self, **_) -> None:
        self.toast_message = "Инвентарь полон!"
        self.toast_timer = 2.0
        self.audio.play_sfx("ui")

    def _on_skill_cast(self, **_) -> None:
        self.audio.play_sfx("skill")

    def _on_player_died(self, killer=None, **_) -> None:
        if self.player.equipment.has_phoenix_amulet():
            self.player.equipment.consume_phoenix_amulet()
            self.player.stats.hp = self.player.max_hp * 0.5
            self.player.clamp_resources()
            self.toast_message = "Амулет феникса воскресил вас!"
            self.toast_timer = 3.5
            self.floating_texts.append(
                (self.player.x, self.player.y, "ВОСКРЕШЕНИЕ!", (255, 180, 60), 1.0)
            )
            self.audio.play_sfx("level_up")
            return
        if killer is not None and hasattr(killer, "enemy_label"):
            self.death_killer = killer.enemy_label()
        elif killer is not None and hasattr(killer, "name"):
            self.death_killer = killer.name
        else:
            self.death_killer = "Неизвестный враг"
        self.state = GameState.GAME_OVER
        self.audio.play_sfx("death")
        self._autosave()

    def _on_enemy_hit(self, enemy: EnemyEntity | None = None, is_crit: bool = False, **_) -> None:
        power = 10.5 if is_crit else 7.5
        self.camera.add_shake(power=power, duration=0.08 if is_crit else 0.06)
        self.audio.play_sfx("hit")
        if is_crit:
            self.hitstop_timer = max(self.hitstop_timer, 0.05)
            self.screen_flash.trigger((255, 200, 100), 0.07, alpha=55)
        if enemy:
            scale = enemy.draw_scale * (1.35 if enemy.is_boss else 1.0)
            self.effects.spawn_hit_burst(enemy.x, enemy.y, scale=scale * (1.2 if is_crit else 1.0))

    def _on_attack_swung(self, hit_count: int = 0, **_) -> None:
        base_power = 2.8 if hit_count <= 0 else 4.0
        self.camera.add_shake(power=base_power, duration=0.04)
        self.audio.play_sfx("swing" if hit_count <= 0 else "hit")

    def _autosave(self) -> None:
        if not self.player:
            return
        self._save_current_floor_state()
        data = SaveData(
            floor=self.floor,
            kills=self.kills,
            difficulty=self.difficulty.value,
            game_mode=self.game_mode.value,
            arena_round=self.arena_round,
            arena_round_difficulty=self.arena_round_difficulty,
            player_data=self._player_to_dict(),
            floor_states={str(k): v for k, v in self.floor_states.items()},
        )
        self.save_manager.save(data)

    def _player_to_dict(self) -> dict:
        p = self.player
        p.clamp_resources()
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
                "strength": p.stats.strength,
                "dexterity": p.stats.dexterity,
                "vitality": p.stats.vitality,
                "energy": p.stats.energy,
            },
            "inventory": p.inventory.to_dict(),
            "equipment": p.equipment.to_dict(),
            "experience": {
                "level": p.experience.level,
                "xp": p.experience.xp,
                "xp_to_next": p.experience.xp_to_next,
            },
            "skill_tree": p.skill_tree.to_dict(),
            "skill_upgrades": p.skill_upgrades.to_dict(),
            "settings": p.settings.to_dict(),
            "buffs": p.buffs.to_dict(),
            "next_mentor_floor": self.next_mentor_floor,
        }

    def _update(self, dt: float) -> None:
        if self.state == GameState.MERCHANT:
            self.merchant_ui.update(dt)
        if self.level_up_banner > 0:
            self.level_up_banner -= dt
        if self.toast_timer > 0:
            self.toast_timer -= dt
        self.screen_flash.update(dt)
        if self.epic_banner_timer > 0:
            self.epic_banner_timer -= dt
        alive_ft: list[tuple[float, float, str, tuple, float]] = []
        for wx, wy, msg, color, alpha in self.floating_texts:
            alpha -= dt * 1.2
            wy -= dt * 1.5
            if alpha > 0:
                alive_ft.append((wx, wy, msg, color, alpha))
        self.floating_texts = alive_ft

        if self.state not in (GameState.PLAYING, GameState.INVENTORY, GameState.MERCHANT):
            self.input.end_frame()
            return

        if self.state == GameState.PLAYING:
            self._update_playing(dt)

        self.input.end_frame()

    def _update_arena_survival(self, dt: float) -> None:
        if not self.arena_active:
            return
        self.arena_timer -= dt
        self.arena_spawn_cd -= dt
        endless = self.game_mode in (GameMode.ARENA, GameMode.ARENA_BOSSES)
        if self.arena_spawn_cd <= 0:
            if endless:
                self.arena_spawn_cd = max(0.35, 1.0 - self.arena_round * 0.05)
            else:
                self.arena_spawn_cd = max(0.55, 1.1 - self.floor * 0.02)
            self._arena_spawn_wave()
        if self.arena_timer <= 0:
            if endless and self.player.hp > 0:
                self.arena_round += 1
                self.arena_round_difficulty = 1.0 + (self.arena_round - 1) * ARENA_ROUND_DIFFICULTY_STEP
                self.arena_timer = ARENA_ROUND_DURATION
                self.toast_message = f"Раунд {self.arena_round}! Сложность ↑"
                self.toast_timer = 3.0
                self.audio.play_sfx("level_up")
            elif not endless and self.player.hp > 0:
                self.arena_active = False
                self.toast_message = "Арена пройдена! Спуск на следующий этаж…"
                self.toast_timer = 3.0
                self.audio.play_sfx("level_up")
                self._go_floor_down()

    def _update_playing(self, dt: float) -> None:
        p = self.player
        gm = self.game_map
        inp = self.input.state

        if self.hitstop_timer > 0:
            self.hitstop_timer = max(0.0, self.hitstop_timer - dt)
            dt *= 0.12

        if p.hit_flash > 0.12:
            self.kill_streak = 0
            self.kill_streak_timer = 0.0
        elif self.kill_streak_timer > 0:
            self.kill_streak_timer -= dt
            if self.kill_streak_timer <= 0:
                self.kill_streak = 0

        self.movement.update(p, gm, inp, dt)
        p.heal_over_time(dt)
        self.camera.follow(p.x, p.y, dt)
        self.combat.update(dt, p, self.enemies)
        mw = screen_to_world(*inp.mouse_pos, self.camera.x, self.camera.y)
        self.skills.update(dt, p, self.enemies, gm, inp.whirlwind, mw)
        self.effects.update(dt)
        self.effects.tick_ambient(p.x, p.y, dt, boss_floor=(self.floor % 3 == 0))
        self.anim_time += dt

        for enemy in list(self.enemies):
            if enemy.alive:
                self.combat.enemy_attack_player(p, enemy, dt)

        self.ai.update(
            self.enemies, p, gm, dt, self.events,
            protect_target=self.villager if self.villager and self.villager.alive else None,
        )
        if self.villager and self.villager.alive:
            self.villager.update(dt)
        if (
            self.encounters.current.kind == EncounterType.PROTECT_NPC
            and self.villager
            and self.villager.alive
        ):
            self.encounter_wave_cd -= dt
            if self.encounter_wave_cd <= 0:
                self.encounter_wave_cd = random.uniform(10.0, 14.0)
                self._spawn_protect_wave()
        elif self.villager and not self.villager.alive and not self._villager_failed:
            self.player.buffs.add("damage", 12.0, magnitude=-0.5)
            self.toast_message = "Житель погиб! Вы ослаблены."
            self.toast_timer = 3.0
            self._villager_failed = True
            self.villager = None
        self._update_arena_survival(dt)
        for enemy in self.enemies:
            if enemy.alive:
                update_enemy_status(enemy, dt, self.events, p, self.enemies)
        self.bonuses.update(dt, p, self.enemies)

        pieces = p.equipment.count_set_pieces()
        if pieces >= 5:
            self._set_pulse_timer -= dt
            if self._set_pulse_timer <= 0:
                self._set_pulse_timer = 4.0
                self.effects.spawn_aoe_ring(p.x, p.y, 75.0, (0, 220, 200))
                for enemy in self.enemies:
                    if enemy.alive and p.distance_to(enemy) <= 2.5:
                        enemy.take_damage(p.skill_damage_bonus * 0.5 + 10)

        if p.settings.auto_pickup or self.game_mode == GameMode.SPEED:
            self.loot.pickup(p, self.ground_items, auto_pickup=True)
            self.bonuses.try_pickup(p, self.enemies, threshold=1.0)
        self._tick_entity_motions(dt)

        if inp.attack and p.attack_timer <= 0:
            mw = screen_to_world(*inp.mouse_pos, self.camera.x, self.camera.y)
            self.combat.try_attack(p, self.enemies, mw, inp.mouse_pos, self.camera)

        self._update_portal_hint()

        if p.hp <= 0:
            killer = None
            best_dist = 999.0
            for enemy in self.enemies:
                if enemy.alive and p.distance_to(enemy) < best_dist:
                    best_dist = p.distance_to(enemy)
                    killer = enemy
            self.events.emit("player_died", killer=killer)

        if self.kills > 0 and self.kills % 5 == 0 and self.kills != self._last_autosave_kills:
            self._last_autosave_kills = self.kills
            self._autosave()

    def _tick_entity_motions(self, dt: float) -> None:
        tick_motion(self.player, dt)
        if self.player.is_dashing:
            self.player.motion_amount = max(self.player.motion_amount, 0.035)
        for enemy in self.enemies:
            if enemy.alive:
                tick_motion(enemy, dt)
        for minion in self.skills.minions:
            tick_motion(minion, dt)
        for npc in self.npcs:
            tick_motion(npc, dt)
        if self.villager and self.villager.alive:
            tick_motion(self.villager, dt)

    @staticmethod
    def _motion_at(entity, sx: float, sy: float, base_scale: float = 1.0) -> tuple[float, float, float, float]:
        sway, bob, scale, shadow_w = motion_visual(entity.motion_phase, entity.motion_amount, scale=base_scale)
        return sx + sway, sy + bob, scale, shadow_w

    def _update_portal_hint(self) -> None:
        self._portal_hint_cd -= 0.016
        if self._portal_hint_cd > 0:
            self.portal_hint = self._cached_portal_hint
            return
        self._portal_hint_cd = 0.12
        p = self.player
        if self.arena_active:
            if self.game_mode in (GameMode.ARENA, GameMode.ARENA_BOSSES):
                self.portal_hint = f"Раунд {self.arena_round} — {max(0, int(self.arena_timer) + 1)}с"
            else:
                self.portal_hint = f"Выживите! {max(0, int(self.arena_timer) + 1)}с"
            return
        if self.villager and self.villager.alive and p.distance_to(self.villager) < 2.5:
            self.portal_hint = f"Защитите жителя! {int(self.villager.hp)}/{int(self.villager.max_hp)} HP"
            return
        for npc in self.npcs:
            if p.distance_to(npc) < 1.8:
                label = "Наставник — пассивные навыки" if npc.dialog_id == "mentor" else npc.name
                self.portal_hint = f"[E] {label}"
                return
        for pillar in self.pillars:
            if not pillar.used and p.distance_to(pillar) < 1.8:
                self.portal_hint = "[E] Проклятое святилище"
                return
        if self._near_tile(TileType.EXIT):
            self.portal_hint = "[E] Спуститься вниз"
        elif self._near_tile(TileType.STAIRS_UP) and self.floor > 1:
            self.portal_hint = "[E] Подняться назад"
        elif any(g.item and p.distance_sq_to(g.x, g.y) < 1.2 for g in self.ground_items):
            self.portal_hint = "[E] Подобрать предмет"
        else:
            self.portal_hint = None
        self._cached_portal_hint = self.portal_hint

    def _try_portal_transition(self) -> None:
        if self.arena_active or self.game_mode in (GameMode.ARENA, GameMode.ARENA_BOSSES):
            return
        if self._near_tile(TileType.EXIT):
            self._go_floor_down()
        elif self._near_tile(TileType.STAIRS_UP) and self.floor > 1:
            self._go_floor_up()

    def _go_floor_down(self) -> None:
        self._autosave()
        next_floor = self.floor + 1
        self.screen_flash.trigger((70, 90, 160), 0.22, alpha=70)
        self._load_floor(next_floor, spawn_at_start=True, from_above=False)

    def _go_floor_up(self) -> None:
        prev = max(1, self.floor - 1)
        has_state = prev in self.floor_states
        self._load_floor(prev, from_above=True, restore_entities=has_state)

    def _draw(self) -> None:
        self.screen.fill((12, 14, 22))
        if self.state == GameState.MENU:
            self.menu_ui.draw(self.save_manager.exists())
            return
        if self.state == GameState.GAME_OVER:
            self._draw_world()
            self.game_over_ui.draw(
                self.floor, self.player.experience.level, self.kills, killer=self.death_killer,
            )
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
            kill_streak=self.kill_streak,
            kill_streak_timer=self.kill_streak_timer,
        )
        if self.arena_active:
            if self.game_mode in (GameMode.ARENA, GameMode.ARENA_BOSSES):
                self.hud.draw_arena_timer(self.arena_timer, round_num=self.arena_round)
            else:
                self.hud.draw_arena_timer(self.arena_timer)
        if self.state == GameState.INVENTORY:
            self.inventory_ui.draw(self.player, mouse_pos=mouse)
        notify_slot = 1 if self.arena_active else 0
        if self.level_up_banner > 0:
            self.hud.draw_level_up_banner(self.level_up_text, self.level_up_banner, slot=notify_slot)
            notify_slot += 1
        if self.epic_banner_timer > 0:
            self.hud.draw_epic_banner(
                self.epic_banner_text, self.epic_banner_color, self.epic_banner_timer, slot=notify_slot,
            )
        if self.toast_timer > 0:
            self.hud.draw_toast(self.toast_message)
        self.hud.draw_floating_texts(self.floating_texts, self.camera)
        self.screen_flash.draw(self.screen)
        if self.state == GameState.PAUSED:
            self.pause_ui.draw(self.player)
        elif self.state == GameState.SKILLS:
            self.skill_tree_ui.draw(self.player)
        elif self.state == GameState.SKILL_UPGRADE:
            self.skill_upgrade_ui.draw(self.player, self.skill_upgrade_selected)
        elif self.state == GameState.MERCHANT:
            self.merchant_ui.draw(self.player)

    def _draw_world(self) -> None:
        cam = self.camera
        r = self.renderer
        t = self.anim_time

        self._ensure_bg()
        if self._bg_composite:
            self.screen.blit(self._bg_composite, (0, 0))

        self.map_renderer.draw_static(self.screen, self.game_map, cam.x, cam.y)
        self.map_renderer.draw_special_tiles(self.game_map, cam.x, cam.y, t)

        margin = 100
        for g in self.ground_items:
            sx, sy = cam.world_to_screen(g.x, g.y)
            if sx < -margin or sx > SCREEN_WIDTH + margin or sy < -margin or sy > SCREEN_HEIGHT + margin:
                continue
            r.draw_loot_orb(sx, sy, g.color(), t + g.x)

        for bonus in self.bonuses.ground_bonuses:
            sx, sy = cam.world_to_screen(bonus.x, bonus.y)
            if sx < -margin or sx > SCREEN_WIDTH + margin or sy < -margin or sy > SCREEN_HEIGHT + margin:
                continue
            pulse = 0.7 + 0.3 * math.sin(t * 5.0 + bonus.bob_phase)
            col = bonus.color()
            glow_col = tuple(int(c * pulse) for c in col)
            r.draw_loot_orb(sx, sy, glow_col, t + bonus.x)
            r.blit_text_outlined(r.font_label, bonus.label[:6], col, (int(sx) - 20, int(sy) - 28))

        pillar_sprite = self.sprites.pillar
        for pillar in self.pillars:
            sx, sy = cam.world_to_screen(pillar.x, pillar.y)
            pulse = 0.6 + 0.4 * math.sin(t * 3.0 + pillar.x)
            if pillar.used:
                glow = None
                scale = 1.15
            elif pillar.is_buff:
                glow = tuple(int(c * pulse) for c in (80, 200, 255))
                scale = 1.25 + 0.05 * math.sin(t * 2.5)
            else:
                glow = tuple(int(c * pulse) for c in (220, 80, 100))
                scale = 1.25 + 0.05 * math.sin(t * 2.5)
            r.draw_entity_shadow(sx, sy, 18, width_scale=1.1)
            if not r.blit_sprite(pillar_sprite, sx, sy, scale=scale, glow_color=glow):
                col = glow or (60, 60, 70)
                r.draw_loot_orb(sx, sy, col, t + pillar.x)
            if not pillar.used:
                hint_col = glow or (180, 180, 200)
                r.blit_text_outlined(r.font_small, "E", hint_col, (int(sx) - 4, int(sy) - 36))

        for ring in self.effects.rings:
            sx, sy = cam.world_to_screen(ring.x, ring.y)
            rad = int(ring.max_radius * (1.0 - ring.life / ring.max_life))
            fade = ring.life / max(ring.max_life, 0.001)
            r.draw_aoe_ring_world(sx, sy, rad, ring.color, int(90 * fade + 40), width=4)

        for npc in self.npcs:
            sx, sy = cam.world_to_screen(npc.x, npc.y)
            msx, msy, scale, shadow_w = self._motion_at(npc, sx, sy, base_scale=1.0)
            r.draw_entity_shadow(msx, msy, 16, width_scale=shadow_w)
            npc_sprite = self.sprites.get(npc.sprite_name) if npc.sprite_name else self.sprites.npc(npc.dialog_id)
            glow = (180, 140, 255) if npc.dialog_id == "mentor" else (255, 200, 100)
            if not r.blit_sprite(npc_sprite, msx, msy, scale=scale * 1.05, glow_color=glow):
                body = (200, 160, 80) if npc.dialog_id == "smith" else (160, 140, 220)
                r.draw_character_orb(msx, msy, 16 * scale, body, accent=glow)
            name_col = (180, 140, 255) if npc.dialog_id == "mentor" else (255, 220, 140)
            r.blit_text_outlined(r.font_label, npc.name, name_col, (int(msx) - 30, int(msy) - 42))

        if self.villager and self.villager.alive:
            sx, sy = cam.world_to_screen(self.villager.x, self.villager.y)
            msx, msy, scale, shadow_w = self._motion_at(self.villager, sx, sy, base_scale=1.0)
            r.draw_entity_shadow(msx, msy, 16, width_scale=shadow_w)
            villager_sprite = self.sprites.get(self.villager.sprite_name) or self.sprites.npc_villager
            glow = (120, 200, 255)
            if not r.blit_sprite(
                villager_sprite, msx, msy,
                hit_flash=self.villager.hit_flash > 0,
                scale=scale * 1.05,
                glow_color=glow,
            ):
                body = (120, 200, 255) if self.villager.hit_flash <= 0 else (255, 255, 255)
                r.draw_character_orb(msx, msy, 16 * scale, body, accent=(180, 230, 255))
            r.blit_text_outlined_centered(
                r.font_label, self.villager.name, (180, 230, 255), msx,
                r.overhead_y(msy, "ability", scale), outline=(20, 40, 60),
            )
            r.draw_hp_bar_world(
                msx, r.overhead_y(msy, "hp", scale),
                self.villager.hp / max(self.villager.max_hp, 1), width=42,
            )

        for enemy in self.enemies:
            if not enemy.alive:
                continue
            sx, sy = cam.world_to_screen(enemy.x, enemy.y)
            if sx < -margin or sx > SCREEN_WIDTH + margin or sy < -margin or sy > SCREEN_HEIGHT + margin:
                continue
            base_scale = enemy.draw_scale
            msx, msy, scale, shadow_w = self._motion_at(enemy, sx, sy, base_scale)
            r.draw_entity_shadow(msx, msy, 16 * base_scale, width_scale=shadow_w)
            sprite = self.sprites.enemy(
                enemy.sprite_name,
                kind=enemy.kind.name,
                is_boss=enemy.is_boss,
            )
            glow = (255, 80, 60) if enemy.is_boss else (255, 210, 60) if enemy.is_treasure_goblin else (200, 70, 70) if enemy.kind.name == "CASTER" else None
            if not r.blit_sprite(sprite, msx, msy, hit_flash=enemy.hit_flash > 0, scale=scale, glow_color=glow):
                body = (190, 75, 75) if enemy.hit_flash <= 0 else (255, 255, 255)
                if enemy.is_boss:
                    body = (220, 60, 60)
                elif enemy.kind.name == "CASTER":
                    body = (140, 80, 200)
                elif enemy.kind.name == "RUNNER":
                    body = (210, 100, 70)
                r.draw_character_orb(msx, msy, 18 * scale, body, accent=glow, hit_flash=enemy.hit_flash > 0)
            if enemy.shield_timer > 0:
                shield_r = int(22 * base_scale)
                r.draw_aoe_ring_world(msx, msy, shield_r, (100, 180, 255), int(80 + 40 * math.sin(t * 6)), width=2)
            if enemy.casting > 0:
                cast_t = min(1.0, enemy.casting / 0.5)
                cast_r = int(20 * base_scale + 12 * cast_t)
                r.draw_aoe_ring_world(msx, msy, cast_r, (180, 90, 255), int(100 + 80 * cast_t), width=2)
            show_hp = (
                enemy.is_boss
                or enemy.is_floor_elite
                or enemy.is_treasure_goblin
                or enemy.hp < enemy.max_hp * 0.98
                or self.player.distance_to(enemy) < 5.5
            )
            has_tag = enemy.is_boss or enemy.is_floor_elite or enemy.is_treasure_goblin
            show_abilities = bool(
                enemy.special_abilities
                and (enemy.is_boss or enemy.is_floor_elite or self.player.distance_to(enemy) < 5.0)
            )
            if show_hp:
                r.draw_hp_bar_world(
                    msx,
                    r.overhead_y(msy, "hp", base_scale),
                    enemy.hp / max(enemy.max_hp, 1),
                    width=int(38 * base_scale),
                )
            if enemy.is_boss:
                r.blit_text_outlined_centered(
                    r.font_label, "БОСС", (255, 90, 80), msx,
                    r.overhead_y(msy, "tag", base_scale), outline=(60, 10, 10),
                )
            elif enemy.is_floor_elite:
                r.blit_text_outlined_centered(
                    r.font_label, "ЭЛИТ", (255, 180, 60), msx,
                    r.overhead_y(msy, "tag", base_scale), outline=(60, 30, 10),
                )
            elif enemy.is_treasure_goblin:
                r.blit_text_outlined_centered(
                    r.font_label, "ЛУТ", (255, 220, 80), msx,
                    r.overhead_y(msy, "tag", base_scale), outline=(60, 40, 10),
                )
            if show_abilities:
                ab_text = "+".join(enemy.special_abilities[:2])
                ab_layer = "ability" if has_tag else "tag"
                r.blit_text_outlined_centered(
                    r.font_small, ab_text, (180, 160, 255), msx,
                    r.overhead_y(msy, ab_layer, base_scale), outline=(30, 20, 50),
                )

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
            if sx < -margin or sx > SCREEN_WIDTH + margin or sy < -margin or sy > SCREEN_HEIGHT + margin:
                continue
            fade = max(0.0, min(1.0, p.life / max(p.max_life, 0.001)))
            pr, pg, pb = p.color
            col = (int(pr * fade), int(pg * fade), int(pb * fade))
            size = max(1, int(p.size * fade))
            if size > 2:
                glow = pygame.Surface((size * 4, size * 4), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*col, int(80 * fade)), (size * 2, size * 2), size + 2)
                self.screen.blit(glow, glow.get_rect(center=(int(sx), int(sy - 8))))
            pygame.draw.circle(self.screen, col, (int(sx), int(sy - 8)), size)

        for ember in self.effects.ambient:
            sx, sy = cam.world_to_screen(ember.x, ember.y)
            if sx < -margin or sx > SCREEN_WIDTH + margin or sy < -margin or sy > SCREEN_HEIGHT + margin:
                continue
            flicker = 0.55 + 0.45 * math.sin(t * 4.0 + ember.phase)
            er, eg, eb = ember.color
            alpha = int(90 * flicker)
            size = max(1, int(ember.size * flicker))
            glow = pygame.Surface((size * 6, size * 6), pygame.SRCALPHA)
            pygame.draw.circle(glow, (er, eg, eb, alpha), (size * 3, size * 3), size + 2)
            self.screen.blit(glow, glow.get_rect(center=(int(sx), int(sy - 10))))

        for hb in self.effects.hit_bursts:
            sx, sy = cam.world_to_screen(hb.x, hb.y)
            progress = 1.0 - hb.life / max(hb.max_life, 0.001)
            r.draw_hit_burst(sx, sy, self.sprites.hit, progress, base_scale=hb.scale)

        for proj in self.skills.projectiles:
            sx, sy = cam.world_to_screen(proj.x, proj.y)
            fb_scale = proj.radius / 0.22
            r.draw_fireball(sx, sy, t + proj.x, self.sprites.fireball, scale=fb_scale)

        for m in self.skills.minions:
            sx, sy = cam.world_to_screen(m.x, m.y)
            msx, msy, scale, shadow_w = self._motion_at(m, sx, sy)
            r.draw_entity_shadow(msx, msy, 12 * scale, width_scale=shadow_w)
            col = (100, 255, 160) if m.hit_flash <= 0 else (255, 255, 255)
            r.draw_character_orb(msx, msy, 14 * scale, col, accent=(80, 220, 140), hit_flash=m.hit_flash > 0)

        for sx_w, sy_w, val, alpha, is_crit in self.combat.damage_numbers:
            sx, sy = cam.world_to_screen(sx_w, sy_w)
            scale = 1.15 if is_crit else 1.0
            dmg_color = (255, 100, 60) if is_crit else (255, 230, 130)
            outline = (120, 20, 10) if is_crit else (80, 40, 10)
            text = f"{val}!" if is_crit else str(val)
            font = r.font_mid if is_crit else r.font_damage
            dmg_y = r.overhead_y(sy, "damage", scale) - int((1.0 - alpha) * 18)
            r.blit_text_outlined_centered(
                font,
                text,
                dmg_color,
                sx,
                dmg_y,
                outline=outline,
                outline_width=3 if is_crit else 2,
                alpha=int(alpha * 255),
            )

        px, py = cam.world_to_screen(self.player.x, self.player.y)
        mpx, mpy, pscale, pshadow = self._motion_at(self.player, px, py)
        r.draw_entity_shadow(mpx, mpy, 18, width_scale=pshadow)
        if self.player.is_dashing:
            r.draw_dash_trail(mpx, mpy, t)
        if not r.blit_sprite(
            self.player_sprite, mpx, mpy,
            hit_flash=self.player.hit_flash > 0,
            glow_color=(80, 220, 140),
            scale=pscale,
        ):
            r.draw_character_orb(
                mpx, mpy, 18 * pscale, (80, 230, 120),
                accent=(100, 255, 180), hit_flash=self.player.hit_flash > 0,
            )

        for arr in self.combat.arrows:
            sx, sy = cam.world_to_screen(arr.x, arr.y)
            r.draw_fireball(sx, sy, t + arr.x, self.sprites.fireball, scale=0.7)

        if self.input.state.whirlwind and self.state == GameState.PLAYING:
            sx, sy = cam.world_to_screen(self.player.x, self.player.y)
            elem = self.player.equipment.whirlwind_element()
            if elem == "default" and self.player.skill_upgrades.whirlwind_upgraded():
                elem = "fire"
            r.draw_whirlwind(sx, sy, 62, self.skills.whirlwind_angle, element=elem)

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
