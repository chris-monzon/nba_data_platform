"""Extract conformed dimensions from the SportVU tracking JSON header (nested -> tabular).

The tracking file's per-event header carries authoritative team meta + the full
roster (firstname/lastname/position/jersey) for both sides, plus the game date --
richer than the PBP, which only names event participants. We pull four silver
outputs PER GAME (same partition layout as parse_tracking), and the cross-game
DISTINCT (a player/team recurs across games) is left to transform/silver_dims.sql:

  - dim_player : player_id, first_name, last_name, position        (BIO ONLY -- no team)
  - dim_team   : team_id, abbreviation, full_name                  (conference added in SQL, NULL)
  - dim_game   : game_id, season_id, home_team_id, away_team_id, game_date
  - roster     : season_id, team_id, player_id                     (raw for the SCD2 bridge)

Why no team on dim_player: a player's team is time-varying (trades/seasons), so it
is not a static player attribute. Team-for-a-play comes from the facts; roster
history is the PLAYER_TEAM_SEASON SCD2 bridge that silver_dims.sql builds from
`roster`. See schema/CHANGES.md.

Nested JSON -> Python (same reason as parse_tracking); the SCD2 effective-dating is
declarative, so it lives in SQL. PBP-independent.

    python -m ingestion.parse_dims [--games ID ...] [--output-root PATH] [--force]
"""
from __future__ import annotations

import argparse
import io
import json

import pandas as pd

from ingestion.common import Game, bronze_path, exists, load_manifest, read_bytes, silver_path, write_bytes

# dataset -> output filename (each is per-game; SQL unions + dedups across games)
OUTPUTS = {
    "dim_player": "dim_player.parquet",
    "dim_team": "dim_team.parquet",
    "dim_game": "dim_game.parquet",
    "roster": "roster.parquet",
}


def _extract(raw: dict, game: Game) -> dict[str, pd.DataFrame]:
    """One game's tracking header -> the four dim/roster frames.

    Rosters are repeated in every event's header (constant per game), so the first
    event suffices. `home`/`visitor` carry team meta + a players[] list.
    """
    events = raw.get("events") or []
    if not events:
        raise RuntimeError(f"{game.game_id}: tracking JSON has no events")
    ev = events[0]
    season_id = game.season_start_year                  # 2015 ("2015-16")
    game_date = raw.get("gamedate")                      # "2015-12-25"

    teams, players, roster = [], [], []
    sides = {"home": ev["home"], "visitor": ev["visitor"]}
    for side in sides.values():
        teams.append((side["teamid"], side["abbreviation"], side["name"]))
        for p in side["players"]:
            players.append((p["playerid"], p["firstname"], p["lastname"], p["position"]))
            roster.append((season_id, side["teamid"], p["playerid"]))

    dim_game = pd.DataFrame(
        [(game.game_id, season_id, sides["home"]["teamid"], sides["visitor"]["teamid"], game_date)],
        columns=["game_id", "season_id", "home_team_id", "away_team_id", "game_date"],
    )
    dim_game["game_date"] = pd.to_datetime(dim_game["game_date"]).dt.date  # -> DATE in parquet

    return {
        "dim_player": pd.DataFrame(players, columns=["player_id", "first_name", "last_name", "position"]),
        "dim_team": pd.DataFrame(teams, columns=["team_id", "abbreviation", "full_name"]),
        "dim_game": dim_game,
        "roster": pd.DataFrame(roster, columns=["season_id", "team_id", "player_id"]),
    }


def _write_parquet(df: pd.DataFrame, dest: str) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    write_bytes(dest, buf.getvalue())


def _process(game: Game, output_root: str, force: bool) -> None:
    dests = {ds: silver_path(output_root, ds, game, fn) for ds, fn in OUTPUTS.items()}
    if not force and all(exists(d) for d in dests.values()):
        print(f"  skip {game.game_id} (exists)")
        return

    src = bronze_path(output_root, "tracking", game, f"{game.game_id}.json")
    print(f"  {game.game_id}: reading {src}")
    raw = json.loads(read_bytes(src))
    frames = _extract(raw, game)
    for ds, df in frames.items():
        _write_parquet(df, dests[ds])
    print(f"  {game.game_id}: players={len(frames['dim_player'])} "
          f"teams={len(frames['dim_team'])} roster={len(frames['roster'])} -> silver/")


def main() -> None:
    p = argparse.ArgumentParser(description="Extract silver dimensions from tracking JSON headers.")
    p.add_argument("--games", nargs="*", help="game_id(s) to process (default: all in manifest)")
    p.add_argument("--output-root", default="./data", help="local dir or gs:// root")
    p.add_argument("--force", action="store_true", help="re-write existing outputs")
    args = p.parse_args()

    games = load_manifest(args.games)
    print(f"dims: {len(games)} game(s)")
    for g in games:
        _process(g, args.output_root, args.force)


if __name__ == "__main__":
    main()
