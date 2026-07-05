from __future__ import annotations

from typing import TYPE_CHECKING

import ray

from agent_rosetta.utils.logging import logger
from agent_rosetta.utils.ray import NAMESPACE

from .esmfold import ESMFold

if TYPE_CHECKING:
    from ray.actor import ActorHandle


ACTOR_NAME = "esmfold"


@ray.remote(num_cpus=1, num_gpus=1)
class ESMFoldActor:
    def __init__(self, device: str = "cuda:0"):
        self.model = ESMFold(device=device, log_filename="esmfold.log")

    def ping(self) -> str:
        return "pong"

    def predict_pdb(
        self, sequences: list[str], batch_size: int = None
    ) -> tuple[list[str], list[float]]:
        return self.model.predict_pdb(sequences=sequences, batch_size=batch_size)


def get_actor() -> ActorHandle:
    logger.info(
        f"Attempting to connect to ESMFoldActor '{ACTOR_NAME}' in '{NAMESPACE}'..."
    )
    assert ray.is_initialized(), "Ray must be initialized to get ESMFoldActor."

    try:
        actor_ref = ray.get_actor(ACTOR_NAME, namespace=NAMESPACE)
        pong = ray.get(actor_ref.ping.remote(), timeout=300)
        assert pong == "pong"
        logger.info("Successfully connected to ESMFoldActor")
        return actor_ref
    except ValueError as e:
        raise RuntimeError(
            "ESMFoldActor is not available. Please run setup() first."
        ) from e


def setup() -> None:
    logger.info(f"Setting up ESMFoldActor '{ACTOR_NAME}' in '{NAMESPACE}'...")
    assert ray.is_initialized(), (
        "Ray must be initialized before setting up ESMFoldActor."
    )

    _ = ESMFoldActor.options(
        namespace=NAMESPACE, name=ACTOR_NAME, lifetime="detached"
    ).remote()
    try:
        actor_ref = ray.get_actor(ACTOR_NAME, namespace=NAMESPACE)
        pong = ray.get(actor_ref.ping.remote(), timeout=300)
        assert pong == "pong"
        logger.info("ESMFoldActor is ready to use.")
    except Exception as e:
        ray.kill(actor_ref)
        raise RuntimeError("Failed to launch ESMFoldActor.") from e
