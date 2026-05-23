"""A* pathfinding on tile grid."""

from __future__ import annotations

import heapq
from typing import Optional

from world.map import GameMap


def heuristic(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path(game_map: GameMap, start: tuple[int, int], goal: tuple[int, int]) -> list[tuple[int, int]]:
    if not game_map.in_bounds(*start) or not game_map.in_bounds(*goal):
        return []
    if not game_map.is_walkable(*goal):
        return []

    open_set: list[tuple[int, tuple[int, int]]] = [(0, start)]
    came_from: dict[tuple[int, int], tuple[int, int]] = {}
    g_score: dict[tuple[int, int], int] = {start: 0}

    while open_set:
        _, current = heapq.heappop(open_set)
        if current == goal:
            path = [current]
            while current in came_from:
                current = came_from[current]
                path.append(current)
            path.reverse()
            return path

        cx, cy = current
        for nx, ny in game_map.neighbors(cx, cy):
            tentative = g_score[current] + 1
            if tentative < g_score.get((nx, ny), 10**9):
                came_from[(nx, ny)] = current
                g_score[(nx, ny)] = tentative
                f = tentative + heuristic((nx, ny), goal)
                heapq.heappush(open_set, (f, (nx, ny)))
    return []
