"""Acquire raw SportVU tracking archives and land them in bronze.

For each manifest game: download its `.7z` from the sealneaward repo, unzip it,
and write the raw tracking JSON to bronze (partitioned by season/game_id). The
`.7z` is transient and discarded after unzip. PBP-independent.

    python -m ingestion.download_tracking [--games ID ...] [--output-root PATH] [--force]
"""
from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import py7zr
import requests

from ingestion.common import Game, bronze_path, exists, load_manifest, write_bytes

TRACKING_URL = "https://github.com/sealneaward/nba-movement-data/raw/master/data/{filename}"


def _download(url: str, dest: Path) -> None:
    last_err = None
    for _ in range(2):  # one retry — transient network blips
        try:
            with requests.get(url, stream=True, timeout=60) as r:
                r.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=1 << 20):
                        f.write(chunk)
            return
        except requests.RequestException as e:
            last_err = e
    raise RuntimeError(f"download failed: {url}") from last_err


def _extract_json_bytes(archive: Path, workdir: Path) -> bytes:
    workdir.mkdir(parents=True, exist_ok=True)
    with py7zr.SevenZipFile(archive, "r") as z:
        z.extractall(path=workdir)
    json_files = list(workdir.rglob("*.json"))
    if len(json_files) != 1:
        raise RuntimeError(f"expected 1 json in {archive.name}, found {len(json_files)}")
    return json_files[0].read_bytes()


def fetch_game(game: Game, output_root: str, force: bool) -> None:
    dest = bronze_path(output_root, "tracking", game, f"{game.game_id}.json")
    if not force and exists(dest):
        print(f"  skip {game.game_id} (exists)")
        return
    url = TRACKING_URL.format(filename=game.tracking_filename)
    with tempfile.TemporaryDirectory() as tmp:  # .7z + extraction discarded on exit
        tmpdir = Path(tmp)
        archive = tmpdir / game.tracking_filename
        print(f"  {game.game_id}: downloading {game.tracking_filename} ...")
        _download(url, archive)
        data = _extract_json_bytes(archive, tmpdir / "extracted")
    write_bytes(dest, data)
    print(f"  {game.game_id}: wrote {len(data) / 1e6:.0f} MB -> {dest}")


def main() -> None:
    p = argparse.ArgumentParser(description="Download raw SportVU tracking to bronze.")
    p.add_argument("--games", nargs="*", help="game_id(s) to process (default: all in manifest)")
    p.add_argument("--output-root", default="./data", help="local dir or gs:// root")
    p.add_argument("--force", action="store_true", help="re-download even if bronze exists")
    args = p.parse_args()

    games = load_manifest(args.games)
    print(f"tracking: {len(games)} game(s)")
    for g in games:
        fetch_game(g, args.output_root, args.force)


if __name__ == "__main__":
    main()
