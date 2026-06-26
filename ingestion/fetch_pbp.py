"""Acquire play-by-play data (extract step).

Pulls PBP via the `nba_on_court` library for the same game set as the tracking
data, and lands it as Parquet in GCS bronze.

TODO:
  - resolve game list (same param as download_tracking)
  - fetch PBP via nba_on_court
  - write Parquet to gs://<bucket>/bronze/pbp/season=2015-16/game_id=<id>/
"""


def main() -> None:
    raise NotImplementedError("ingestion: fetch_pbp — see module docstring")


if __name__ == "__main__":
    main()
