"""NPC stub."""

from __future__ import annotations

from dataclasses import dataclass

from entities.entity import Entity


@dataclass
class NPC(Entity):
    name: str = "Странник степи"
    dialog_id: str = "wanderer"
    sprite_name: str = ""
