"""Explicit location for the separately built React application assets."""

import os
from pathlib import Path

FRONTEND_DIRECTORY = (
    Path(os.environ.get("EMPORIO_MUSIC_FRONTEND_DIR", "apps/frontend/dist"))
    .expanduser()
    .resolve()
)
