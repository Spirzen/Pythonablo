"""Visual effects: death explosions, AOE rings."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


@dataclass
class Particle:
    x: float
    y: float
    vx: float
    vy: float
    life: float
    max_life: float
    size: float
    color: tuple[int, int, int]
    circle: bool = True


@dataclass
class Explosion:
    x: float
    y: float
    life: float = 0.45
    max_life: float = 0.45
    max_radius: float = 42.0
    color: tuple[int, int, int] = (255, 120, 60)

    @property
    def progress(self) -> float:
        return 1.0 - self.life / max(self.max_life, 0.001)

    @property
    def radius(self) -> float:
        return self.max_radius * min(1.0, self.progress * 1.15)


@dataclass
class SpriteBurst:
    x: float
    y: float
    life: float = 0.22
    max_life: float = 0.22
    scale: float = 1.0


@dataclass
class AmbientEmber:
    x: float
    y: float
    vy: float
    phase: float
    size: float
    color: tuple[int, int, int]


class EffectSystem:
    MAX_PARTICLES = 180
    MAX_EXPLOSIONS = 24
    MAX_AMBIENT = 28

    def __init__(self) -> None:
        self.explosions: list[Explosion] = []
        self.rings: list[AoERing] = []
        self.particles: list[Particle] = []
        self.hit_bursts: list[SpriteBurst] = []
        self.ambient: list[AmbientEmber] = []
        self.rng = random.Random()

    def spawn_death_explosion(self, x: float, y: float, *, big: bool = False) -> None:
        if len(self.explosions) >= self.MAX_EXPLOSIONS:
            self.explosions = self.explosions[-self.MAX_EXPLOSIONS // 2 :]
        self.explosions.append(
            Explosion(
                x,
                y,
                life=0.75 if big else 0.6,
                max_life=0.75 if big else 0.6,
                max_radius=110.0 if big else 72.0,
                color=(255, 30, 20) if big else (255, 45, 30),
            )
        )
        # Inner flash
        self.explosions.append(
            Explosion(
                x,
                y,
                life=0.35 if big else 0.28,
                max_life=0.35 if big else 0.28,
                max_radius=(60.0 if big else 42.0),
                color=(255, 120, 80),
            )
        )
        count = 42 if big else 28
        if len(self.particles) + count > self.MAX_PARTICLES:
            count = max(8, self.MAX_PARTICLES - len(self.particles))
        red_palette = [
            (255, 70, 35),
            (255, 110, 50),
            (210, 45, 25),
            (255, 150, 70),
            (180, 30, 15),
            (255, 190, 90),
        ]
        for _ in range(count):
            angle = self.rng.random() * math.tau
            speed = 120 + self.rng.random() * (320 if big else 220)
            streak = self.rng.random() < 0.35
            self.particles.append(
                Particle(
                    x,
                    y,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed,
                    life=0.45 + self.rng.random() * 0.45,
                    max_life=0.7,
                    size=5 + self.rng.random() * (9 if big else 6),
                    color=self.rng.choice(red_palette),
                    circle=not streak,
                )
            )

    def spawn_hit_burst(self, x: float, y: float, *, scale: float = 1.0) -> None:
        self.hit_bursts.append(SpriteBurst(x, y, scale=scale))

    def spawn_xp_sparkles(self, x: float, y: float, *, amount: int = 12) -> None:
        gold_palette = [
            (255, 220, 80),
            (255, 200, 60),
            (255, 180, 40),
            (255, 240, 140),
            (220, 180, 50),
        ]
        count = min(amount, max(4, self.MAX_PARTICLES - len(self.particles)))
        for _ in range(count):
            angle = self.rng.random() * math.tau
            speed = 40 + self.rng.random() * 100
            self.particles.append(
                Particle(
                    x,
                    y - 0.15,
                    math.cos(angle) * speed,
                    math.sin(angle) * speed - 30,
                    life=0.55 + self.rng.random() * 0.35,
                    max_life=0.7,
                    size=3 + self.rng.random() * 4,
                    color=self.rng.choice(gold_palette),
                )
            )

    def spawn_level_up_burst(self, x: float, y: float) -> None:
        self.spawn_xp_sparkles(x, y, amount=28)
        if len(self.explosions) < self.MAX_EXPLOSIONS:
            self.explosions.append(
                Explosion(x, y, life=0.55, max_life=0.55, max_radius=90.0, color=(255, 210, 80))
            )
            self.explosions.append(
                Explosion(x, y, life=0.35, max_life=0.35, max_radius=50.0, color=(255, 240, 160))
            )

    def spawn_aoe_ring(self, x: float, y: float, radius: float, color: tuple[int, int, int] = (255, 200, 100)) -> None:
        self.rings.append(AoERing(x, y, life=0.35, max_life=0.35, max_radius=radius, color=color))

    def tick_ambient(self, center_x: float, center_y: float, dt: float, *, boss_floor: bool = False) -> None:
        target = self.MAX_AMBIENT if boss_floor else 18
        while len(self.ambient) < target:
            self.ambient.append(
                AmbientEmber(
                    center_x + self.rng.uniform(-7.0, 7.0),
                    center_y + self.rng.uniform(-5.0, 5.0),
                    vy=-12.0 - self.rng.random() * 18.0,
                    phase=self.rng.random() * math.tau,
                    size=1.5 + self.rng.random() * 2.5,
                    color=self.rng.choice(
                        [(255, 90, 40), (255, 60, 30), (200, 50, 25)]
                        if boss_floor
                        else [(255, 170, 70), (210, 130, 60), (180, 100, 50), (218, 175, 55)]
                    ),
                )
            )
        alive: list[AmbientEmber] = []
        for ember in self.ambient:
            ember.y += ember.vy * dt
            ember.x += math.sin(ember.phase + ember.y * 0.4) * 8.0 * dt
            if math.hypot(ember.x - center_x, ember.y - center_y) < 9.0:
                alive.append(ember)
        self.ambient = alive

    def update(self, dt: float) -> None:
        for e in self.explosions:
            e.life -= dt
        self.explosions = [e for e in self.explosions if e.life > 0]
        for ring in self.rings:
            ring.life -= dt
        self.rings = [r for r in self.rings if r.life > 0]
        alive: list[Particle] = []
        for p in self.particles:
            p.life -= dt
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vx *= 0.90
            p.vy *= 0.90
            if p.life > 0:
                alive.append(p)
        self.particles = alive
        for hb in self.hit_bursts:
            hb.life -= dt
        self.hit_bursts = [h for h in self.hit_bursts if h.life > 0]


@dataclass
class AoERing:
    x: float
    y: float
    life: float
    max_life: float
    max_radius: float
    color: tuple[int, int, int] = (255, 180, 80)
