"""Legendary item and skill override definitions."""

from __future__ import annotations

# Base skills that legendary items can replace (not fireball / whirlwind)
REPLACEABLE_SKILLS = ("aoe", "summon", "pulse")

# Random pool — stat-only legendaries
STAT_LEGENDARY_AFFIXES = (
    "vampiric", "explosive", "thorns", "swift", "arcane",
    "fortune", "fury", "ward", "precision", "lifesteal",
    "phoenix_heart",
)

LEGENDARY_AFFIXES: dict[str, dict[str, str]] = {
    "vampiric": {"name": "Кровь жизни", "desc": "Исцеляет 8% HP при убийстве"},
    "explosive": {"name": "Удар грома", "desc": "15% шанс взрыва при атаке"},
    "thorns": {"name": "Шипы", "desc": "Отражает 25% полученного урона"},
    "swift": {"name": "Стремительность", "desc": "+15% скорости передвижения"},
    "arcane": {"name": "Сила духов", "desc": "+20% урона умений"},
    "fortune": {"name": "Удача батыра", "desc": "+50% золота с убийств"},
    "fury": {"name": "Ярость", "desc": "+12% урона атаки"},
    "ward": {"name": "Оберег", "desc": "+18% максимального HP"},
    "precision": {"name": "Точность", "desc": "-10% перезарядки умений"},
    "lifesteal": {"name": "Кровожадность", "desc": "3% вампиризм от урона"},
    "phoenix_heart": {"name": "Живая вода", "desc": "Один раз воскрешает после смерти (50% HP)"},
    # Whirlwind transforms
    "whirlwind_fire": {"name": "Огненный вихрь", "desc": "Вихрь становится огненным (оранжевый)"},
    "whirlwind_ice": {"name": "Ледяной вихрь", "desc": "Вихрь становится ледяным (голубой)"},
    "whirlwind_poison": {"name": "Ядовитый вихрь", "desc": "Вихрь становится ядовитым (зелёный)"},
    # Attack transform
    "homing_arrow": {"name": "Стрела Самрау", "desc": "ЛКМ заменена магической стрелой"},
    # Skill overrides
    "skill_power_strike": {"name": "Мощный удар", "desc": "Заменяет умение: огромная область урона"},
    "skill_knife_fan": {"name": "Веер клинков", "desc": "Заменяет умение: конус снарядов"},
    "skill_meteor": {"name": "Град камней", "desc": "Заменяет умение: серия ударов по зоне"},
    "skill_ice_wave": {"name": "Ледяная волна", "desc": "Заменяет умение: расширяющийся круг"},
    "skill_chain_lightning": {"name": "Цепная молния", "desc": "Заменяет умение: урон перескакивает между врагами"},
    "skill_poison": {"name": "Отравление", "desc": "Заменяет умение: периодический урон ядом"},
    "skill_burning": {"name": "Пламя", "desc": "Заменяет умение: огонь с распространением"},
    "skill_bleeding": {"name": "Кровотечение", "desc": "Заменяет умение: урон и замедление"},
    "skill_curse": {"name": "Проклятие", "desc": "Заменяет умение: враги получают больше урона"},
    "skill_battle_cry": {"name": "Боевой клич", "desc": "Заменяет умение: +урон и скорость атаки"},
    "skill_mana_shield": {"name": "Щит маны", "desc": "Заменяет умение: часть урона уходит в ману"},
    "skill_ice_armor": {"name": "Ледяная броня", "desc": "Заменяет умение: замедляет атакующих"},
    "skill_vampirism": {"name": "Поглощение жизни", "desc": "Заменяет умение: усиленное поглощение HP"},
    "skill_reflect": {"name": "Отражение урона", "desc": "Заменяет умение: отражает урон атакующим"},
}

UNIQUE_LEGENDARY_ITEMS: dict[str, dict] = {
    "whirlwind_fire": {"name": "Перчатки огня", "slot": "gloves", "category": "armor"},
    "whirlwind_ice": {"name": "Обод северного ветра", "slot": "helmet", "category": "armor"},
    "whirlwind_poison": {"name": "Жало змея", "slot": "ring_left", "category": "jewelry"},
    "homing_arrow": {"name": "Лук Самрау", "slot": "weapon_main", "category": "weapon"},
    "skill_power_strike": {"name": "Молот дива", "slot": "weapon_main", "category": "weapon"},
    "skill_knife_fan": {"name": "Перчатки охотника", "slot": "gloves", "category": "armor"},
    "skill_meteor": {"name": "Посох грома", "slot": "weapon_main", "category": "weapon"},
    "skill_ice_wave": {"name": "Оберег зимы", "slot": "amulet", "category": "jewelry"},
    "skill_chain_lightning": {"name": "Кольцо грозы", "slot": "ring_right", "category": "jewelry"},
    "skill_poison": {"name": "Флакон яда", "slot": "talisman", "category": "jewelry"},
    "skill_burning": {"name": "Пояс пепла", "slot": "belt", "category": "armor"},
    "skill_bleeding": {"name": "Клинок мучений", "slot": "weapon_off", "category": "weapon"},
    "skill_curse": {"name": "Тёмный талисман", "slot": "talisman", "category": "jewelry"},
    "skill_battle_cry": {"name": "Рог батыра", "slot": "shoulders", "category": "armor"},
    "skill_mana_shield": {"name": "Кристалл Яншишмы", "slot": "chest", "category": "armor"},
    "skill_ice_armor": {"name": "Доспех северного ветра", "slot": "chest", "category": "armor"},
    "skill_vampirism": {"name": "Клык волка", "slot": "amulet", "category": "jewelry"},
    "skill_reflect": {"name": "Зеркальный щит", "slot": "weapon_off", "category": "weapon"},
    "phoenix_heart": {"name": "Оберег Яншишмы", "slot": "amulet", "category": "jewelry"},
}

SKILL_OVERRIDE_IDS = tuple(k for k in UNIQUE_LEGENDARY_ITEMS if k.startswith("skill_"))

WHIRLWIND_ELEMENTS = {
    "whirlwind_fire": "fire",
    "whirlwind_ice": "ice",
    "whirlwind_poison": "poison",
}

WHIRLWIND_COLORS = {
    "fire": ((255, 120, 40), (255, 180, 60), (255, 220, 120)),
    "ice": ((80, 180, 255), (140, 210, 255), (200, 240, 255)),
    "poison": ((80, 220, 80), (120, 255, 100), (180, 255, 140)),
    "default": ((120, 180, 255), (180, 220, 255), (255, 255, 255)),
}

SKILL_OVERRIDE_LABELS = {
    "power_strike": "Мощный удар",
    "knife_fan": "Веер клинков",
    "meteor": "Град камней",
    "ice_wave": "Ледяная волна",
    "chain_lightning": "Молния",
    "poison": "Яд",
    "burning": "Пламя",
    "bleeding": "Кровь",
    "curse": "Проклятие",
    "battle_cry": "Клич",
    "mana_shield": "Щит маны",
    "ice_armor": "Лед. броня",
    "vampirism": "Поглощение",
    "reflect": "Отражение",
}

FLOOR_ELITE_SPAWN_CHANCE = 0.38
FLOOR_ELITE_COUNT = 3
