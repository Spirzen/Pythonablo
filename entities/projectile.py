"""Projectile stub for future ranged enemies."""

from __future__ import annotations

from dataclasses import dataclass

from entities.entity import Entity


@dataclass
class ProjectileEntity(Entity):
    vx: float = 0.0
    vy: float = 0.0
    damage: float = 5.0
    life: float = 2.0
    from_enemy: bool = False
