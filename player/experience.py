"""Experience and leveling."""

from __future__ import annotations

from dataclasses import dataclass

from core.config import XP_BASE, XP_LEVEL_MULT


@dataclass
class Experience:
    level: int = 1
    xp: int = 0
    xp_to_next: int = XP_BASE

    def add_xp(self, amount: int) -> int:
        """Returns number of level-ups."""
        self.xp += amount
        ups = 0
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = int(self.xp_to_next * XP_LEVEL_MULT + 4)
            ups += 1
        return ups
