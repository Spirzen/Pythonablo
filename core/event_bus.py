"""Simple pub/sub event bus."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, list[Callable[..., None]]] = defaultdict(list)

    def subscribe(self, event: str, callback: Callable[..., None]) -> None:
        if callback not in self._subs[event]:
            self._subs[event].append(callback)

    def unsubscribe(self, event: str, callback: Callable[..., None]) -> None:
        if callback in self._subs[event]:
            self._subs[event].remove(callback)

    def emit(self, event: str, **payload: Any) -> None:
        for cb in list(self._subs[event]):
            cb(**payload)
