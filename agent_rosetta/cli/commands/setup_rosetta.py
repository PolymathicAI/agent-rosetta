from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import click

from agent_rosetta.cli.constants import ROSETTASCRIPTS_BINARIES
from agent_rosetta.cli.logging import log_error, log_info, log_success, log_warning

from .common import get_config_dir

if TYPE_CHECKING:
    from agent_rosetta.cli.typing import rosettascripts_mode


def resolve_bin(bin_name: str) -> str | None:
    return shutil.which(bin_name) or shutil.which(Path(bin_name).expanduser())


def get_rosettascripts_bin(mode: rosettascripts_mode) -> str:
    bin_name = click.prompt(
        f"- {mode} executable", default=ROSETTASCRIPTS_BINARIES[mode]
    )
    resolved = resolve_bin(bin_name)
    if not resolved:
        log_error(
            f"Could not resolve '{bin_name}'. Please ensure the binary is in PATH or provide a full valid path."
        )
        raise click.Abort()
    log_success(f"{mode} binary resolved to '{resolved}'")
    return resolved


def setup_rosetta():
    log_info("Setting up RosettaScripts binaries...")
    log_info()

    ### RosettaScripts disclaimer ###
    log_warning(
        "Agent Rosetta uses RosettaScripts, which is part of the Rosetta software suite developed by the Rosetta Commons. Please visit https://github.com/RosettaCommons/rosetta/blob/main/LICENSE.md to agree to Rosetta's licence and download the Rosetta software."
    )
    log_info()

    config_dir = get_config_dir()

    ### RosettaScripts paths ###
    log_info("Please enter the RosettaScripts binaries (if in PATH) or full paths.")
    resolved_rosettascripts_bins = {
        mode: get_rosettascripts_bin(mode) for mode in ROSETTASCRIPTS_BINARIES.keys()
    }
    log_info()

    config_path = config_dir / "config.json"
    with config_path.open("r") as f:
        config = json.load(f)

    config["rosettascripts_binaries"] = resolved_rosettascripts_bins
    try:
        with config_path.open("w") as f:
            json.dump(config, f, indent=4)
        log_success(f"RosettaScripts configuration saved to '{config_path}'")
    except Exception as e:
        log_error(f"Failed to save configuration file to '{config_path}': {e}")
        raise click.Abort()
