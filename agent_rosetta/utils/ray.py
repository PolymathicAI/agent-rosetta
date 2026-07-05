from __future__ import annotations

import ray
from ray.exceptions import GetTimeoutError

from agent_rosetta.utils.logging import logger

NAMESPACE = "agent-rosetta"


def setup(num_cpus: int = None, num_gpus: int = None, log_dir: str = None) -> None:
    logger.info(
        f"Setting up Ray cluster with namespace={NAMESPACE}, num_cpus={num_cpus}, num_gpus={num_gpus}..."
    )
    if ray.is_initialized():
        logger.warning(
            "Ray is already initialized. Shutting down existing Ray cluster..."
        )
        ray.shutdown()

    try:
        ray.init(
            namespace=NAMESPACE,
            num_cpus=num_cpus,
            num_gpus=num_gpus,
            runtime_env={
                "env_vars": {"LOG_DIR": log_dir},
                "working_dir": "./",
                "excludes": ["./external", "./scripts"],
            },
        )

        @ray.remote
        def health_check():
            return "healthy"

        logger.info("Waiting for Ray cluster to be ready...")
        status = ray.get(health_check.remote(), timeout=100)
        if status == "healthy":
            logger.info("Ray cluster is ready.")
    except GetTimeoutError as e:
        raise RuntimeError(
            "Ray cluster failed to initialize within the expected time"
        ) from e
    except Exception as e:
        ray.shutdown()
        raise RuntimeError("Ray cluster setup failed.") from e
