"""Movement and collision."""

from __future__ import annotations

import math

from core.config import DASH_COOLDOWN, DASH_DURATION, DASH_SPEED_MULTIPLIER
from entities.player import PlayerEntity
from engine.input_handler import InputState
from world.collision import move_slide
from world.map import GameMap


class MovementSystem:
    def update(self, player: PlayerEntity, game_map: GameMap, inp: InputState, dt: float) -> None:
        if player.is_dashing:
            player.dash_timer -= dt
            if player.dash_timer <= 0:
                player.is_dashing = False
        else:
            player.dash_cooldown_timer = max(0.0, player.dash_cooldown_timer - dt)

        if player.hit_flash > 0:
            player.hit_flash -= dt

        if not player.is_dashing:
            dx = dy = 0.0
            if inp.up:
                dy -= 1
            if inp.down:
                dy += 1
            if inp.left:
                dx -= 1
            if inp.right:
                dx += 1
            if dx or dy:
                length = math.hypot(dx, dy)
                speed = player.move_speed * dt * 0.012
                mx = (dx / length) * speed
                my = (dy / length) * speed
                player.x, player.y = move_slide(game_map, player.x, player.y, mx, my)
                player.facing_angle = math.atan2(dy, dx)

    def try_dash(self, player: PlayerEntity, game_map: GameMap, inp: InputState) -> bool:
        if player.is_dashing or player.dash_cooldown_timer > 0:
            return False
        dx = dy = 0.0
        if inp.up:
            dy -= 1
        if inp.down:
            dy += 1
        if inp.left:
            dx -= 1
        if inp.right:
            dx += 1
        if dx == 0 and dy == 0:
            dy = -1
        length = math.hypot(dx, dy)
        if length == 0:
            return False

        dash_dist = player.move_speed * DASH_SPEED_MULTIPLIER * DASH_DURATION * 0.012
        mx = (dx / length) * dash_dist
        my = (dy / length) * dash_dist
        player.x, player.y = move_slide(game_map, player.x, player.y, mx, my)
        player.is_dashing = True
        player.dash_timer = DASH_DURATION
        player.dash_cooldown_timer = DASH_COOLDOWN
        player.facing_angle = math.atan2(dy, dx)
        return True
