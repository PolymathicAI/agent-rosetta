from __future__ import annotations

import subprocess
from pathlib import Path


def get_root_dir() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"Failed to get git root directory: {result.stderr}")
    return Path(result.stdout.strip())


def load_dotenv(dotenv_path: Path | None = None):
    from dotenv import load_dotenv as _load_dotenv

    if dotenv_path is None:
        dotenv_path = get_root_dir() / ".env"

    _load_dotenv(dotenv_path)
