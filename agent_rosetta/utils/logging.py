from __future__ import annotations

import os
import sys
from pathlib import Path

from loguru import logger
from rich.console import Console

from agent_rosetta.utils.fs import get_root_dir

console = Console(file=sys.__stderr__)


def setup_log_dir(log_dir: Path | None = None) -> None:
    if log_dir is None:
        log_dir = get_root_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    os.environ["LOG_DIR"] = str(log_dir)


def setup_logger(
    log_dir: Path | None = None, filename: str = None, level: str = "DEBUG"
):
    logger_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level}</level> | "
        "<cyan>{file.name}:{line}</cyan> | "
        "{message}"
    )

    if not os.getenv("LOG_DIR"):
        setup_log_dir(log_dir=log_dir)
    log_dir = Path(os.getenv("LOG_DIR"))

    logfile = log_dir / filename
    if logfile.exists():
        logfile.unlink()

    logger.remove()
    logger.add(
        logfile,
        format=logger_format,
        level=level,
        enqueue=True,
        backtrace=True,
        diagnose=True,
        filter=lambda record: record["extra"].get("component") != "esmfold",
    )
