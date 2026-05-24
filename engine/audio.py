"""Audio — procedural SFX and music via pygame.mixer."""

from __future__ import annotations

import array
import math
from typing import Callable

import pygame


def _sine_wave(freq: float, duration: float, volume: float = 0.25, sample_rate: int = 22050) -> pygame.mixer.Sound:
    n = int(sample_rate * duration)
    buf = array.array("h")
    for i in range(n):
        t = i / sample_rate
        fade = min(1.0, i / (sample_rate * 0.01), (n - i) / (sample_rate * 0.04))
        val = int(32767 * volume * fade * math.sin(2 * math.pi * freq * t))
        buf.append(val)
    return pygame.mixer.Sound(buffer=buf)


def _noise_burst(duration: float, volume: float = 0.15, sample_rate: int = 22050) -> pygame.mixer.Sound:
    import random

    n = int(sample_rate * duration)
    buf = array.array("h")
    for i in range(n):
        fade = 1.0 - i / n
        val = int(32767 * volume * fade * (random.random() * 2 - 1))
        buf.append(val)
    return pygame.mixer.Sound(buffer=buf)


class AudioSystem:
    SFX_NAMES = (
        "hit", "swing", "kill", "pickup", "rare_loot", "level_up",
        "skill", "floor", "menu", "death", "gold", "ui",
    )

    def __init__(self) -> None:
        self.enabled = False
        self._sfx: dict[str, pygame.mixer.Sound] = {}
        self._music_playing: str | None = None
        self._volume = 0.6
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.enabled = True
            self._build_sfx()
        except Exception:
            self.enabled = False

    def _build_sfx(self) -> None:
        builders: dict[str, Callable[[], pygame.mixer.Sound]] = {
            "hit": lambda: _noise_burst(0.06, 0.2),
            "swing": lambda: _sine_wave(180, 0.07, 0.12),
            "kill": lambda: _sine_wave(90, 0.15, 0.2),
            "pickup": lambda: _sine_wave(520, 0.08, 0.15),
            "rare_loot": lambda: _sine_wave(660, 0.12, 0.22),
            "level_up": lambda: _sine_wave(440, 0.25, 0.25),
            "skill": lambda: _sine_wave(280, 0.14, 0.18),
            "floor": lambda: _sine_wave(120, 0.3, 0.2),
            "menu": lambda: _sine_wave(330, 0.06, 0.1),
            "death": lambda: _sine_wave(60, 0.5, 0.3),
            "gold": lambda: _sine_wave(880, 0.06, 0.12),
            "ui": lambda: _sine_wave(400, 0.04, 0.08),
        }
        for name, fn in builders.items():
            try:
                self._sfx[name] = fn()
            except Exception:
                pass

    def play_sfx(self, name: str) -> None:
        if not self.enabled:
            return
        snd = self._sfx.get(name)
        if snd:
            snd.set_volume(self._volume)
            snd.play()

    def play_music(self, name: str) -> None:
        if not self.enabled:
            return
        if self._music_playing == name:
            return
        self.stop_music()
        self._music_playing = name
        try:
            freq = {"menu": 55, "dungeon": 45, "boss": 38}.get(name, 45)
            snd = self._make_drone(freq)
            snd.set_volume(self._volume * 0.35)
            snd.play(-1)
            self._sfx[f"_music_{name}"] = snd
        except Exception:
            self._music_playing = None

    def stop_music(self) -> None:
        if self._music_playing and self.enabled:
            key = f"_music_{self._music_playing}"
            snd = self._sfx.get(key)
            if snd:
                snd.stop()
        self._music_playing = None

    def _make_drone(self, freq: float) -> pygame.mixer.Sound:
        sample_rate = 22050
        duration = 4.0
        n = int(sample_rate * duration)
        buf = array.array("h")
        for i in range(n):
            t = i / sample_rate
            v = 0.12 * math.sin(2 * math.pi * freq * t)
            v += 0.06 * math.sin(2 * math.pi * freq * 1.5 * t + 0.3)
            v *= 0.5 + 0.5 * math.sin(2 * math.pi * 0.08 * t)
            buf.append(int(32767 * v))
        return pygame.mixer.Sound(buffer=buf)
