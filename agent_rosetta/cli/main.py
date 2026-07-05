from pathlib import Path

import click

from .commands.run import run as _run
from .commands.setup import setup as _setup
from .commands.setup_rosetta import setup_rosetta as _setup_rosetta
from .constants import AGR_OUTPUT_DIR


@click.group()
@click.version_option()
def main():
    """Agent Rosetta - An LLM-agent to execute protein design tasks with RosettaScripts."""
    pass


@main.command()
def setup():
    """Set up Agent Rosetta."""

    _setup()


@main.command()
def setup_rosetta():
    """Set up paths to RosettaScripts binaries."""

    _setup_rosetta()


@main.command()
@click.argument(
    "config",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
)
@click.option(
    "--output-dir",
    type=click.Path(exists=False, file_okay=False, path_type=Path),
    required=False,
    default=AGR_OUTPUT_DIR,
    help="Directory to save outputs",
)
def run(config: Path, output_dir: Path = None):
    """Run Agent Rosetta."""

    _run(config_path=config, output_dir=output_dir)


if __name__ == "__main__":
    main()
