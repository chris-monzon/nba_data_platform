# data/

**No data is committed to this repo** (this folder is gitignored except for this README).
This documents how to obtain the raw data.

## Sources

- **Tracking (SportVU 2015-16):** https://github.com/sealneaward/nba-movement-data
  Per-game `.7z` archives of ~25 Hz optical tracking JSON (~100 MB each unzipped).
- **Play-by-play:** the [`nba_on_court`](https://github.com/shufinskiy/nba-on-court) Python
  library (a project dependency — no manual download needed).

## Sample-data approach

We use a **representative subset of games** (about one week of the 2015-16 season), not the full
volume — enough to demo the full bronze → silver → gold path and the dashboard. The pipeline is
parameterized by game id, so the same code scales to more games.

## Local layout (gitignored)

```
data/
├── bronze/   # raw downloaded tracking JSON
├── silver/   # parsed tabular Parquet
└── gold/     # (optional) local copies of gold extracts
```
