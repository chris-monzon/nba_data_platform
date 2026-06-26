# Schema changes — midterm → final

What changed since the midterm ER diagram (`er_diagram_original.png`) and why. Current model: [`er_diagram.md`](er_diagram.md).

## Context

Scope tightened to a **SportVU + PBP event-map** proof-of-concept; **EPV is out of scope**. The midterm model was kept almost entirely intact — the steer was *small & few* schema changes. The changes below are the minimum needed to match what we actually build.

## Changes

1. **`MOMENT.event_id` removed.** After deduping tracking to one row per unique `timestamp_ms`, an instant maps to *multiple* SportVU eventIds (multi-valued), and SportVU `eventId` is not a trusted join key. The `EVENT ⟷ MOMENT` link is the **derived fuzzy-clock** relationship (period + nearest `game_clock`) the diagram already labeled — so the stored FK was both ill-defined and redundant.

2. **`POSSESSION` (+ `EVENT.possession_id`) marked future / not-built.** Its consumer was EPV, which is cut. Kept in the diagram (greyed, narrated as roadmap) rather than deleted — keeping is the smaller change, preserves the EPV foundation, and adding it back later is purely additive (new table + metadata-only `ALTER ADD COLUMN`).

3. **`EVENT` primary key is game-scoped `(game_id, event_id)`.** `event_id` (= PBP `EVENTNUM`) is only unique *within* a game. This is the stable key future entities attach to.

## Unchanged

Dims (`SEASON`, `TEAM`, `PLAYER`, `GAME`), `EVENT`, `SHOT` (1:1 weak ext.), the `MOMENT` + `PLAYER_LOCATION` tracking facts (tall, header–detail; ball on `MOMENT`), and `EVENT_PARTICIPANT` (direct play participants).

## Serving layer

`gold.events_with_location` is a **denormalized mart derived from the silver tables** (not a dimensional entity) — see the lineage view in [`er_diagram.md`](er_diagram.md).
