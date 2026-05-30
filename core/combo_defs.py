"""Kill-streak tiers and combo callouts."""

from __future__ import annotations

KILL_STREAK_TIERS: list[tuple[int, str, tuple[int, int, int]]] = [
    (3, "СЕРИЯ", (255, 210, 90)),
    (5, "ЖАРКО!", (255, 170, 60)),
    (8, "БЕРСЕРК!", (255, 120, 50)),
    (12, "РЕЗНЯ!", (255, 80, 40)),
    (18, "БЕЗУМИЕ!", (255, 60, 120)),
    (25, "БОГОУБИЙЦА!", (255, 220, 80)),
]


def streak_tier(streak: int) -> tuple[str, tuple[int, int, int]] | None:
    result: tuple[str, tuple[int, int, int]] | None = None
    for threshold, label, color in KILL_STREAK_TIERS:
        if streak >= threshold:
            result = (label, color)
    return result


def streak_milestone(streak: int) -> tuple[int, str, tuple[int, int, int]] | None:
    for threshold, label, color in KILL_STREAK_TIERS:
        if streak == threshold:
            return threshold, label, color
    return None
