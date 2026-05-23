"""Input handling."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class InputState:
    up: bool = False
    down: bool = False
    left: bool = False
    right: bool = False
    attack: bool = False
    attack_pressed: bool = False
    whirlwind: bool = False
    dash_pressed: bool = False
    inventory_pressed: bool = False
    interact_pressed: bool = False
    skill_pressed: str | None = None
    mouse_pos: tuple[int, int] = (0, 0)
    menu_up: bool = False
    menu_down: bool = False
    menu_confirm: bool = False
    menu_back: bool = False
    menu_left: bool = False
    menu_right: bool = False

    def clear_frame(self) -> None:
        self.attack_pressed = False
        self.dash_pressed = False
        self.inventory_pressed = False
        self.interact_pressed = False
        self.skill_pressed = None
        self.menu_up = False
        self.menu_down = False
        self.menu_confirm = False
        self.menu_back = False
        self.menu_left = False
        self.menu_right = False


class InputHandler:
    def __init__(self) -> None:
        self.state = InputState()

    def on_key_down(self, key: int) -> None:
        import pygame

        if key in (pygame.K_w, pygame.K_UP):
            self.state.up = True
        if key in (pygame.K_s, pygame.K_DOWN):
            self.state.down = True
        if key in (pygame.K_a, pygame.K_LEFT):
            self.state.left = True
        if key in (pygame.K_d, pygame.K_RIGHT):
            self.state.right = True
        if key == pygame.K_SPACE:
            self.state.dash_pressed = True
        if key == pygame.K_i:
            self.state.inventory_pressed = True
        if key == pygame.K_e:
            self.state.interact_pressed = True
        if key == pygame.K_RETURN:
            self.state.menu_confirm = True
        if key == pygame.K_ESCAPE:
            self.state.menu_back = True
        if key == pygame.K_LEFT:
            self.state.menu_left = True
        if key == pygame.K_RIGHT:
            self.state.menu_right = True
        if key in (pygame.K_UP, pygame.K_w):
            self.state.menu_up = True
        if key in (pygame.K_DOWN, pygame.K_s):
            self.state.menu_down = True
        if key == pygame.K_1:
            self.state.skill_pressed = "aoe"
        if key == pygame.K_2:
            self.state.skill_pressed = "fireball"
        if key == pygame.K_3:
            self.state.skill_pressed = "summon"
        if key == pygame.K_4:
            self.state.skill_pressed = "pulse"

    def on_key_up(self, key: int) -> None:
        import pygame

        if key in (pygame.K_w, pygame.K_UP):
            self.state.up = False
        if key in (pygame.K_s, pygame.K_DOWN):
            self.state.down = False
        if key in (pygame.K_a, pygame.K_LEFT):
            self.state.left = False
        if key in (pygame.K_d, pygame.K_RIGHT):
            self.state.right = False

    def on_mouse_down(self, button: int, pos: tuple[int, int]) -> None:
        if button == 1:
            self.state.attack = True
            self.state.attack_pressed = True
        if button == 3:
            self.state.whirlwind = True
        self.state.mouse_pos = pos

    def on_mouse_up(self, button: int) -> None:
        if button == 1:
            self.state.attack = False
        if button == 3:
            self.state.whirlwind = False

    def on_mouse_move(self, pos: tuple[int, int]) -> None:
        self.state.mouse_pos = pos

    def end_frame(self) -> None:
        self.state.clear_frame()
