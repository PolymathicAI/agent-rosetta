from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias

Metric: TypeAlias = Literal[
    "cavity_volume",
    "radius_of_gyration",
    "buns",
    "res_fa_rep",
    "res_rama_prepro",
    "core_residues",
]


@dataclass(frozen=True)
class TaskMetricConfig:
    score_weights: str | None = None
    residue_selectors: str | None = None
    simple_metrics: str | None = None
    filters: str | None = None
    movers: str | None = None
    protocols: str | None = None


@dataclass(frozen=True)
class TaskMetricConfigList:
    configs: list[TaskMetricConfig]

    def _collect(self, attr: str) -> list[str]:
        return [getattr(c, attr) for c in self.configs if getattr(c, attr) is not None]

    @property
    def score_weights(self) -> list[str]:
        return self._collect("score_weights")

    @property
    def residue_selectors(self) -> list[str]:
        return self._collect("residue_selectors")

    @property
    def simple_metrics(self) -> list[str]:
        return self._collect("simple_metrics")

    @property
    def filters(self) -> list[str]:
        return self._collect("filters")

    @property
    def movers(self) -> list[str]:
        return self._collect("movers")

    @property
    def protocols(self) -> list[str]:
        return self._collect("protocols")


class TaskMetric(Protocol):
    def __call__(self) -> TaskMetricConfig: ...


@dataclass(frozen=True)
class NCAAConfig:
    name: str
    code3: str
    description: str
