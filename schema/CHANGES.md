# Schema changes — midterm → final

What changed since the midterm ER diagram (`er_diagram_original.png`) and why. Current model: [`er_diagram.md`](er_diagram.md).

## Context

Scope tightened to a **SportVU + PBP event-map** proof-of-concept; **EPV is out of scope**. The midterm model was kept almost entirely intact — the steer was *small & few* schema changes. The changes below are the minimum needed to match what we actually build.

## Changes

1. **`MOMENT.event_id` removed.** After deduping tracking to one row per unique `timestamp_ms`, an instant maps to *multiple* SportVU eventIds (multi-valued), and SportVU `eventId` is not a trusted join key. The `EVENT ⟷ MOMENT` link is the **derived fuzzy-clock** relationship (period + nearest `game_clock`) the diagram already labeled — so the stored FK was both ill-defined and redundant.

2. **`POSSESSION` (+ `EVENT.possession_id`) marked future / not-built.** Its consumer was EPV, which is cut. Kept in the diagram (greyed, narrated as roadmap) rather than deleted — keeping is the smaller change, preserves the EPV foundation, and adding it back later is purely additive (new table + metadata-only `ALTER ADD COLUMN`).

3. **`EVENT` primary key is game-scoped `(game_id, event_id)`.** `event_id` (= PBP `EVENTNUM`) is only unique *within* a game. This is the stable key future entities attach to.

4. **`SHOT` folded into `EVENT`.** A shot is a 1:1 specialization of an event, and its fields split by layer: the **PBP facts** (`is_made` → `shot_made_flag`; `points`/`shot_type` later) are within-source, so they live on the `EVENT` fact rather than a separate table (over-normalizing ~335 shot rows isn't worth it). The **geometry** (`shot_distance`/`shot_zone`) is a *cross-source* derivation (PBP ⋈ tracking) computed in the `gold.events_with_location` serving mart, not silver. `contested_distance` is future/EPV. Net: no standalone `SHOT` table — removed from the silver ER diagram.

## Unchanged

Dims (`SEASON`, `TEAM`, `PLAYER`, `GAME`), `EVENT`, the `MOMENT` + `PLAYER_LOCATION` tracking facts (tall, header–detail; ball on `MOMENT`), and `EVENT_PARTICIPANT` (direct play participants).

## Serving layer

`gold.events_with_location` is a **denormalized mart derived from the silver tables** (not a dimensional entity) — see the lineage view in [`er_diagram.md`](er_diagram.md).
