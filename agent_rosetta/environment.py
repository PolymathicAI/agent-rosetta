from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic

from .typing import EnvironmentConfigT, EnvironmentStateT

if TYPE_CHECKING:
    from pydantic import BaseModel

    from .trajectory import Trajectory
    from .typing import ActionTag, TaskT


@dataclass(frozen=True)
class EnvironmentConfig:
    name: str = None
    system_prompt: str = None
    task_template: str = None

    docs_template: str | None = None
    refine_template: str | None = None
    debug_template: str | None = None
    timeout_template: str | None = None


class Environment(ABC, Generic[EnvironmentConfigT, EnvironmentStateT]):
    config: EnvironmentConfigT
    state: EnvironmentStateT

    def __init__(self, config: EnvironmentConfigT):
        self.config = config

    def get_state(self) -> EnvironmentStateT:
        return self.state.model_copy(deep=True)

    @abstractmethod
    def setup(self):
        pass

    @abstractmethod
    def reset(self):
        pass

    @abstractmethod
    def step(
        self,
        act_name: str = None,
        act_args: BaseModel = None,
        act_tag: ActionTag | None = None,
        task: TaskT | None = None,
        traj: Trajectory | None = None,
    ) -> EnvironmentStateT:
        pass
