# Schema — ER Diagram (silver) + Gold lineage

> Text-based source of record for the schema. Renders inline on GitHub.
> The prior rendered export is kept alongside at [`er_diagram_original.png`](er_diagram_original.png).

## Legend

- **dim** = conformed dimension · **fact** = fact table · **bridge** = many-to-many bridge.
- **Implemented** = everything below *except* the clearly-marked future block.
- **FUTURE / not built** = `POSSESSION` (per-possession fact + `epv_estimate`, the EPV foundation) and
  its `EVENT.possession_id` FK. Designed-for, intentionally **not** built in the PoC (EPV is out of scope).
  Mermaid `erDiagram` can't grey a table, so future entities are isolated in the marked block below and in
  every relationship label; treat that block as greyed/dashed when presenting.
- **On-court lineup is deliberately absent** — the 10 on-court players come *from the tracking moment itself*
  (`PLAYER_LOCATION`), so no lineup table is needed. `EVENT_PARTICIPANT` is the *direct play participants*
  bridge (shooter/assister/fouler), which is a different thing and **is** implemented.
- **`SHOT` facts folded into `EVENT`; shot *location* is the `SHOT_LOCATION` fact.** A shot's PBP facts
  live on `EVENT` (`shot_made_flag` now; `points`/`shot_type` later). Its court **location** is the
  `SHOT_LOCATION` fact (one row per field-goal attempt), derived by `parse_shot_locations.py` from the
  **ball trajectory** (ball-at-rim → release) — *not* a fuzzy clock match, because PBP and SportVU clocks
  aren't synced to the second. Shot *geometry* (`shot_distance`/`is_three`) is then computed in the gold
  mart from those release coords; `contested_distance` is future/EPV.
- **`EVENT ⟷ MOMENT` fuzzy-clock alignment was dropped.** It located shots ~9 ft off (clock desync); the
  full-floor 10-player snapshot that needed it is deferred (it requires per-event tracking windows).
- **`PLAYER` is bio-only; team modeled by the `PLAYER_TEAM_SEASON` SCD2 bridge.** A player's team is
  time-varying (trades/seasons), so it's not a static player attribute. Team *for a given play* comes
  from the facts (`PLAYER_LOCATION`/`EVENT_PARTICIPANT`); roster history is the Type-2 SCD bridge
  (effective-dated `valid_from`/`valid_to`/`is_current`). PoC loads one current stint per player
  (single season); the change-detecting MERGE load activates with multi-season data.

## Silver — dimensional model (galaxy / fact constellation)

