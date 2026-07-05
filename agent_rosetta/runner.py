from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic

from hydra.utils import instantiate
from rich.text import Text

from .agent import Agent
from .trajectory import Trajectory
from .typing import RunnerConfigT
from .utils.logging import console, logger

if TYPE_CHECKING:
    from pathlib import Path

    from omegaconf import DictConfig

    from .typing import EnvironmentT, ModelT, ParserT, TaskT


@dataclass(frozen=True)
class RunnerConfig:
    name: str = None
    max_steps: int = None


class Runner(ABC, Generic[RunnerConfigT]):
    def __init__(self, config: RunnerConfigT):
        self.config = config

        self.env: EnvironmentT = None
        self.task: TaskT = None
        self.trajectory: Trajectory = None
        self.agent: Agent = None

    def setup(
        self,
        env_config: DictConfig = None,
        task_config: DictConfig = None,
        model_config: DictConfig = None,
        parser_config: DictConfig = None,
        workdir: Path = None,
    ):
        logger.info("Initializing environment")
        with console.status(
            Text("Initializing environment", style="grey37"),
            spinner="dots",
            spinner_style="grey37",
        ):
            env: EnvironmentT = instantiate(env_config)

            env.setup()
            env.reset()
            self.env = env
        console.print(":heavy_check_mark: Initialized environment", style="grey37")

        logger.info("Initializing task")
        with console.status(
            Text("Initializing task", style="grey37"),
            spinner="dots",
            spinner_style="grey37",
        ):
            task: TaskT = instantiate(task_config, workdir=workdir)

            step = task.setup(self.env)
            trajectory = Trajectory()
            if step:
                trajectory.add(step)

            self.task = task
            self.trajectory = trajectory
        console.print(":heavy_check_mark: Initialized task", style="grey37")

        logger.info("Initializing agent")
        with console.status(
            Text("Initializing agent", style="grey37"),
            spinner="dots",
            spinner_style="grey37",
        ):
            model: ModelT = instantiate(model_config)
            parser: ParserT = instantiate(parser_config)

            agent = Agent(model=model, parser=parser)
            agent.setup(env=self.env, task=self.task)
            self.agent = agent
        console.print(":heavy_check_mark: Initialized agent", style="grey37")

    @abstractmethod
    def run(self):
        pass

    def save(self, output_dir: Path):
        self.trajectory.save(output_dir / "trajectory.json")
