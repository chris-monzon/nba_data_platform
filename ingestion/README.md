# ingestion/

**Platform layer — acquisition + parsing.** Gets raw data from the two sources and lands it as
tabular Parquet in GCS (bronze/silver). No business logic lives here — that's `transform/`.

Two distinct jobs:

1. **Acquire (extract)** — pull raw data from source.
   - `download_tracking.py` — download + unzip the `.7z`/JSON SportVU archives.
   - `fetch_pbp.py` — pull play-by-play via the `nba_on_court` library.
2. **Parse (structural reshape)** — `parse_tracking.py` explodes the nested ~25 Hz tracking JSON
   into flat, tabular moments. This is the heavy per-game step containerized for Cloud Run
   (`Dockerfile`).

## How raw data is obtained

- **Tracking:** SportVU 2015-16 JSON archives from
  https://github.com/sealneaward/nba-movement-data
- **Play-by-play:** the [`nba_on_court`](https://github.com/shufinskiy/nba-on-court) Python
  library (a declared dependency — no third repo vendored).

We process a **representative subset of games** (not the full season) — see `data/README.md`.

`parse_tracking.py` is a per-game, idempotent function (keyed by `season/game_id`) so it can run
over a few games now and fan out to one Cloud Run job per game later.
