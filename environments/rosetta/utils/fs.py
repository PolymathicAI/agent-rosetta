from __future__ import annotations

# import os
import shutil
import subprocess
import tarfile
from typing import TYPE_CHECKING

from agent_rosetta.utils.logging import logger

if TYPE_CHECKING:
    from pathlib import Path


def verify_file_count(tar_path: Path = None, expected_count: int = None) -> bool:
    try:
        with tarfile.open(tar_path, "r:gz") as tar:
            archive_count = sum(1 for m in tar.getmembers() if m.isfile())
            return archive_count == expected_count
    except:
        return False


def compress_designs(design_dir: Path) -> bool:
    logger.info(f"Compressing designs in {design_dir}...")
    tar_path = design_dir.with_suffix(".tar.gz")

    file_count = sum(1 for _, _, files in design_dir.walk() for _ in files)

    try:
        subprocess.run(
            [
                "tar",
                "-czf",
                tar_path,
                "-C",
                design_dir.parent,
                design_dir.name,
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        assert verify_file_count(tar_path=tar_path, expected_count=file_count), (
            f"Verification failed for {tar_path}. Expected {file_count} files."
        )
        logger.info(
            f"Successfully compressed and verified {file_count} designs. Removing original directory..."
        )
        shutil.rmtree(design_dir)
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error during compression: {e.stderr}")
        return False
    except AssertionError as e:
        logger.error(str(e) + " Removing corrupted archive.")
        if tar_path.exists():
            tar_path.unlink()
        return False
