"""Audio stub — can be extended with pygame.mixer."""

from __future__ import annotations


class AudioSystem:
    def __init__(self) -> None:
        self.enabled = False
        try:
            import pygame.mixer

            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.enabled = True
        except Exception:
            self.enabled = False

    def play_sfx(self, name: str) -> None:
        pass

    def play_music(self, name: str) -> None:
        pass
