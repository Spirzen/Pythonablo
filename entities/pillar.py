"""Interactive pillars — random buff or debuff."""

from __future__ import annotations

from dataclasses import dataclass

from entities.entity import Entity


@dataclass
class Pillar(Entity):
    pillar_id: str = "p0"
    used: bool = False
    effect_id: str = ""
    is_buff: bool = True
    label: str = ""
