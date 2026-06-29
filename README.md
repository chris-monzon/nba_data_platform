# nba_data_platform

A cloud **data platform** that fuses NBA SportVU optical player/ball tracking (~25 Hz) with
play-by-play (PBP) for the **2015-16 season**, and serves an interactive event-map dashboard.

This repo is the **platform layer** (ingestion → warehouse → gold tables). The dashboard is a
**consumer** that sits on top of the gold layer.

> **Status:** See [CHECKLIST.md](CHECKLIST.md).

---

## What it is

The game becomes a stream of **events in space and time** rather than a box score. For each shot,
we recover its true court `(x, y)` from the SportVU **ball trajectory** — detecting the release
frame from the ball's flight rather than matching clocks (the two feeds aren't synced to the
second). We expose it as a dashboard: *select a player → see their shot map*.

## Architecture

```
 Sources                Ingest (Python, Cloud Run-ready)   Warehouse (BigQuery)        Serve
 ───────                ────────────────────────────────   ────────────────────        ─────
 SportVU tracking  ─┐   parse 25Hz JSON → Parquet           silver: PBP event model     Streamlit
 (.7z JSON, GitHub) │   locate shots from ball trajectory   + tracking (external)       shot-map
                    ├─►                                  ──► load → BQ ─► SQL join ──►   app
 Play-by-play       │   fetch via                                       + geometry       (consumer)
 (nba_on_court lib) ─┘   nba_on_court                                                    events_with_
                                                                                         location
```

**Medallion layers**
- **Bronze** — raw, untransformed (subset of games) landed in GCS.
- **Silver** — parsed/cleaned/conformed tables: PBP event model, tracking moments, shot
  locations, and conformed dimensions.
- **Gold** — `events_with_location`: one row per PBP event; field-goal attempts carry the shot's
  court `(x, y)` plus distance and 3PT geometry, other events carry NULL location. This is what
  the dashboard reads.

The headline transformation **locates each shot from the SportVU ball trajectory**: find the frame
where the ball passes through the rim, then back up to the release — sidestepping the fact that the
PBP and tracking clocks aren't synced to the second (a naive clock-match lands ~9 ft off, up to
40 ft on transition). Done in Python (`ingestion/parse_shot_locations.py`); the gold SQL
(`transform/gold_events_with_location.sql`) then joins it to the PBP event spine and adds shot
distance + 3PT classification.

## Tech stack

| Layer | Tool | Role |
|---|---|---|
| Storage | **GCS** | bronze/silver/gold object storage |
| Ingestion | **Python** (containerized, Cloud Run-ready) | parse heavy JSON → Parquet + locate shots (per-game, idempotent) |
| Warehouse | **BigQuery** | single OLAP warehouse; SQL transforms |
| Serve | **Streamlit** | interactive event-map dashboard (consumer) |

## Data sources

No data is committed to this repo. See [`data/README.md`](data/README.md) for how to obtain it.

- **Tracking (SportVU 2015-16):** https://github.com/sealneaward/nba-movement-data
- **Play-by-play:** the [`nba_on_court`](https://github.com/shufinskiy/nba-on-court) Python library

## How to run

> Prerequisites: [`uv`](https://docs.astral.sh/uv/), and a GCP project with GCS + BigQuery enabled.

```bash
# 1. Set up the environment (Python 3.11, all deps)
uv sync

# 2. Configure credentials
cp .env.example .env        # then fill in your GCP values
gcloud auth application-default login

# 3. Run ingestion (bronze → silver Parquet), per-game and idempotent
uv run python -m ingestion.download_tracking     # SportVU .7z  → bronze JSON
uv run python -m ingestion.fetch_pbp             # play-by-play → bronze Parquet
uv run python -m ingestion.parse_tracking        # 25Hz JSON    → silver Parquet (moment + player_location)
uv run python -m ingestion.parse_dims            # dims (player/team/game/season) from tracking headers
uv run python -m ingestion.parse_shot_locations  # locate shots from ball trajectory → silver Parquet

# 4. Build silver + gold in BigQuery (run the SQL in transform/, in order)
#    silver_tracking.sql · silver_pbp.sql · silver_dims.sql · silver_shot_location.sql · gold_events_with_location.sql

# 5. Launch the dashboard (consumer)
uv run streamlit run app/streamlit_app.py
```

## Repository structure

```
nba_data_platform/
├── ingestion/   # PLATFORM: acquire raw data + parse tracking JSON → Parquet
├── transform/   # PLATFORM: BigQuery SQL (silver + gold business logic)
├── schema/      # PLATFORM: schema design (ER diagram, DDL)
├── app/         # CONSUMER: Streamlit dashboard (thin view + queries + court geometry)
├── notebooks/   # exploratory analysis only (not part of the pipeline)
└── data/        # gitignored; see data/README.md for how to obtain raw data
```

## Team

Denver Chicken Nuggets — Christopher Monzon · Lokesh Muvva · Joshua He
MSDS 683 · Data Architecture
