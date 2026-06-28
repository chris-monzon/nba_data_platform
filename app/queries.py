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

# Only game 0021500438 has tracking-derived shot locations; game 0021500622's
# SportVU file is corrupt, so its shots are unlocated (left NULL in gold).
GAME_ID = "0021500438"


@st.cache_resource
def _client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT)


def _run(sql: str, params: list | None = None) -> pd.DataFrame:
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    return _client().query(sql, job_config=job_config).to_dataframe()


@st.cache_data(show_spinner=False)
def list_players() -> list[str]:
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
    df = _run(sql, [bigquery.ScalarQueryParameter("game_id", "STRING", GAME_ID)])
    return df["event_player_name"].tolist()


@st.cache_data(show_spinner=False)
def get_shots(player_name: str) -> pd.DataFrame:
    """Return one player's located shots (result/type filtering happens in-view)."""
    sql = f"""
        SELECT shooter_x, shooter_y, shot_made_flag, is_three, shot_distance,
               description, period, clock_display
        FROM `{GOLD_TABLE}`
        WHERE game_id = @game_id
          AND has_shot_location
          AND event_player_name = @player
        ORDER BY period, event_clock_seconds DESC
    """
    params = [
        bigquery.ScalarQueryParameter("game_id", "STRING", GAME_ID),
        bigquery.ScalarQueryParameter("player", "STRING", player_name),
    ]
    return _run(sql, params)
