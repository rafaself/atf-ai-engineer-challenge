"""Install the image's prepared demo data before starting the container command."""

import os
import shutil
import sys
from pathlib import Path

from emporio_music.paths import DATA_DIRECTORY


def initialize_data(seed_directory: Path, data_directory: Path) -> None:
    """Refresh derived snapshots and source data; never touch conversations."""
    # Replace the whole generated index, including any old SQLite WAL/HNSW files.
    # No server is running yet; the image contains the complete prepared index.
    index = data_directory / "policies" / "policy-indexes"
    if index.exists():
        shutil.rmtree(index)
    for name in ("catalog", "operations", "policies"):
        shutil.copytree(
            seed_directory / name, data_directory / name, dirs_exist_ok=True
        )
    print(
        "Demo catalog, orders and policy index ready; conversation history preserved.",
        flush=True,
    )


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit(
            "Supply a container command to execute after data initialization"
        )
    initialize_data(Path("/opt/emporio-music/data"), DATA_DIRECTORY)
    os.execvp(sys.argv[1], sys.argv[1:])


if __name__ == "__main__":
    main()
