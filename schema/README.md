# schema/

Schema design for the platform.

> Schema gate locked 2026-06-26 (silver model + gold serving layer). DDL to follow.

## Files

- `er_diagram.md` — **source of record**: text-based Mermaid ER diagram (silver) + gold lineage,
  reflecting the locked decisions. Renders inline on GitHub.
- `er_diagram_original.png` — prior rendered export (midterm design); kept for reference.

## Model summary

- **Dimensions:** TEAM, PLAYER, GAME, SEASON (conformed); EVENT_PARTICIPANT (bridge).
- **Facts:** EVENT (PBP spine), SHOT (1:1 with EVENT), tracking moments / player locations.
- **Gold:** `events_with_location` — events joined to their court `(x, y)` at event time.
