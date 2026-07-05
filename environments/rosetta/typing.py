from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, TypeAlias

from pydantic import BaseModel

if TYPE_CHECKING:
    from agent_rosetta.trajectory import Trajectory
    from tasks.rosetta.task import RosettaTask

    from .environment import RosettaEnvironment
    from .state import RosettaDesign


RosettaAction: TypeAlias = Literal[
    "sandbox", "score_pdb", "rotamer_change", "backbone_change", "go_back_to_step"
]
RosettaStatusCode: TypeAlias = Literal[
    "none",
    "success",
    "validation_error",
    "resource_error",
    "runtime_error",
    "transport_error",
    "timeout",
]
CmdMode: TypeAlias = Literal["local", "slurm"]
ResidueRestrictionType: TypeAlias = Literal["restrict", "prohibit"]
ScoreDict: TypeAlias = dict[str, str | float]
BackboneMover: TypeAlias = Literal["small", "shear", "backrub"]
RosettaCmdResults: TypeAlias = tuple[RosettaStatusCode, str | None]


class RosettaCmdArgs(BaseModel):
    nstruct: int
    use_mpi: bool
    cmd_mode: CmdMode

    delete_decoy: bool = False
    jd2_failed_job_exception: bool = False

    suffix: str | None = None
    native_pdb: Path | None = None
    extra_res_fa: Path | None = None


@dataclass(frozen=True)
class RosettaActionResults:
    status_code: RosettaStatusCode
    stderr: str | None = None
    designs: list[RosettaDesign] | None = None


class RosettaActionFunction(Protocol):
    def __call__(
        self,
        env: RosettaEnvironment = None,
        task: RosettaTask = None,
        act_args: BaseModel = None,
        workdir: str = None,
        traj: Trajectory = None,
    ) -> RosettaActionResults: ...


class RosettaRewardFunction(Protocol):
    def __call__(
        self,
        designs: list[RosettaDesign] = None,
        env: RosettaEnvironment = None,
        task: RosettaTask = None,
    ) -> list[RosettaDesign]: ...


class RosettaError(Exception):
    pass


class RosettaActionError(RosettaError):
    pass
