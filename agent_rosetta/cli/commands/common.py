from __future__ import annotations

import re
from typing import TYPE_CHECKING

import click

from agent_rosetta.cli.constants import AGR_CONFIG_DIR
from agent_rosetta.cli.logging import log_error, log_info, log_success

if TYPE_CHECKING:
    from pathlib import Path


def get_config_dir() -> Path:
    default_config_dir = AGR_CONFIG_DIR
    log_info(f"Configuration files will be stored in '{default_config_dir}'")
    click.confirm("Do you want to continue?", default=True, abort=True)
    try:
        default_config_dir.mkdir(parents=True, exist_ok=True)
        log_success("Configuration directory created successfully")
    except Exception as e:
        log_error(f"Failed to create configuration directory: {e}")
        raise click.Abort()
    log_info()
    return default_config_dir


def sanitize_path(value: str) -> str:
    value = value.lower().strip().replace(" ", "-")
    return re.sub(r'[<>:"/\\|?*]', "-", value)
