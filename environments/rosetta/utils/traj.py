from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_rosetta.trajectory import Trajectory
    from agent_rosetta.typing import TrajectoryStep


def is_successful(step: TrajectoryStep) -> bool:
    if not step.parser_output:
        return False
    if not step.observation:
        return False

    return (
        step.parser_output.act_tag == "run"
        and step.observation.status_code == "success"
        and step.parser_output.act_name
        not in ["sandbox", "score_pdb", "go_back_to_step"]
    )


def get_successful_steps(traj: Trajectory) -> list[TrajectoryStep]:
    return list(filter(is_successful, traj))
