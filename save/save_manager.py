"""Save / load game state."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from core.config import SAVE_DIR


@dataclass
class SaveData:
    floor: int = 1
    kills: int = 0
    player_data: dict[str, Any] = field(default_factory=dict)
    floors_visited: list[int] = field(default_factory=list)


class SaveManager:
    def __init__(self) -> None:
        SAVE_DIR.mkdir(parents=True, exist_ok=True)
        self.path = SAVE_DIR / "save.json"

    def exists(self) -> bool:
        return self.path.exists()

    def save(self, data: SaveData) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "floor": data.floor,
                    "kills": data.kills,
                    "player": data.player_data,
                    "floors_visited": data.floors_visited,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

    def load(self) -> SaveData | None:
        if not self.path.exists():
            return None
        try:
            with open(self.path, encoding="utf-8") as f:
                raw = json.load(f)
            return SaveData(
                floor=raw.get("floor", 1),
                kills=raw.get("kills", 0),
                player_data=raw.get("player", {}),
                floors_visited=raw.get("floors_visited", []),
            )
        except (OSError, json.JSONDecodeError):
            return None

    def delete(self) -> None:
        if self.path.exists():
            self.path.unlink()
