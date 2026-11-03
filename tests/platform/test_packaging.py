"""Build and import the shared wheel without the repository on sys.path."""

import os
import subprocess
import sys
from pathlib import Path
from zipfile import ZipFile

from tests._support import REPOSITORY_ROOT


def test_shared_wheel_imports_outside_checkout_with_explicit_data_path(
    tmp_path: Path,
) -> None:
    wheel_directory = tmp_path / "wheels"
    wheel_directory.mkdir()
    subprocess.run(
        [
            "uv",
            "build",
            "--project",
            str(REPOSITORY_ROOT / "packages/emporio_music"),
            "--wheel",
            "--out-dir",
            str(wheel_directory),
        ],
        cwd=REPOSITORY_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    wheel = next(wheel_directory.glob("emporio_music-*.whl"))
    with ZipFile(wheel) as archive:
        wheel_paths = set(archive.namelist())
    assert "emporio_music/py.typed" in wheel_paths
    assert not any(
        path.startswith(("emporio_music_api/", "emporio_music_cli/"))
        for path in wheel_paths
    )
    install_directory = tmp_path / "installed"
    install_environment = os.environ.copy()
    install_environment["UV_CACHE_DIR"] = str(tmp_path / "install-cache")
    install_environment["UV_OFFLINE"] = "1"
    subprocess.run(
        [
            "uv",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(install_directory),
            str(wheel),
        ],
        cwd=tmp_path,
        env=install_environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    data_directory = tmp_path / "runtime-data"
    data_directory.mkdir()
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("AWS_")
    }
    environment["EMPORIO_MUSIC_DATA_DIR"] = str(data_directory)
    probe = (
        "import importlib.metadata, pathlib, sys; "
        "sys.path.insert(0, sys.argv[1]); "
        "import emporio_music; "
        "from emporio_music.paths import DATA_DIRECTORY; "
        "assert importlib.metadata.distribution('emporio-music').metadata['Name'] "
        "== 'emporio-music'; "
        "assert pathlib.Path(emporio_music.__file__).is_relative_to(sys.argv[1]); "
        "assert DATA_DIRECTORY == pathlib.Path(sys.argv[2]).resolve(); "
        "assert not {'fastapi', 'boto3', 'pydantic_ai'} & sys.modules.keys()"
    )
    subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            probe,
            str(install_directory),
            str(data_directory),
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
