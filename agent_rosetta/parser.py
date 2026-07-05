from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic

from .typing import ParserConfigT

if TYPE_CHECKING:
    from .typing import EnvironmentT, ParserOutput, TaskT


@dataclass(frozen=True)
class ParserConfig:
    name: str = None
    max_parse_retries: int = None
    parsing_error_template: str = None


class Parser(ABC, Generic[ParserConfigT]):
    def __init__(self, config: ParserConfigT):
        self.config = config

    @abstractmethod
    def setup(self, env: EnvironmentT | None = None, task: TaskT | None = None):
        pass

    @abstractmethod
    def parse(self, content: str) -> ParserOutput:
        pass
