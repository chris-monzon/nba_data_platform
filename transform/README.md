# transform/

**Platform layer — business-logic transformations, in BigQuery SQL.**

This is where the data becomes analytics-ready. Unlike `ingestion/` (structural reshaping),
everything here is *business logic*: cleaning, conforming, joining, aggregating.

| File | Layer | Purpose |
|---|---|---|
| `silver_pbp.sql` | silver | clean / conform play-by-play events |
| `silver_tracking.sql` | silver | conform parsed tracking moments |
| `gold_events_with_location.sql` | gold | **headline transformation** — fuzzy-clock join of PBP events to the nearest 25 Hz tracking moment → one row per event with court `(x, y)` |

The gold table `events_with_location` is the single source of truth the Streamlit app reads.

> Schema (table/column names) is still being finalized — see `schema/`.
