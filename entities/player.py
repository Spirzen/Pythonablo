"""Player entity."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from core.config import ATTACK_COOLDOWN, DASH_COOLDOWN, DASH_DURATION, PLAYER_SPEED
from entities.entity import Entity
from player.buffs import BuffManager
from player.equipment import Equipment
from player.experience import Experience
from player.inventory import Inventory
from player.settings import GameSettings
from player.skill_tree import SkillTree
from player.skill_upgrades import SkillUpgrades
from player.stats import Stats


@dataclass
class PlayerEntity(Entity):
    stats: Stats = field(default_factory=Stats)
    inventory: Inventory = field(default_factory=Inventory)
    equipment: Equipment = field(default_factory=Equipment)
    experience: Experience = field(default_factory=Experience)
    skill_tree: SkillTree = field(default_factory=SkillTree)
    skill_upgrades: SkillUpgrades = field(default_factory=SkillUpgrades)
    buffs: BuffManager = field(default_factory=BuffManager)
    settings: GameSettings = field(default_factory=GameSettings)
    mode_speed_mult: float = 1.0
    move_speed: float = PLAYER_SPEED
    attack_cooldown: float = ATTACK_COOLDOWN
    attack_timer: float = 0.0
    facing_angle: float = 0.0
    is_dashing: bool = False
    dash_timer: float = 0.0
    dash_cooldown_timer: float = 0.0
    hit_flash: float = 0.0
    pending_thorns_damage: float = 0.0

    def attr(self, name: str) -> int:
        base = getattr(self.stats, name, 0)
        return int(base + self.equipment.bonus(name))

    @property
    def max_hp(self) -> float:
        vit_bonus = self.attr("vitality") * 3.0
        ward = self.equipment.legendary_bonus("ward")
        base = (
            self.stats.max_hp
            + self.equipment.bonus("max_hp")
            + vit_bonus
            + ward * (4 + self.experience.level * 1.5)
        )
        return base * self.skill_tree.hp_mult()

    @property
    def max_mana(self) -> float:
        en_bonus = self.attr("energy") * 2.0
        base = self.stats.max_mana + self.equipment.bonus("max_mana") + en_bonus
        return base * self.skill_tree.mana_mult()

    @property
    def hp(self) -> float:
        return self.stats.hp

    @hp.setter
    def hp(self, value: float) -> None:
        self.stats.hp = value

    @property
    def mana(self) -> float:
        return self.stats.mana

    @property
    def damage(self) -> float:
        str_bonus = self.attr("strength") * 0.5
        base = self.stats.damage + self.equipment.bonus("damage") + str_bonus
        fury = self.equipment.legendary_bonus("fury")
        return base * self.skill_tree.damage_mult() * self.buffs.damage_mult() * (1.0 + fury * 0.12)

    @property
    def armor(self) -> float:
        str_bonus = self.attr("strength") * 0.1
        return (
            self.stats.armor
            + self.equipment.bonus("armor")
            + str_bonus
            + self.buffs.armor_bonus()
        ) * self.skill_tree.armor_mult()

    @property
    def effective_move_speed(self) -> float:
        base = self.move_speed * self.buffs.speed_mult() * self.skill_tree.move_speed_mult() * self.mode_speed_mult
        swift = self.equipment.legendary_bonus("swift")
        move_bonus = self.equipment.bonus("move_speed") * 0.012
        return base * (1.0 + swift * 0.15 + move_bonus)

    @property
    def attack_speed_mult(self) -> float:
        """Used for whirlwind rotation and scales with dexterity + passives."""
        dex = self.attr("dexterity") * 0.012
        cry = 0.18 if self.buffs.has("battle_cry") else 0.0
        return self.skill_tree.attack_speed_mult() * (1.0 + dex + cry)

    @property
    def effective_attack_cooldown(self) -> float:
        dex = self.attr("dexterity")
        reduction = min(0.35, dex * 0.008)
        cd = self.attack_cooldown * (1.0 - reduction)
        precision = self.equipment.legendary_bonus("precision")
        atk_spd = self.equipment.bonus("attack_speed") * 0.006
        cdr = min(0.2, self.equipment.bonus("cooldown_reduction") * 0.008)
        mult = self.skill_tree.cooldown_mult() * (1.0 - min(0.25, precision * 0.1) - cdr)
        if self.buffs.has("battle_cry"):
            mult *= 0.82
        return max(0.12, cd * mult / max(0.5, (self.attack_speed_mult + atk_spd) * self.mode_speed_mult))

    @property
    def skill_damage_bonus(self) -> float:
        en_bonus = self.attr("energy") * 0.4
        arcane = self.equipment.legendary_bonus("arcane")
        base = (
            self.equipment.bonus("skill_damage")
            + en_bonus
            + self.buffs.skill_damage_bonus()
            + arcane * (3 + self.experience.level * 0.8)
        )
        return base * self.skill_tree.skill_damage_mult()

    def clamp_resources(self) -> None:
        self.stats.hp = min(self.max_hp, max(0.0, self.stats.hp))
        self.stats.mana = min(self.max_mana, max(0.0, self.stats.mana))

    def take_damage(self, amount: float) -> float:
        passives = self.equipment.passive_skill_affixes()
        mana_pct = 0.0
        if "mana_shield" in passives:
            mana_pct = 0.2
        if self.buffs.has("mana_shield"):
            mana_pct = max(mana_pct, 0.35)
        if mana_pct > 0:
            to_mana = amount * mana_pct
            if self.stats.mana >= to_mana:
                self.stats.mana -= to_mana
                amount -= to_mana
        reduced = max(1.0, amount * (1.0 - min(0.75, self.armor * 0.01)))
        block = self.equipment.bonus("block")
        if block > 0 and random.random() < min(0.45, block * 0.025):
            reduced *= 0.35
        resist = (
            self.equipment.bonus("fire_resist")
            + self.equipment.bonus("cold_resist")
            + self.equipment.bonus("poison_resist")
        ) * 0.003
        reduced = max(1.0, reduced * (1.0 - min(0.35, resist)))
        thorns = self.equipment.legendary_bonus("thorns")
        thorns_dmg = self.equipment.bonus("thorns_damage")
        self.stats.hp -= reduced
        self.hit_flash = 0.15
        self.pending_thorns_damage = reduced * min(0.35, thorns * 0.25 + thorns_dmg * 0.01)
        return reduced

    def heal_over_time(self, dt: float) -> None:
        if self.hit_flash > 0:
            self.hit_flash -= dt
        regen = (
            self.stats.regen + self.equipment.bonus("regen") + self.equipment.set_regen_bonus()
        ) * self.skill_tree.regen_mult()
        self.stats.hp = min(self.max_hp, self.stats.hp + regen * dt)
        mana_regen = (
            2.0 + self.equipment.bonus("mana_regen") + self.attr("energy") * 0.05
        ) * self.skill_tree.mana_regen_mult()
        self.stats.mana = min(self.max_mana, self.stats.mana + mana_regen * dt)
