"""Base entity."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import uuid


@dataclass
class Entity:
    x: float
    y: float
    radius: float = 0.4
    alive: bool = True
    uid: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    components: dict[str, Any] = field(default_factory=dict)

    def tile_pos(self) -> tuple[int, int]:
        return int(self.x), int(self.y)

    def distance_to(self, other: "Entity") -> float:
        import math

        return math.hypot(self.x - other.x, self.y - other.y)

    def distance_sq_to(self, ox: float, oy: float) -> float:
        dx, dy = self.x - ox, self.y - oy
        return dx * dx + dy * dy
