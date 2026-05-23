"""Skill tree stub for future expansion."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SkillNode:
    id: str
    name: str
    description: str
    cost: int = 1
    unlocked: bool = False


@dataclass
class SkillTree:
    points: int = 0
    nodes: dict[str, SkillNode] = field(default_factory=dict)

    def unlock(self, node_id: str) -> bool:
        node = self.nodes.get(node_id)
        if not node or node.unlocked or self.points < node.cost:
            return False
        self.points -= node.cost
        node.unlocked = True
        return True
