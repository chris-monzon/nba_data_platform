# nba_data_platform

A cloud **data platform** that fuses NBA SportVU optical player/ball tracking (~25 Hz) with
play-by-play (PBP) for the **2015-16 season**, and serves an interactive event-map dashboard.

This repo is the **platform layer** (ingestion → warehouse → gold tables). The dashboard is a
**consumer** that sits on top of the gold layer.

> **Status:** Scaffolding (Milestone 4). Folder structure, config, and stubs are in place;
> pipeline logic and final schema DDL are in progress. See [CHECKLIST.md](CHECKLIST.md).

---

## What it is

The game becomes a stream of **events in space and time** rather than a box score. We join each
play-by-play event to the tracking moment at that instant to get its court `(x, y)` location,
then expose it as a dashboard: *select a player + event type → see a court map of where those
events occurred* (e.g. a player's shot map).

## Architecture

```
 Sources                Ingest (Cloud Run)        Warehouse (BigQuery)         Serve
 ───────                ──────────────────        ────────────────────         ─────
 SportVU tracking  ─┐   parse 25Hz JSON           silver: cleaned tables       Streamlit app
 (.7z JSON, GitHub) │   → tabular Parquet  ──┐                                  (consumer)
                    ├─►                      ├─► load → BQ ──► SQL fuzzy-join ──► gold
 Play-by-play       │   fetch via            │                 (PBP ↔ tracking)  events_with_
 (nba_on_court lib) ─┘   nba_on_court  ───────┘                                  location
```

**Medallion layers**
- **Bronze** — raw, untransformed (subset of games) landed in GCS.
- **Silver** — parsed/cleaned/conformed tables (tracking moments, PBP).
- **Gold** — `events_with_location`: one row per event with the acting player's court `(x, y)`
  at event time. This is what the dashboard reads.

The headline transformation is the **fuzzy-clock join** of PBP events to the nearest 25 Hz
tracking moment, done in **BigQuery SQL** (`transform/gold_events_with_location.sql`).

## Tech stack

| Layer | Tool | Role |
|---|---|---|
| Storage | **GCS** | bronze/silver/gold object storage |
| Ingestion | **Python on Cloud Run** | parse heavy JSON → Parquet (per-game, idempotent) |
| Warehouse | **BigQuery** | single OLAP warehouse; SQL transforms |
| Serve | **Streamlit** | interactive event-map dashboard (consumer) |
| Tooling | **uv**, Python **3.11**, Git/GitHub | env + deps + collaboration |

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

# 3. (Pipeline — in progress)
#    uv run python ingestion/download_tracking.py
#    uv run python ingestion/fetch_pbp.py
#    uv run python ingestion/parse_tracking.py
#    ...then run the BigQuery SQL in transform/

# 4. Launch the dashboard (consumer)
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
