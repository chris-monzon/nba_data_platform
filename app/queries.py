"""Gold-layer data access for the shot-map dashboard.

Thin BigQuery client over the event-grain serving mart. All table/column names
live here; functions return pandas DataFrames. No Streamlit UI or plotting.

Results are cached with ``st.cache_data`` because BigQuery carries a ~1s fixed
per-query latency — the dataset is a static snapshot, so caching is safe.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from google.cloud import bigquery

PROJECT = "nba-data-architecture"
GOLD_TABLE = f"{PROJECT}.nba_gold.events_with_location"
SILVER = f"{PROJECT}.nba_silver"

# Games are discovered at runtime from the gold layer (any game with at least
# one tracking-located shot), so ingesting another game surfaces it in the
# picker with no code change. Games without located shots simply never appear
# (e.g. 0021500622, whose SportVU file is corrupt).


@st.cache_resource
def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT)


def _run(sql: str, params: list | None = None) -> pd.DataFrame:
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    return _client().query(sql, job_config=job_config).to_dataframe()


@st.cache_data(show_spinner=False)
def list_games() -> list[dict]:
    """Games that have at least one located shot, oldest first.

    Each entry is ``{"game_id", "label"}`` where label is "AWAY @ HOME · DATE",
    derived from the silver dims so the picker is fully table-driven.
    """
    sql = f"""
        SELECT e.game_id,
               CONCAT(a.abbreviation, ' @ ', h.abbreviation, ' · ',
                      CAST(g.game_date AS STRING)) AS label
        FROM `{GOLD_TABLE}` e
        JOIN `{SILVER}.dim_game` g ON e.game_id = g.game_id
        JOIN `{SILVER}.dim_team` h ON g.home_team_id = h.team_id
        JOIN `{SILVER}.dim_team` a ON g.away_team_id = a.team_id
        WHERE e.has_shot_location
        GROUP BY e.game_id, label, g.game_date
        ORDER BY g.game_date
    """
    return _run(sql).to_dict("records")


@st.cache_data(show_spinner=False)
def list_players(game_id: str) -> list[str]:
    """Full roster of players who acted in the game, most shots first.

    Includes players with zero located shots (the view shows a 0 counter for
    them so an empty chart reads as intentional, not a bug).
    """
    sql = f"""
        SELECT event_player_name
        FROM `{GOLD_TABLE}`
        WHERE game_id = @game_id AND event_player_name IS NOT NULL
        GROUP BY event_player_name
        ORDER BY COUNTIF(has_shot_location) DESC, event_player_name
    """
    df = _run(sql, [bigquery.ScalarQueryParameter("game_id", "STRING", game_id)])
    return df["event_player_name"].tolist()


@st.cache_data(show_spinner=False, max_entries=16)
def get_shots(game_id: str) -> pd.DataFrame:
    """Return ALL located shots for one game (one cached frame per game).

    The view filters this frame by player / result / shot type in-memory, so
    every selection after a game first loads is instant — no BQ round trip.
    Latency is paid once per game; it stays flat as games are added, since the
    query is game-scoped and gold clusters by game_id. ``max_entries`` caps the
    cache at 16 games (LRU eviction) so it can never grow unbounded.
    """
    sql = f"""
        SELECT event_player_name, shooter_x, shooter_y, shot_made_flag,
               is_three, shot_distance, description, period, clock_display
        FROM `{GOLD_TABLE}`
        WHERE game_id = @game_id AND has_shot_location
        ORDER BY period, event_clock_seconds DESC
    """
    return _run(sql, [bigquery.ScalarQueryParameter("game_id", "STRING", game_id)])
