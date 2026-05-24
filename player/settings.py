"""Player game settings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GameSettings:
    auto_pickup: bool = False

    def to_dict(self) -> dict:
        return {"auto_pickup": self.auto_pickup}

    @classmethod
    def from_dict(cls, data: dict | None) -> "GameSettings":
        if not data:
            return cls()
        return cls(auto_pickup=bool(data.get("auto_pickup", False)))
