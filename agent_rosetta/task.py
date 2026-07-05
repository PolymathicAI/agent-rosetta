from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic

from .typing import TaskConfigT

if TYPE_CHECKING:
    from pathlib import Path

    from .agent import Agent
    from .history import History
    from .trajectory import Trajectory
    from .typing import EnvironmentT, Message, TrajectoryStep


@dataclass(frozen=True)
class TaskConfig:
    name: str = None
    prompt: str = None
    workdir: str = None


class Task(ABC, Generic[TaskConfigT]):
    def __init__(self, config: TaskConfigT, workdir: Path = None):
        self.config = config
        self.workdir = workdir

    @abstractmethod
    def setup(self, env: EnvironmentT) -> TrajectoryStep | None:
        pass

    @abstractmethod
    def build_history(
        self, env: EnvironmentT = None, agent: Agent | None = None
    ) -> History:
        pass

    @abstractmethod
    def build_next_step_message(
        self,
        env: EnvironmentT = None,
        agent: Agent | None = None,
        traj: Trajectory | None = None,
    ) -> Message:
        pass
