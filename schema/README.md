# schema/

Schema design for the platform.

> **DRAFT — under revision.** The ER diagram below reflects the midterm design and is being
> updated (BigQuery warehouse, event-map focus). DDL will be added once finalized.

## Files

- `er_diagram.png` — entity-relationship diagram (exported from the team deck).
  Replace with a clean export from Google Slides when convenient.

## Model summary

- **Dimensions:** TEAM, PLAYER, GAME, SEASON (conformed); EVENT_PARTICIPANT (bridge).
- **Facts:** EVENT (PBP spine), SHOT (1:1 with EVENT), tracking moments / player locations.
- **Gold:** `events_with_location` — events joined to their court `(x, y)` at event time.
