"""Camera following the player with shake."""

from __future__ import annotations

import random

from engine.renderer import world_to_screen


class Camera:
    def __init__(self) -> None:
        self.x = 0.0
        self.y = 0.0
        self.smooth = 8.0
        self.shake_timer = 0.0
        self.shake_power = 0.0
        self.shake_offset_x = 0.0
        self.shake_offset_y = 0.0

    def follow(self, target_x: float, target_y: float, dt: float) -> None:
        from core.config import ISO_TILE_H, ISO_TILE_W

        tx = (target_x - target_y) * (ISO_TILE_W / 2)
        ty = (target_x + target_y) * (ISO_TILE_H / 2)
        t = min(1.0, self.smooth * dt)
        self.x += (tx - self.x) * t
        self.y += (ty - self.y) * t
        self._update_shake(dt)

    def add_shake(self, power: float = 6.0, duration: float = 0.08) -> None:
        self.shake_timer = max(self.shake_timer, duration)
        self.shake_power = max(self.shake_power, power)

    def _update_shake(self, dt: float) -> None:
        if self.shake_timer <= 0:
            self.shake_offset_x = 0.0
            self.shake_offset_y = 0.0
            self.shake_power = 0.0
            return
        self.shake_timer -= dt
        self.shake_power *= 0.88
        self.shake_offset_x = random.uniform(-self.shake_power, self.shake_power)
        self.shake_offset_y = random.uniform(-self.shake_power, self.shake_power)

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        sx, sy = world_to_screen(wx, wy, self.x, self.y)
        return sx + self.shake_offset_x, sy + self.shake_offset_y
