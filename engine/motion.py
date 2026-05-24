"""Procedural walk / idle motion for characters."""

from __future__ import annotations

import math


def tick_motion(entity, dt: float) -> None:
    """Advance bob phase from world-space movement since last tick."""
    last_x = getattr(entity, "_motion_last_x", entity.x)
    last_y = getattr(entity, "_motion_last_y", entity.y)
    dx = entity.x - last_x
    dy = entity.y - last_y
    dist = math.hypot(dx, dy)

    smooth = getattr(entity, "_motion_smooth", 0.0)
    smooth = smooth * 0.82 + dist * 0.18
    entity._motion_smooth = smooth
    entity.motion_amount = smooth

    if smooth > 0.004:
        speed_factor = min(1.0, smooth / max(dt, 1e-5) * 0.025)
        entity.motion_phase += dt * (3.5 + speed_factor * 4.0)
    else:
        entity.motion_amount = 0.0
        entity.motion_phase += dt * 1.2

    entity._motion_last_x = entity.x
    entity._motion_last_y = entity.y


def motion_visual(phase: float, amount: float, *, scale: float = 1.0) -> tuple[float, float, float, float]:
    """Return screen sway, bob (up), draw scale, shadow width scale."""
    if amount <= 0.004:
        idle_bob = math.sin(phase * math.tau) * 0.9
        idle_squish = 1.0 + math.sin(phase * math.tau) * 0.012
        return 0.0, idle_bob, scale * idle_squish, 1.0

    intensity = min(1.0, amount * 14.0)
    sway = math.sin(phase * math.tau) * (0.6 + 0.9 * intensity)
    bob = abs(math.sin(phase * math.tau)) * (1.2 + 1.6 * intensity)
    squish = 1.0 + math.sin(phase * math.tau) * 0.018 * intensity
    shadow = 1.0 - abs(math.sin(phase * math.tau)) * 0.07 * intensity
    return sway, -bob, scale * squish, shadow
