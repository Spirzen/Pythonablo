"""Full-screen color flash for impact moments."""

from __future__ import annotations

import pygame


class ScreenFlash:
    def __init__(self) -> None:
        self.timer = 0.0
        self.duration = 0.0
        self.color = (255, 255, 255)
        self.max_alpha = 180
        self._scratch: pygame.Surface | None = None

    def trigger(
        self,
        color: tuple[int, int, int],
        duration: float = 0.25,
        *,
        alpha: int = 180,
    ) -> None:
        self.color = color
        self.duration = max(duration, 0.001)
        self.timer = duration
        self.max_alpha = alpha

    def update(self, dt: float) -> None:
        if self.timer > 0:
            self.timer = max(0.0, self.timer - dt)

    @property
    def active(self) -> bool:
        return self.timer > 0

    def draw(self, screen: pygame.Surface) -> None:
        if self.timer <= 0:
            return
        w, h = screen.get_size()
        if self._scratch is None or self._scratch.get_size() != (w, h):
            self._scratch = pygame.Surface((w, h), pygame.SRCALPHA)
        t = self.timer / self.duration
        alpha = int(self.max_alpha * t * t)
        self._scratch.fill((*self.color, alpha))
        screen.blit(self._scratch, (0, 0))
