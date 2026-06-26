"""Gold-layer data access for the dashboard.

Keeps all table/column names in one place. Functions return DataFrames; no
Streamlit or plotting code here.

TODO:
  - connect to BigQuery (google-cloud-bigquery)
  - list_players(), list_event_types()
  - get_player_events(player_id, event_type, game_id=None) -> DataFrame
"""

from __future__ import annotations

GOLD_TABLE = "events_with_location"  # TODO: confirm name once schema is finalized


def get_player_events(player_id: int, event_type: str, game_id: int | None = None):
    """Return events (with court x, y) for a player + event type."""
    raise NotImplementedError("app.queries.get_player_events — see module docstring")
