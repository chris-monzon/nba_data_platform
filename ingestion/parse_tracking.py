"""Parse raw tracking JSON into tabular moments (structural reshape).

Explodes the nested ~25 Hz SportVU JSON for ONE game into flat rows
(ball + 10 player positions per moment) and writes Parquet to GCS silver.

Per-game and idempotent (keyed by season/game_id). PBP-independent — the join to
events happens later in BigQuery (transform/).

Keep full 25 Hz here (no time-downsampling) so the downstream event-time join
stays precise.

TODO:
  - read raw JSON for a single game_id from GCS bronze
  - explode events -> moments -> (ball xyz + player xy) rows
  - write Parquet to gs://<bucket>/silver/tracking/season=2015-16/game_id=<id>/
"""


def parse_game(game_id: str) -> None:
    """Parse a single game's tracking JSON -> tabular Parquet. Idempotent."""
    raise NotImplementedError("ingestion: parse_tracking.parse_game — see module docstring")


def main() -> None:
    raise NotImplementedError("ingestion: parse_tracking — wire up game list -> parse_game")


if __name__ == "__main__":
    main()
