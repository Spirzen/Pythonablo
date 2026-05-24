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
    difficulty: str = "normal"
    game_mode: str = "classic"
    arena_round: int = 1
    arena_round_difficulty: float = 1.0
    player_data: dict[str, Any] = field(default_factory=dict)
    floor_states: dict[str, Any] = field(default_factory=dict)


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
                    "difficulty": data.difficulty,
                    "game_mode": data.game_mode,
                    "arena_round": data.arena_round,
                    "arena_round_difficulty": data.arena_round_difficulty,
                    "player": data.player_data,
                    "floor_states": data.floor_states,
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
                difficulty=raw.get("difficulty", "normal"),
                game_mode=raw.get("game_mode", "classic"),
                arena_round=raw.get("arena_round", 1),
                arena_round_difficulty=raw.get("arena_round_difficulty", 1.0),
                player_data=raw.get("player", {}),
                floor_states=raw.get("floor_states", raw.get("floors_visited", {})),
            )
        except (OSError, json.JSONDecodeError):
            return None

    def delete(self) -> None:
        if self.path.exists():
            self.path.unlink()
