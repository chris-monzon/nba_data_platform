"""Parse raw SportVU tracking JSON into tabular silver Parquet (structural reshape).

For ONE game, explode the nested ~25 Hz JSON into two silver tables, partitioned
by season/game_id:

  - MOMENT          (header): one row per unique moment instant — clocks + ball x/y/z
  - PLAYER_LOCATION (detail): one tall row per player per moment — x/y

`moment_id` is the SportVU millisecond timestamp (unique within a game). PBP-
independent: the event<->tracking join happens later in BigQuery (transform/).

Full 25 Hz is kept (no time-downsampling). SportVU re-lists overlapping moment
windows across adjacent events, so the same instant recurs in several events'
moment arrays; we keep one row per timestamp (duplicates verified identical).

    python -m ingestion.parse_tracking [--games ID ...] [--output-root PATH] [--force]
"""
from __future__ import annotations

import argparse
import io
import json

import pandas as pd

from ingestion.common import (
    Game, bronze_path, exists, load_manifest, read_bytes, silver_path, write_bytes,
)

MOMENT_FILE = "moment.parquet"
PLAYER_LOCATION_FILE = "player_location.parquet"


def _explode(raw: dict) -> tuple[list[tuple], list[tuple]]:
    """Walk events -> moments -> positions into (moment_rows, player_rows).

    Dedupes moments by timestamp. The ball is the position with player_id == -1
    (not assumed first — ~1% of frames drop the ball or a player).
    """
    moment_rows: list[tuple] = []
    player_rows: list[tuple] = []
    seen: set[int] = set()
    dropped_null_ts = 0

    for event in raw["events"]:
        for m in event["moments"]:
            period, ts, game_clock, shot_clock, _unused, positions = m
            if ts is None:          # no moment_id -> unusable for dedup/join
                dropped_null_ts += 1
                continue
            if ts in seen:          # same instant re-listed by an adjacent event
                continue
            seen.add(ts)

            ball = next((p for p in positions if p[1] == -1), None)
            ball_x, ball_y, ball_z = (ball[2], ball[3], ball[4]) if ball else (None, None, None)
            moment_rows.append((ts, period, game_clock, shot_clock, ball_x, ball_y, ball_z))

            for team_id, player_id, x, y, _z in positions:
                if player_id == -1:
                    continue        # ball, already captured on the moment row
                player_rows.append((ts, team_id, player_id, x, y))

    if dropped_null_ts:
        print(f"    dropped {dropped_null_ts} moment(s) with null timestamp")
    return moment_rows, player_rows


def _write_parquet(df: pd.DataFrame, dest: str) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    write_bytes(dest, buf.getvalue())


def parse_game(game: Game, output_root: str, force: bool) -> None:
    """Parse one game's tracking JSON -> two silver Parquet tables. Idempotent."""
    moment_dest = silver_path(output_root, "tracking_moment", game, MOMENT_FILE)
    player_dest = silver_path(output_root, "player_location", game, PLAYER_LOCATION_FILE)
    if not force and exists(moment_dest) and exists(player_dest):
        print(f"  skip {game.game_id} (exists)")
        return

    src = bronze_path(output_root, "tracking", game, f"{game.game_id}.json")
    print(f"  {game.game_id}: reading {src}")
    raw = json.loads(read_bytes(src))
    moment_rows, player_rows = _explode(raw)

    moment_df = pd.DataFrame(
        moment_rows,
        columns=["moment_id", "period", "game_clock", "shot_clock", "ball_x", "ball_y", "ball_z"],
    )
    moment_df.insert(0, "game_id", game.game_id)
    moment_df.insert(1, "season", game.season)

    player_df = pd.DataFrame(
        player_rows,
        columns=["moment_id", "team_id", "player_id", "player_x", "player_y"],
    )
    player_df.insert(0, "game_id", game.game_id)

    _write_parquet(moment_df, moment_dest)
    _write_parquet(player_df, player_dest)
    print(f"  {game.game_id}: wrote {len(moment_df)} moments, {len(player_df)} player-locations")


def main() -> None:
    p = argparse.ArgumentParser(description="Parse SportVU tracking JSON -> silver Parquet.")
    p.add_argument("--games", nargs="*", help="game_id(s) to process (default: all in manifest)")
    p.add_argument("--output-root", default="./data", help="local dir or gs:// root")
    p.add_argument("--force", action="store_true", help="re-parse even if silver exists")
    args = p.parse_args()

    games = load_manifest(args.games)
    print(f"parse: {len(games)} game(s)")
    for g in games:
        parse_game(g, args.output_root, args.force)


if __name__ == "__main__":
    main()
