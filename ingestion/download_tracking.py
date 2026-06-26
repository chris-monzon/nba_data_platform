"""Acquire raw SportVU tracking archives (extract step).

Downloads the 2015-16 tracking `.7z`/JSON archives from
https://github.com/sealneaward/nba-movement-data, unzips them, and lands the raw
JSON in GCS bronze (partitioned by `season/game_id`).

PBP-independent: this does NOT touch play-by-play data.

TODO:
  - resolve game list (param: list of game_ids or date range — do not hardcode)
  - download + unzip .7z archives (py7zr)
  - upload raw JSON to gs://<bucket>/bronze/season=2015-16/game_id=<id>/
  - make idempotent (skip games already present)
"""


def main() -> None:
    raise NotImplementedError("ingestion: download_tracking — see module docstring")


if __name__ == "__main__":
    main()
