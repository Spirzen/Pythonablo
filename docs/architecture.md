# Архитектура Pythonablo

Документ для навигации по коду и для переноса в [draw.io](https://app.diagrams.net/) после проверки Mermaid.

**Стек:** Python 3, Pygame ≥ 2.5.0, один процесс, без сети.

**Паттерны (кратко):**

| Есть | Нет |
|------|-----|
| Машина состояний (`GameState`) | ECS (только лёгкий `Entity.components`) |
| Системы, вызываемые из `Game` | MVC |
| `EventBus` (pub/sub) | Глобальный singleton шины |
| Data-driven (`data/*.json`, `config.py`) | Мультиплеер |

**Заметка:** `systems/effect_system.py` не подключён к `Game`. VFX и частицы — `systems/effects.py`.

---

## 1. Слои и пакеты

```mermaid
flowchart TB
  subgraph Entry["Entry"]
    main["main.py"]
  end

  subgraph Core["core/ — оркестрация"]
    Game["Game<br/>game loop + state machine"]
    Config["config.py"]
    EB["EventBus"]
    LegDefs["legendary_defs.py"]
  end

  subgraph Engine["engine/ — Pygame"]
    Rnd["Renderer + MapRenderer"]
    Cam["Camera"]
    Inp["InputHandler"]
    Aud["AudioSystem"]
    Spr["SpriteCatalog"]
    Mot["motion"]
  end

  subgraph World["world/"]
    Map["GameMap"]
    Gen["LevelGenerator / ArenaGenerator"]
    Col["collision + pathfinding"]
  end

  subgraph Entities["entities/"]
    Ent["Entity hierarchy"]
    PE["PlayerEntity"]
  end

  subgraph PlayerDom["player/ — данные игрока"]
    PData["stats, inventory, equipment,<br/>experience, skills, buffs"]
  end

  subgraph Systems["systems/ — геймплей"]
    Mov["MovementSystem"]
    Cbt["CombatSystem"]
    Skl["SkillSystem"]
    AI["AISystem"]
    Loot["LootSystem"]
    Bon["BonusSystem"]
    Enc["EncounterSystem"]
    FX["EffectSystem · effects.py"]
    Aux["enemy_status, pillar_effects,<br/>legendary_skills"]
  end

  subgraph UI["ui/"]
    UIs["Menu, HUD, Inventory, Pause,<br/>Skills, Merchant, GameOver…"]
  end

  subgraph Persist["save/ + data/"]
    Save["SaveManager + floor_state"]
    JSON["data/*.json"]
  end

  main --> Game
  Game --> Config
  Game --> EB
  Game --> Engine
  Game --> World
  Game --> Entities
  Game --> Systems
  Game --> UI
  Game --> Save
  Game --> JSON

  PE --> Ent
  PE --> PData
  Mov & Cbt & Skl & AI & Loot & Bon --> EB
  Systems --> Entities
  Systems --> World
  Skl --> LegDefs
  Map --> Gen
  Map --> Col
```

---

## 2. Композиция `Game`

`Game` (`core/game.py`) — единственный оркестратор: создаёт зависимости, держит списки мира, вызывает системы по порядку.

```mermaid
flowchart LR
  subgraph GameObj["Game"]
    EB2["events: EventBus"]
    lists["enemies, ground_items, npcs,<br/>pillars, floor_cache, floor_states…"]
    runtime["player, game_map, state, floor…"]
  end

  subgraph Engine2["engine"]
    renderer["renderer"]
    mapr["map_renderer"]
    camera["camera"]
    input["input"]
    audio["audio"]
    sprites["sprites"]
  end

  subgraph Sys2["systems"]
    movement["movement"]
    combat["combat ← events"]
    effects["effects"]
    skills["skills ← events, effects"]
    ai["ai ← effects"]
    loot["loot ← events"]
    bonuses["bonuses ← events, effects"]
    encounters["encounters"]
  end

  subgraph UI2["ui"]
    menu["menu_ui"]
    hud["hud"]
    inv["inventory_ui"]
    pause["pause_ui"]
    stree["skill_tree_ui"]
    supg["skill_upgrade_ui"]
    merch["merchant_ui"]
    gover["game_over_ui"]
  end

  savem["save_manager"]

  GameObj --> Engine2
  GameObj --> Sys2
  GameObj --> UI2
  GameObj --> savem
  combat --> EB2
  loot --> EB2
  bonuses --> EB2
  skills --> EB2
  skills -.->|extends| legendary["LegendarySkillCaster"]
```

**Связи при создании (`Game.__init__`):**

- `CombatSystem(self.events)`
- `SkillSystem(self.events, self.effects)` — наследует `LegendarySkillCaster`
- `AISystem(self.effects)`
- `LootSystem(self.events)`, `BonusSystem(self.events, self.effects)`
- `EncounterSystem()` — без шины, вызывается из `Game` при загрузке этажа

---

## 3. Иерархия сущностей

```mermaid
classDiagram
  class Entity {
    +float x, y
    +float radius
    +bool alive
    +dict components
    +tile_pos()
    +distance_to()
  }

  class PlayerEntity {
    +Stats stats
    +Inventory inventory
    +Equipment equipment
    +Experience experience
    +SkillTree skill_tree
    +SkillUpgrades skill_upgrades
    +BuffManager buffs
  }

  class EnemyEntity
  class NPC
  class VillagerNPC
  class GroundItem
  class PickupBonus
  class Pillar
  class ProjectileEntity
  class MinionEntity

  Entity <|-- PlayerEntity
  Entity <|-- EnemyEntity
  Entity <|-- NPC
  Entity <|-- VillagerNPC
  Entity <|-- GroundItem
  Entity <|-- PickupBonus
  Entity <|-- Pillar
  Entity <|-- ProjectileEntity
  Entity <|-- MinionEntity
  NPC <|-- VillagerNPC

  note for PlayerEntity "Модули player/* — composition,\nне наследование"
```

---

## 4. Машина состояний `GameState`

```mermaid
stateDiagram-v2
  [*] --> MENU

  MENU --> PLAYING : новая игра / continue
  MENU --> [*] : quit

  PLAYING --> PAUSED : Esc
  PLAYING --> INVENTORY : I / Tab
  PLAYING --> SKILLS : наставник [E]
  PLAYING --> SKILL_UPGRADE : очки улучшения
  PLAYING --> MERCHANT : кузнец [E]
  PLAYING --> GAME_OVER : hp ≤ 0

  PAUSED --> PLAYING : Esc
  INVENTORY --> PLAYING : Esc / I
  SKILLS --> PLAYING : Esc / _prev_state
  SKILL_UPGRADE --> PLAYING : Esc / выбор
  MERCHANT --> PLAYING : Esc

  GAME_OVER --> MENU : подтверждение

  note right of PLAYING
    INVENTORY: мир рисуется,
    поверх — панель инвентаря
    _prev_state хранит возврат
    из SKILLS / SKILL_UPGRADE
  end note
```

---

## 5. Главный цикл (один кадр)

```mermaid
sequenceDiagram
  participant Loop as Game.run
  participant Ev as pygame events
  participant Inp as InputHandler
  participant Up as _update
  participant Dr as _draw
  participant Disp as display

  loop while running
    Loop->>Loop: dt = min(tick/FPS, 0.05)
    Loop->>Ev: _handle_events()
    Ev->>Inp: key/mouse
    Loop->>Up: _update(dt)
    Loop->>Dr: _draw()
    Loop->>Disp: flip()
  end
```

---

## 6. Порядок `_update_playing`

Вызывается только при `state == PLAYING` (и частично при `INVENTORY` / `MERCHANT` — см. `_update`).

```mermaid
flowchart TD
  A[kill streak / hit flash] --> B[MovementSystem.update]
  B --> C[player.heal_over_time]
  C --> D[Camera.follow]
  D --> E[CombatSystem.update]
  E --> F[SkillSystem.update]
  F --> G[EffectSystem.update · particles]
  G --> H[CombatSystem.enemy_attack_player × N]
  H --> I[AISystem.update + events]
  I --> J[VillagerNPC.update]
  J --> K[Protect encounter waves]
  K --> L[_update_arena_survival]
  L --> M[update_enemy_status · DoT → enemy_killed]
  M --> N[BonusSystem.update]
  N --> O[Arcane 5-piece set pulse · в Game]
  O --> P[auto pickup loot/bonuses]
  P --> Q[tick_motion entities]
  Q --> R[combat.try_attack if held]
  R --> S[_update_portal_hint]
  S --> T{hp ≤ 0?}
  T -->|да| U[emit player_died]
  T -->|нет| V{kills % 5?}
  V -->|да| W[_autosave]
```

---

## 7. Порядок отрисовки `_draw_world`

Снизу вверх (задний план → передний).

```mermaid
flowchart TD
  L1[background composite] --> L2[MapRenderer static + special tiles]
  L2 --> L3[ground_items · loot orbs]
  L3 --> L4[bonus_system.ground_bonuses]
  L4 --> L5[pillars]
  L5 --> L6[effects.rings · AoE]
  L6 --> L7[npcs]
  L7 --> L8[villager + HP bar]
  L8 --> L9[enemies + HP/cast UI]
  L9 --> L10[explosions · particles · hit_bursts]
  L10 --> L11[skill projectiles · minions]
  L11 --> L12[combat.damage_numbers]
  L12 --> L13[player sprite]
  L13 --> L14[combat.arrows homing]
  L14 --> L15[whirlwind overlay]
  L15 --> L16[melee slash arcs]
  L16 --> L17[portal markers EXIT / STAIRS_UP]

  L17 --> HUD[_draw: HUD + overlays по GameState]
```

---

## 8. EventBus

Один экземпляр на `Game`, передаётся в системы, которые эмитят события.

```mermaid
flowchart LR
  subgraph Emitters["emit"]
    CBT[CombatSystem]
    SKL[SkillSystem / LegendarySkillCaster]
    LOOT[LootSystem]
    BON[BonusSystem]
    EST[enemy_status]
    GM[Game · pillar / player_died]
  end

  EB3[(EventBus)]

  subgraph Handlers["subscribe → Game"]
    H1[_on_enemy_killed · XP, loot roll, audio]
    H2[_on_item_dropped / picked]
    H3[_on_bonus_picked]
    H4[_on_legendary_proc · VFX]
    H5[_on_inventory_full · toast]
    H6[_on_player_died → GAME_OVER]
    H7[_on_goblin_hit / enemy_hit · streak]
    H8[_on_attack_swung / skill_cast · SFX]
  end

  CBT & SKL & LOOT & BON & EST & GM --> EB3
  EB3 --> Handlers
```

| Событие | Основные emitters |
|---------|-------------------|
| `enemy_killed` | combat, skills, legendary, bonus, enemy_status, game |
| `enemy_hit` | combat, skills, legendary |
| `attack_swung` | combat |
| `skill_cast` | skills, legendary |
| `item_dropped` / `item_picked` / `inventory_full` | loot |
| `bonus_picked` | bonus |
| `legendary_proc` | combat |
| `goblin_hit` | combat |
| `player_died` | combat, game |

---

## 9. Загрузка игры и этажа

```mermaid
flowchart TD
  Start([main.py]) --> Init[Game.__init__]
  Init --> Menu[state = MENU]

  Menu -->|New game| NG[_start_new_game]
  Menu -->|Continue| LG[_load_game]

  NG --> P1[PlayerEntity + mode/difficulty multipliers]
  P1 --> LF{режим арены?}
  LF -->|да| Arena[_load_dedicated_arena]
  LF -->|нет| F1[_load_floor 1]

  LG --> SD[deserialize SaveData]
  SD --> LF2[_load_floor saved floor]

  F1 & Arena & LF2 --> Load[_load_floor]
  Load --> Cache{floor in floor_cache?}
  Cache -->|нет| GenMap[GameMap → LevelGenerator / ArenaGenerator]
  Cache -->|да| Reuse[cached GameMap]
  GenMap --> Spawn[AI spawn + restore_floor_state]
  Reuse --> Spawn
  Spawn --> EncRoll[EncounterSystem.roll]
  EncRoll --> Play[state = PLAYING]
```

**Персистентность этажа:** `floor_states[floor]` — снимок врагов/лута/бонусов; `floor_cache[floor]` — сгенерированная карта.

---

## 10. Зависимости данных

```mermaid
flowchart LR
  JSON[data/*.json]
  CFG[core/config.py]
  LEG[core/legendary_defs.py]

  JSON --> AI[AISystem templates]
  JSON --> Loot[LootSystem]
  JSON --> Save[restore_floor_state]

  CFG --> Game
  CFG --> All[баланс, enum'ы, UI colors]
  LEG --> Loot
  LEG --> Skl[SkillSystem / legendary skills]

  SaveMgr[save/save_manager.py] --> File[(save_data/save.json)]
```

---

## Следующий шаг: draw.io

После правок в этом файле можно запросить базовый `.drawio` (страницы 1–4: слои, `Game`, state machine, event bus). Раскладку и стили лучше довести вручную в diagrams.net.

**Проверка Mermaid:** [mermaid.live](https://mermaid.live) или предпросмотр Markdown в IDE.
