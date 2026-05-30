"""Cached static map layer for fast isometric rendering."""

from __future__ import annotations

import math

import pygame

from core.config import ISO_TILE_H, ISO_TILE_W, MAP_HEIGHT, MAP_WIDTH, SCREEN_HEIGHT, SCREEN_WIDTH, TileType
from engine.renderer import Renderer, world_to_screen
from world.map import GameMap
from world.visual_themes import floor_palette, floor_variation, tile_color


class MapRenderer:
    PAD = 128

    def __init__(self, renderer: Renderer) -> None:
        self.renderer = renderer
        self._layer: pygame.Surface | None = None
        self._map_key: tuple | None = None
        self._origin = (0, 0)

    def invalidate(self) -> None:
        self._layer = None
        self._map_key = None

    def _map_key_for(self, game_map: GameMap) -> tuple:
        return (game_map.floor, game_map.map_type, id(game_map.grid))

    def ensure_layer(self, game_map: GameMap) -> None:
        key = self._map_key_for(game_map)
        if self._layer is not None and self._map_key == key:
            return
        self._build(game_map)
        self._map_key = key

    def _build(self, game_map: GameMap) -> None:
        r = self.renderer
        palette = floor_palette(game_map.floor, game_map.map_type)
        min_sx, min_sy = 10**9, 10**9
        max_sx, max_sy = -10**9, -10**9
        static_tiles: list[tuple[int, int, tuple[int, int, int], bool, int, int]] = []

        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile = game_map.grid[y][x]
                if tile.type == TileType.VOID:
                    continue
                if tile.type in (TileType.START, TileType.EXIT, TileType.STAIRS_UP):
                    continue
                is_wall = tile.type == TileType.WALL
                if tile.type == TileType.FLOOR:
                    color = floor_variation(x, y, palette)
                else:
                    color = palette["wall"]
                sx, sy = world_to_screen(x, y, 0, 0)
                static_tiles.append((int(sx), int(sy), color, is_wall, x, y))
                min_sx = min(min_sx, sx - ISO_TILE_W)
                max_sx = max(max_sx, sx + ISO_TILE_W)
                min_sy = min(min_sy, sy - ISO_TILE_H)
                max_sy = max(max_sy, sy + ISO_TILE_H * 2)

        w = int(max_sx - min_sx) + self.PAD * 2
        h = int(max_sy - min_sy) + self.PAD * 2
        layer = pygame.Surface((max(w, SCREEN_WIDTH), max(h, SCREEN_HEIGHT)), pygame.SRCALPHA)
        ox = self.PAD - int(min_sx)
        oy = self.PAD - int(min_sy)
        self._origin = (ox, oy)

        static_tiles.sort(key=lambda t: t[0] + t[1])
        for sx, sy, color, is_wall, tx, ty in static_tiles:
            tx_pos = sx + ox
            ty_pos = sy + oy
            surf = r.get_iso_tile_surface(color, is_wall=is_wall, seed=tx * 17 + ty * 31)
            layer.blit(surf, surf.get_rect(center=(tx_pos, ty_pos)))

        self._layer = layer

    def draw_static(self, screen: pygame.Surface, game_map: GameMap, cam_x: float, cam_y: float) -> None:
        self.ensure_layer(game_map)
        if self._layer is None:
            return
        ox, oy = self._origin
        blit_x = int(-cam_x - ox)
        blit_y = int(-cam_y - oy)
        screen.blit(self._layer, (blit_x, blit_y))

    def draw_special_tiles(
        self,
        game_map: GameMap,
        cam_x: float,
        cam_y: float,
        anim_time: float,
    ) -> None:
        r = self.renderer
        margin = 80
        for y in range(MAP_HEIGHT):
            for x in range(MAP_WIDTH):
                tile = game_map.grid[y][x]
                if tile.type not in (TileType.START, TileType.EXIT, TileType.STAIRS_UP):
                    continue
                sx, sy = world_to_screen(x, y, cam_x, cam_y)
                if sx < -margin or sx > SCREEN_WIDTH + margin or sy < -margin or sy > SCREEN_HEIGHT + margin:
                    continue
                color = tile_color(tile.type, game_map.floor, game_map.map_type)
                pulse = 0.5 + 0.5 * math.sin(anim_time * 2.8 + x)
                accent = None
                if tile.type == TileType.START:
                    accent = (90, 210, 120)
                elif tile.type == TileType.EXIT:
                    pulse = 0.5 + 0.5 * math.sin(anim_time * 3.0 + y)
                    accent = (255, 160, 80)
                elif tile.type == TileType.STAIRS_UP:
                    pulse = 0.5 + 0.5 * math.sin(anim_time * 2.8)
                    accent = (140, 180, 255)
                r.draw_iso_tile(x, y, cam_x, cam_y, color, pulse=pulse, accent=accent)