```mermaid
erDiagram
    %% ============ DIMENSIONS ============
    SEASON {
        int    season_id    PK
        string season_label
        date   start_date
        date   end_date
    }
    TEAM {
        int    team_id      PK
        string abbreviation
        string full_name
        string conference
    }
    PLAYER {
        int    player_id   PK
        string first_name
        string last_name
        string position
    }
    GAME {
        int    game_id       PK
        int    season_id     FK
        int    home_team_id  FK
        int    away_team_id  FK
        date   game_date
        string arena
    }

    %% ============ FACTS (implemented) ============
    EVENT {
        int     game_id        PK,FK "PK is game-scoped"
        int     event_id       PK    "= PBP EVENTNUM, unique within game"
        int     period
        decimal game_clock
        string  event_type
        string  description
        boolean shot_made_flag        "SHOT folded in; geometry derived in gold"
    }
    MOMENT {
        int     moment_id   PK   "= tracking timestamp_ms, deduped, globally unique"
        int     game_id     FK
        int     period
        decimal game_clock
        decimal shot_clock  "nullable"
        decimal ball_x
        decimal ball_y
        decimal ball_z
    }
    PLAYER_LOCATION {
        int     moment_id PK,FK
        int     player_id PK,FK
        int     team_id   FK
        decimal loc_x
        decimal loc_y
    }
    SHOT_LOCATION {
        int     game_id            PK,FK
        int     event_id           PK,FK
        int     shot_player_id     FK
        decimal shooter_x   "release: shooter feet"
        decimal shooter_y
        decimal ball_x      "release: ball (official basis)"
        decimal ball_y
        decimal release_game_clock
    }

    %% ============ BRIDGE ============
    EVENT_PARTICIPANT {
        int    event_id  PK,FK
        int    player_id PK,FK
        string role      PK
        int    team_id   FK
    }
    PLAYER_TEAM_SEASON {
        int     player_team_season_id PK "surrogate (SCD2 version key)"
        int     player_id  FK
        int     team_id    FK
        int     season_id  FK
        date    valid_from
        date    valid_to       "NULL = current"
        boolean is_current
    }

    %% ============ FUTURE / NOT BUILT (treat as greyed) ============
    POSSESSION {
        int     possession_id   PK   "FUTURE / not built"
        int     game_id         FK   "FUTURE"
        int     offense_team_id FK   "FUTURE"
        int     defense_team_id FK   "FUTURE"
        int     period               "FUTURE"
        decimal start_game_clock      "FUTURE"
        decimal end_game_clock        "FUTURE"
        int     points_scored         "FUTURE"
        string  outcome_type          "FUTURE"
        decimal epv_estimate          "FUTURE / EPV"
    }

    %% ---- relationships (implemented) ----
    SEASON ||--o{ GAME              : "spans"
    TEAM   ||--o{ GAME              : "home team"
    TEAM   ||--o{ GAME              : "away team"
    GAME   ||--o{ EVENT             : "contains"
    GAME   ||--o{ MOMENT            : "tracked in"
    EVENT  ||--o{ EVENT_PARTICIPANT : "involves"
    PLAYER ||--o{ EVENT_PARTICIPANT : "participates as"
    PLAYER ||--o{ PLAYER_TEAM_SEASON : "roster stints (SCD2)"
    TEAM   ||--o{ PLAYER_TEAM_SEASON : "rosters"
    SEASON ||--o{ PLAYER_TEAM_SEASON : "within"
    PLAYER ||--o{ PLAYER_LOCATION   : "located as"
    MOMENT ||--o{ PLAYER_LOCATION   : "captures"
    EVENT  ||--o| SHOT_LOCATION     : "located (ball-trajectory release)"
    PLAYER ||--o{ SHOT_LOCATION     : "shoots"

    %% ---- relationships (FUTURE / not built) ----
    GAME       ||--o{ POSSESSION : "contains (future)"
    TEAM       ||--o{ POSSESSION : "on offense (future)"
    TEAM       ||--o{ POSSESSION : "on defense (future)"
    POSSESSION ||--o{ EVENT      : "sequences (future)"
```

### Changes from `er_diagram_original.png` (this redraw)

1. **Removed `event_id` FK from `MOMENT`** — after dedup an instant maps to multiple SportVU eventIds (multi-valued) and SportVU `eventId` is not a trusted join key; the `EVENT ⟷ MOMENT` link is the derived fuzzy-clock relationship instead.
2. **`POSSESSION` (+ `EVENT.possession_id`) marked FUTURE / not built** — greyed in the diagram, narrated as roadmap.
3. **No lineup table** — on-court players come from the tracking moment; `EVENT_PARTICIPANT` (direct participants) is unaffected.
4. **`EVENT` PK is game-scoped `(game_id, event_id)`** — `event_id` alone (= PBP `EVENTNUM`) is only unique within a game.

## Gold — serving layer lineage (not a dimensional entity)

`events_with_location` is a **denormalized serving mart derived from the silver tables**, not part of the
dimensional model above. Shown here as bronze → silver → gold lineage.

```mermaid
flowchart LR
    subgraph BRONZE
        b1["tracking JSON<br/>(per game)"]
        b2["pbp parquet<br/>(per game)"]
    end
    subgraph SILVER["SILVER · dimensional model"]
        s1[MOMENT]
        s2[PLAYER_LOCATION]
        s3["EVENT<br/>(shot facts folded in)"]
        s4["SHOT_LOCATION<br/>(ball-trajectory release)"]
        s5["dims: GAME / PLAYER / TEAM / SEASON"]
    end
    subgraph GOLD["GOLD · serving marts"]
        g1["events_with_location<br/>(event-grain; shots located)"]
    end

    b1 --> s1
    b1 --> s2
    b2 --> s3
    b1 -->|ball arc + shooter| s4
    b2 -->|"shot events (eventId)"| s4
    s3 -->|event spine| g1
    s4 -->|"release x,y → geometry"| g1

    ff["full-floor (event × 10 players)<br/>+ POSSESSION + lineup<br/>FUTURE / not built"]:::future
    classDef future fill:#eee,stroke:#999,stroke-dasharray:5 5,color:#666;
```

> Streamlit reads `events_with_location` directly (thin view) — all shot-location/geometry work is resolved upstream.
> `MOMENT`/`PLAYER_LOCATION` remain in silver for the deferred full-floor view; they are not currently joined into gold.
> To export a PNG for a deck: `mmdc -i schema/er_diagram.md -o schema/er_diagram_new.png` (mermaid-cli), or paste a block into <https://mermaid.live>.
