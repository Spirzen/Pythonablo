"""Experience and leveling."""

from __future__ import annotations

from dataclasses import dataclass

from core.config import XP_BASE, XP_EARLY_CAP, XP_EARLY_STEP, XP_LEVEL_ADD, XP_LEVEL_MULT


@dataclass
class Experience:
    level: int = 1
    xp: int = 0
    xp_to_next: int = XP_BASE

    @staticmethod
    def _next_threshold(current: int, new_level: int) -> int:
        base = int(current * XP_LEVEL_MULT + XP_LEVEL_ADD)
        if new_level < XP_EARLY_CAP:
            base = int(base * (1.0 + (XP_EARLY_CAP - new_level) * XP_EARLY_STEP))
        return max(base, current + 4)

    def add_xp(self, amount: int) -> int:
        """Returns number of level-ups."""
        self.xp += amount
        ups = 0
        while self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next = self._next_threshold(self.xp_to_next, self.level)
            ups += 1
        return ups
