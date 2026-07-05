from __future__ import annotations

import subprocess
import time
from typing import TYPE_CHECKING

from agent_rosetta.utils.logging import logger

if TYPE_CHECKING:
    from pathlib import Path

    from environments.rosetta.typing import RosettaCmdResults


def is_resource_error(stderr: str = None) -> bool:
    messages = [
        "There are not enough slots available in the system",
    ]
    for message in messages:
        if message in stderr:
            return True
    return False


def is_transport_error(stdout: str = None, stderr: str = None) -> bool:
    messages = ["Transport retry count exceeded"]
    for message in messages:
        if message in stderr or message in stdout:
            return True
    return False


def is_backbone_mover_error(stdout: str = None, stderr: str = None) -> bool:
    messages = ["no movable positions in"]
    for message in messages:
        if message in stdout or message in stderr:
            return True
    return False


def classify_runtime_error(
    stdout_path: Path = None, stderr_path: Path = None
) -> RosettaCmdResults:
    with stdout_path.open("r") as f:
        stdout = f.read()
    with stderr_path.open("r") as f:
        stderr = f.read()

    if is_resource_error(stderr=stderr):
        return "resource_error", stderr
    if is_transport_error(stdout=stdout, stderr=stderr):
        return "transport_error", stderr
    if is_backbone_mover_error(stdout=stdout, stderr=stderr):
        return ("runtime_error", "Backbone mover failed: no movable positions found.")
    return "runtime_error", stderr


def is_sbatch_resource_error(sbatch_stderr: str = None) -> bool:
    messages = [
        "sbatch: unrecognized option",
        "Batch job submission failed: Invalid partition name specified",
        "Batch job submission failed: Job violates accounting/QOS policy",
        "Batch job submission failed: More processors requested than permitted",
    ]
    for message in messages:
        if message in sbatch_stderr:
            return True
    return False


def classify_sbatch_error(sbatch_stderr_path: Path = None) -> RosettaCmdResults:
    with sbatch_stderr_path.open("r") as f:
        sbatch_stderr = f.read()

    if is_sbatch_resource_error(sbatch_stderr=sbatch_stderr):
        return "resource_error", sbatch_stderr
    if sbatch_stderr.strip():
        return "runtime_error", sbatch_stderr
    return "runtime_error", None


def run_cmd(
    cmd: list[str] = None,
    stdout_path: Path = None,
    stderr_path: Path = None,
    timeout: float = None,
) -> RosettaCmdResults:
    with stdout_path.open("w") as stdout_file, stderr_path.open("w") as stderr_file:
        try:
            subprocess.run(
                cmd,
                stdout=stdout_file,
                stderr=stderr_file,
                timeout=timeout,
                text=True,
                check=True,
            )
            return "success", None
        except subprocess.CalledProcessError:
            return "runtime_error", None
        except subprocess.TimeoutExpired:
            return (
                "timeout",
                f"Command timed out after {timeout:.3f} seconds.",
            )
        except Exception as e:
            return "runtime_error", str(e)


def run_cmd_local(
    cmd_path: Path = None,
    stdout_path: Path = None,
    stderr_path: Path = None,
    timeout: float = None,
) -> RosettaCmdResults:
    cmd = [cmd_path]
    status_code, error_message = run_cmd(
        cmd=cmd, stdout_path=stdout_path, stderr_path=stderr_path, timeout=timeout
    )

    if status_code == "success":
        return status_code, error_message

    if error_message is not None:
        return status_code, error_message

    status_code, error_message = classify_runtime_error(
        stdout_path=stdout_path, stderr_path=stderr_path
    )
    return status_code, error_message


def run_cmd_slurm(
    cmd_path: Path = None,
    stdout_path: Path = None,
    stderr_path: Path = None,
    timeout: float = None,
    max_retries: int = None,
    delay: int = None,
) -> RosettaCmdResults:
    sbatch_stdout_path = stdout_path.with_name(stdout_path.stem + "_sbatch.log")
    sbatch_stderr_path = stderr_path.with_name(stderr_path.stem + "_sbatch.log")

    cmd = [
        "sbatch",
        "--parsable",
        "--wait",
        f"--output={stdout_path}",
        f"--error={stderr_path}",
        cmd_path,
    ]

    retries = 0
    while retries <= max_retries:
        status_code, error_message = run_cmd(
            cmd=cmd,
            stdout_path=sbatch_stdout_path,
            stderr_path=sbatch_stderr_path,
            timeout=timeout,
        )

        if status_code == "success":
            return status_code, error_message

        if error_message is not None:
            return status_code, error_message

        status_code, error_message = classify_sbatch_error(
            sbatch_stderr_path=sbatch_stderr_path
        )

        if error_message is not None:
            return status_code, error_message

        status_code, error_message = classify_runtime_error(
            stdout_path=stdout_path, stderr_path=stderr_path
        )

        if status_code == "transport_error":
            retries += 1
            logger.warning(
                f"There was a network transport error. Retrying command in {delay:.0f} seconds... (retry {retries}/{max_retries})"
            )
            time.sleep(delay)
            continue

        return status_code, error_message
    raise RuntimeError(
        f"Command failed after {max_retries} retries due to transport errors. Last error message: {error_message}"
    )
