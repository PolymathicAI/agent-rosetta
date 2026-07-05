from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from agent_rosetta.typing import EnvironmentState

from .constants.aa import AA_3TO1
from .constants.score import SCORE_FIELDS
from .typing import RosettaStatusCode


class RosettaDesign(BaseModel):
    pdb: Path | None = None
    sequence: list[str] | str | None = None
    score_dict: dict[str, int | float | str] | None = None

    parent_pdb: Path | None = None
    esmfold_pdb: Path | None = None

    reward: dict | None = Field(default_factory=dict)
    is_pareto_efficient: bool | None = None

    @property
    def aa1_sequence(self) -> str:
        if isinstance(self.sequence, str):
            return self.sequence
        return "".join([AA_3TO1.get(res, "X") for res in self.sequence])

    @property
    def metrics(self) -> dict[str, float]:
        score_metrics = {
            k: v for k, v in self.score_dict.items() if isinstance(v, (int, float))
        }
        return {**score_metrics, **self.reward}

    def get_total_energy(self) -> float:
        return sum([self.score_dict.get(k, 0) for k in SCORE_FIELDS])


class RosettaEnvironmentState(EnvironmentState):
    status_code: RosettaStatusCode = "none"
    designs: list[RosettaDesign] | None = None

    def get_error_message(self) -> str:
        lines = []
        lines.append("<error>")
        for line in self.stderr.splitlines():
            if "Begin developer's backtrace" in line:
                break
            line = line.strip()
            if not line:
                continue
            lines.append(line)
        lines.append("</error>")
        return "\n".join(lines).strip().rstrip()
