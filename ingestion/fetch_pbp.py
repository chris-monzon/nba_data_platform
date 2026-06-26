"""Acquire play-by-play and land it in bronze (per game).

Downloads the full-season PBP once via `nba_on_court` (there is no per-game
endpoint), caches it locally, then filters to each manifest game and writes
per-game Parquet to bronze. No enrichment — `players_on_court` is deferred, so
bronze stays content-faithful (same rows/columns as source, just scoped).

    python -m ingestion.fetch_pbp [--games ID ...] [--output-root PATH] [--force]
"""
from __future__ import annotations

import argparse
import io
from pathlib import Path

import nba_on_court as noc
import pandas as pd

from ingestion.common import Game, bronze_path, exists, load_manifest, write_bytes


def _ensure_season_csv(year: int, cache_dir: Path, force: bool) -> Path:
    """Download the season PBP once; the cache is always local (transient)."""
    csv_path = cache_dir / f"nbastats_{year}.csv"
    if csv_path.exists() and not force:
        print(f"  season {year}: cached")
        return csv_path
    cache_dir.mkdir(parents=True, exist_ok=True)
    print(f"  season {year}: downloading PBP ...")
    # seasontype="rg" = regular season; path MUST be explicit or it litters CWD.
    noc.load_nba_data(path=cache_dir, seasons=[year], data=("nbastats",),
                      seasontype="rg", untar=True)
    if not csv_path.exists():
        raise RuntimeError(f"expected {csv_path} after download")
    return csv_path


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch + filter PBP to bronze.")
    p.add_argument("--games", nargs="*", help="game_id(s) to process (default: all in manifest)")
    p.add_argument("--output-root", default="./data", help="local dir or gs:// root")
    p.add_argument("--cache-dir", default="./data/_cache", help="local season-CSV cache")
    p.add_argument("--force", action="store_true", help="re-download / re-write")
    args = p.parse_args()

    games = load_manifest(args.games)
    cache_dir = Path(args.cache_dir)
    print(f"pbp: {len(games)} game(s)")

    # One season download serves every game in that season.
    by_year: dict[int, list[Game]] = {}
    for g in games:
        by_year.setdefault(g.season_start_year, []).append(g)

    for year, year_games in by_year.items():
        csv_path = _ensure_season_csv(year, cache_dir, args.force)
        df = pd.read_csv(csv_path, low_memory=False)
        # Join-key gotcha: PBP GAME_ID is int (21500438); manifest is zero-padded str.
        key = df["GAME_ID"].astype(str).str.zfill(10)
        for g in year_games:
            dest = bronze_path(args.output_root, "pbp", g, "pbp.parquet")
            if not args.force and exists(dest):
                print(f"  skip {g.game_id} (exists)")
                continue
            sub = df[key == g.game_id]
            if sub.empty:
                raise RuntimeError(f"no PBP rows for {g.game_id} — check game_id/format")
            buf = io.BytesIO()
            sub.to_parquet(buf, index=False)
            write_bytes(dest, buf.getvalue())
            print(f"  {g.game_id}: wrote {len(sub)} rows -> {dest}")


if __name__ == "__main__":
    main()
