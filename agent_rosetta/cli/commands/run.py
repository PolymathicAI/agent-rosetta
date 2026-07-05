from __future__ import annotations

import json
import os
import time
from typing import TYPE_CHECKING

from hydra import compose, initialize_config_dir
from hydra.utils import instantiate

from agent_rosetta.cli.commands.common import sanitize_path
from agent_rosetta.cli.constants import AGR_CONFIG_DIR, AGR_PDB_DIR
from agent_rosetta.utils.fs import load_dotenv
from agent_rosetta.utils.logging import console, logger, setup_logger

if TYPE_CHECKING:
    from pathlib import Path

    from omegaconf import DictConfig

    from agent_rosetta.runner import Runner


def load_agr_config():
    with (AGR_CONFIG_DIR / "config.json").open("r") as f:
        config = json.load(f)

    rosettascripts_binaries = config.get("rosettascripts_binaries", {})
    for mode, path in rosettascripts_binaries.items():
        os.environ[f"AGR_ROSETTASCRIPTS_{mode.upper()}_BIN"] = path

    llm_providers = config.get("llm_providers", {})
    for _, provider_env_vars in llm_providers.items():
        for env_var, value in provider_env_vars.items():
            os.environ[env_var] = value

    default_model = config.get("default_model")
    if default_model:
        os.environ["AGR_DEFAULT_MODEL"] = default_model


def compose_hydra_config(config_path: Path) -> DictConfig:
    config_dir = str(config_path.parent.absolute())
    config_name = config_path.stem

    with initialize_config_dir(config_dir=config_dir, version_base=None):
        config = compose(config_name=config_name, return_hydra_config=True)
    choices = config.hydra.runtime.choices
    return config, choices


def run(config_path: Path = None, output_dir: Path = None):
    load_agr_config()
    load_dotenv()
    os.environ["AGR_PDB_DIR"] = str(AGR_PDB_DIR)

    config, choices = compose_hydra_config(config_path)

    console.print(
        f"Running agent [blue]{config.model.config.name}[/blue] on config [blue]{config.name}[/blue]",
        style="grey37",
    )

    now = time.strftime("%Y-%m-%dT%H-%M-%S")
    workdir = (
        output_dir
        / sanitize_path(config.name)
        / sanitize_path(choices.get("model"))
        / now
    )
    workdir.mkdir(parents=True, exist_ok=True)
    console.print(f"Working directory: {workdir}", style="grey37")

    setup_logger(log_dir=workdir / "logs", filename="main.log", level="DEBUG")
    logger.info(f"Running agent {config.model.config.name} on config {config.name}")

    runner: Runner = instantiate(config.runner)
    runner.setup(
        env_config=config.environment,
        task_config=config.task,
        model_config=config.model,
        parser_config=config.parser,
        workdir=workdir,
    )
    runner.run()

    runner.save(output_dir=workdir)
    console.print("All outputs saved", style="grey37")
