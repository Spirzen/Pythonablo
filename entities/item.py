"""Ground item entity."""

from __future__ import annotations

from dataclasses import dataclass

from entities.entity import Entity
from player.inventory import Item


@dataclass
class GroundItem(Entity):
    item: Item | None = None

    def color(self) -> tuple[int, int, int]:
        if self.item:
            return self.item.color
        return (200, 200, 200)
