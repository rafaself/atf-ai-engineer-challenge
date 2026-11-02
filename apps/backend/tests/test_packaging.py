"""Exercise the installed distribution without relying on the source directory."""

import os
import subprocess
import sys
from pathlib import Path


def test_installed_package_imports_without_aws_configuration(tmp_path: Path) -> None:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("AWS_")
    }
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import sys; import emporio_music_backend; "
            "from importlib.metadata import distribution; "
            "package = distribution('emporio-music-backend'); "
            "assert package.metadata['Name'] == 'emporio-music-backend'; "
            "assert not {'boto3', 'botocore', 'pydantic_ai', 'fastapi'} & sys.modules.keys(); "
            "print(package.version)",
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
    assert result.stdout.strip()


def test_installed_package_resolves_readable_and_writable_project_data(
    tmp_path: Path,
) -> None:
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("AWS_")
    }
    source = (
        "from pathlib import Path; from tempfile import NamedTemporaryFile; "
        "from emporio_music_backend.paths import DATA_DIRECTORY; "
        "assert (DATA_DIRECTORY / 'products.csv').is_file(); "
        "probe = NamedTemporaryFile(prefix='.packaging-smoke-', dir=DATA_DIRECTORY); "
        "probe.write(b'packaging smoke'); probe.flush(); "
        "assert Path(probe.name).read_bytes() == b'packaging smoke'; probe.close()"
    )
    subprocess.run(
        [sys.executable, "-I", "-c", source],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
        check=True,
    )
