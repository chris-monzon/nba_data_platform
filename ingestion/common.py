"""Shared helpers for the ingestion extract scripts.

Loads the game manifest, builds bronze partition paths, and routes output writes
to local disk. GCS upload is a deliberate seam (see `write_bytes`): only the
output root differs (`./data` vs `gs://bucket`), so the same code lands bronze
locally now and on Cloud Run later — the `gs://` branch is filled in when the
bucket exists.
"""
from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from pathlib import Path

INGESTION_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = INGESTION_DIR / "games.csv"


@dataclass(frozen=True)
class Game:
    game_id: str          # canonical key, zero-padded (e.g. "0021500438")
    tracking_filename: str
    game_date: str
    away: str
    home: str
    season: str           # label, e.g. "2015-16"

    @property
    def season_start_year(self) -> int:
        return int(self.season[:4])  # "2015-16" -> 2015


def load_manifest(game_ids: list[str] | None = None) -> list[Game]:
    with open(MANIFEST_PATH, newline="") as f:
        games = [Game(**row) for row in csv.DictReader(f)]
    if game_ids:
        wanted = set(game_ids)
        games = [g for g in games if g.game_id in wanted]
        missing = wanted - {g.game_id for g in games}
        if missing:
            raise SystemExit(f"game_id(s) not in manifest: {sorted(missing)}")
    return games


def is_gcs(path: str) -> bool:
    return str(path).startswith("gs://")


def join_path(root: str, *parts: str) -> str:
    return "/".join([str(root).rstrip("/"), *parts])


def _partition_path(output_root: str, layer: str, dataset: str, game: Game, filename: str) -> str:
    return join_path(
        output_root, layer, dataset,
        f"season={game.season}", f"game_id={game.game_id}", filename,
    )


def bronze_path(output_root: str, source: str, game: Game, filename: str) -> str:
    """e.g. <root>/bronze/tracking/season=2015-16/game_id=0021500438/0021500438.json"""
    return _partition_path(output_root, "bronze", source, game, filename)


def silver_path(output_root: str, dataset: str, game: Game, filename: str) -> str:
    """e.g. <root>/silver/tracking_moment/season=2015-16/game_id=0021500438/moment.parquet"""
    return _partition_path(output_root, "silver", dataset, game, filename)


def exists(dest: str) -> bool:
    if is_gcs(dest):
        from google.cloud import storage
        bucket, _, blob = dest[len("gs://"):].partition("/")
        return storage.Client().bucket(bucket).blob(blob).exists()
    return os.path.exists(dest)


def read_bytes(src: str) -> bytes:
    """Read bytes from a local path or GCS. Mirror of write_bytes."""
    if is_gcs(src):
        from google.cloud import storage
        bucket, _, blob = src[len("gs://"):].partition("/")
        return storage.Client().bucket(bucket).blob(blob).download_as_bytes()
    with open(src, "rb") as f:
        return f.read()


def write_bytes(dest: str, data: bytes) -> None:
    """Write bytes to a local path or GCS. Only the root differs."""
    if is_gcs(dest):
        from google.cloud import storage
        bucket, _, blob = dest[len("gs://"):].partition("/")
        storage.Client().bucket(bucket).blob(blob).upload_from_string(data)
        return
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
