"""Locate each PBP shot on the court from the SportVU ball trajectory.

WHY THIS EXISTS: a PBP shot's clock and the SportVU game_clock are NOT synced to the
second, so picking the tracking frame whose clock matches the PBP stamp lands ~9 ft from
the real shot (on transition plays, up to 40 ft — the shooter has already run off). The fix
is to ignore the clock for *locating* the shot and instead read it off the ball's flight:
find the frame where the ball passes through the rim, then back up to the release (when the
ball leaves the shooter's hands). Verified against PBP's own stated distances: median error
drops from ~9 ft (clock match) to ~2 ft.

This is inherently per-shot trajectory analysis over the *un-deduped* per-event moment
windows, so it lives in Python (walking the raw JSON), like parse_tracking — not SQL. It
emits release COORDINATES only; the distance/zone geometry stays in gold.

`eventId` in the SportVU JSON == PBP EVENTNUM (verified 1:1), and is used only to SCOPE
each shot to its own moment window.

    python -m ingestion.parse_shot_locations [--games ID ...] [--output-root PATH] [--force]
"""
from __future__ import annotations

import argparse
import io
import json

import pandas as pd

from ingestion.common import (
    Game, bronze_path, exists, load_manifest, read_bytes, silver_path, write_bytes,
)

SHOT_LOCATION_FILE = "shot_location.parquet"

# Rim centers on the 94x50 ft SportVU court (origin at a corner). Used ONLY to find the
# ball-at-rim frame; the authoritative distance/zone geometry is computed in gold.
HOOPS = ((5.25, 25.0), (88.75, 25.0))
RIM_Z = (8.0, 12.0)          # ball height band (ft) that brackets the rim (10 ft)
RELEASE_LOOKBACK_S = 2.5     # search this many seconds before the rim frame for the release


def _ball(moment: list):
    for team_id, pid, x, y, z in moment[5]:
        if pid == -1:
            return x, y, z
    return None


def _player(moment: list, pid: int):
    for _team, p, x, y, _z in moment[5]:
        if p == pid:
            return x, y
    return None


def _hoop_dist(x: float, y: float) -> float:
    return min(((x - hx) ** 2 + (y - hy) ** 2) ** 0.5 for hx, hy in HOOPS)


def _locate_shot(moments: list, shooter_id: int) -> dict | None:
    """Detect the release frame from the ball arc; return shooter & ball position there.

    Returns None when the shot can't be located (no ball-at-rim frame in the window, or the
    shooter isn't tracked near release) -- caller emits a NULL-location row.
    """
    if not moments:
        return None
    # 1) ball-at-rim frame: ball near rim height, closest horizontally to a hoop.
    rim_i, rim_d = None, 1e9
    for i, m in enumerate(moments):
        b = _ball(m)
        if b and RIM_Z[0] <= b[2] <= RIM_Z[1]:
            d = _hoop_dist(b[0], b[1])
            if d < rim_d:
                rim_d, rim_i = d, i
    if rim_i is None:
        return None
    rim_clock = moments[rim_i][2]
    # 2) release: in the window just BEFORE the ball reaches the rim (higher game_clock),
    #    the frame where the ball is closest to the shooter (ball still in hand).
    rel_i, rel_d = None, 1e9
    for i, m in enumerate(moments):
        if not (0 <= (m[2] - rim_clock) <= RELEASE_LOOKBACK_S):
            continue
        b, p = _ball(m), _player(m, shooter_id)
        if b and p:
            d = ((b[0] - p[0]) ** 2 + (b[1] - p[1]) ** 2) ** 0.5
            if d < rel_d:
                rel_d, rel_i = d, i
    if rel_i is None:
        return None
    m = moments[rel_i]
    p, b = _player(m, shooter_id), _ball(m)
    return {
        "shooter_x": p[0], "shooter_y": p[1],
        "ball_x": b[0], "ball_y": b[1],
        "release_game_clock": m[2],
    }


def _shots_from_pbp(output_root: str, game: Game) -> pd.DataFrame:
    """Bronze PBP -> the field-goal attempts (made/missed) with a real shooter."""
    raw = read_bytes(bronze_path(output_root, "pbp", game, "pbp.parquet"))
    df = pd.read_parquet(io.BytesIO(raw))
    df = df[df["EVENTMSGTYPE"].isin([1, 2]) & df["PERSON1TYPE"].isin([4, 5])].copy()
    df["event_id"] = df["EVENTNUM"].astype(int)
    df["shot_player_id"] = df["PLAYER1_ID"].astype(int)
    df["shot_made_flag"] = df["EVENTMSGTYPE"] == 1
    return df[["event_id", "shot_player_id", "shot_made_flag"]]


def parse_game(game: Game, output_root: str, force: bool) -> None:
    dest = silver_path(output_root, "shot_location", game, SHOT_LOCATION_FILE)
    if not force and exists(dest):
        print(f"  skip {game.game_id} (exists)")
        return

    raw = json.loads(read_bytes(bronze_path(output_root, "tracking", game, f"{game.game_id}.json")))
    moments_by_event = {int(e["eventId"]): (e.get("moments") or []) for e in raw["events"]}
    shots = _shots_from_pbp(output_root, game)

    rows = []
    located = 0
    for s in shots.itertuples(index=False):
        loc = _locate_shot(moments_by_event.get(s.event_id, []), s.shot_player_id)
        row = {"game_id": game.game_id, "event_id": s.event_id,
               "shot_player_id": s.shot_player_id, "shot_made_flag": s.shot_made_flag,
               "shooter_x": None, "shooter_y": None, "ball_x": None, "ball_y": None,
               "release_game_clock": None}
        if loc:
            row.update(loc)
            located += 1
        rows.append(row)

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    write_bytes(dest, buf.getvalue())
    print(f"  {game.game_id}: {len(df)} shots, located {located} ({located*100//max(len(df),1)}%) -> {dest}")


def main() -> None:
    p = argparse.ArgumentParser(description="Locate PBP shots from SportVU ball trajectory.")
    p.add_argument("--games", nargs="*", help="game_id(s) (default: all in manifest)")
    p.add_argument("--output-root", default="./data", help="local dir or gs:// root")
    p.add_argument("--force", action="store_true", help="recompute even if silver exists")
    args = p.parse_args()

    games = load_manifest(args.games)
    print(f"parse_shot_locations: {len(games)} game(s)")
    for g in games:
        parse_game(g, args.output_root, args.force)


if __name__ == "__main__":
    main()
