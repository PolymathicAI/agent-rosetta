from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from rich.text import Text

from agent_rosetta.environment import Environment, EnvironmentConfig
from agent_rosetta.utils.logging import console, logger

from . import functional as F
from . import reward as R
from .state import RosettaEnvironmentState

if TYPE_CHECKING:
    from pydantic import BaseModel

    from agent_rosetta.trajectory import Trajectory
    from agent_rosetta.typing import ActionTag
    from tasks.rosetta.task import RosettaTask

    from .tools.esmfold import ESMFold
    from .tools.esmfold_ray import ESMFoldActor
    from .typing import RosettaAction


@dataclass(frozen=True)
class RosettaEnvironmentConfig(EnvironmentConfig):
    exec_path: str = None
    mpi_exec_path: str = None

    timeout: int = None

    docs_template: str = None
    refine_template: str = None
    debug_template: str = None
    timeout_template: str = None


class RosettaEnvironment(
    Environment[RosettaEnvironmentConfig, RosettaEnvironmentState]
):
    env_dir: Path = Path(__file__).parent
    ref_pdb: Path

    esmfold: ESMFold | ESMFoldActor

    def __init__(self, config: RosettaEnvironmentConfig):
        super().__init__(config)

    def setup(self):
        pass

    def reset(self):
        self.state = RosettaEnvironmentState(global_step=0)

    def get_docs(self, act_name: str) -> str | None:
        act_doc_path = self.env_dir / "docs" / f"{act_name}.md"
        with act_doc_path.open("r") as f:
            doc_content = f.read().strip()
        return doc_content

    def step(
        self,
        act_name: RosettaAction = None,
        act_args: BaseModel = None,
        act_tag: ActionTag = None,
        task: RosettaTask = None,
        traj: Trajectory | None = None,
    ) -> RosettaEnvironmentState:
        if act_name == "sandbox":
            self.state.global_step += 1
            return self.get_state()

        if act_tag == "choose":
            self.state.global_step += 1
            self.state.status_code = "success"
            return self.get_state()

        act_fn = F.act_fn_map[act_name]
        reward_fn = R.task_reward_map[task.config.name]

        step_workdir = task.workdir / f"step_{self.state.global_step}_{act_name}"
        step_workdir.mkdir(parents=True, exist_ok=True)

        with console.status(
            Text(f"Running {act_name}", style="grey37"),
            spinner="dots",
            spinner_style="grey37",
            refresh_per_second=4,
        ):
            logger.info(
                f"Running {act_name} with args:\n{act_args.model_dump_json(indent=4)}"
            )

            start_time = time.time()
            act_results = act_fn(
                env=self, task=task, act_args=act_args, workdir=step_workdir, traj=traj
            )
            end_time = time.time()

        with (step_workdir / "timing.txt").open("a") as f:
            f.write(
                f"{self.state.global_step},{act_name},{act_results.status_code},{start_time},{end_time}\n"
            )

        if act_results.status_code == "success":
            console.print(
                f":heavy_check_mark: {act_name} completed in {end_time - start_time:,.2f} seconds",
                style="grey37",
            )
            logger.info(f"{act_name} completed in {end_time - start_time:,.2f} seconds")
        else:
            console.print(f":heavy_ballot_x: {act_name} failed", style="grey37")
            logger.error(
                f"{act_name} failed with status code {act_results.status_code}, stderr:\n{act_results.stderr}"
            )

        self.state.status_code = act_results.status_code
        self.state.stderr = act_results.stderr

        if act_results.status_code == "success":
            with console.status(
                Text("Scoring designs", style="grey37"),
                spinner="dots",
                spinner_style="grey37",
                refresh_per_second=4,
            ):
                logger.info(f"Scoring {len(act_results.designs)} designs...")
                designs = reward_fn(designs=act_results.designs, env=self, task=task)

            with (step_workdir / "designs.json").open("w") as f:
                json.dump([d.model_dump(mode="json") for d in designs], f, indent=4)

            self.state.designs = designs

        self.state.global_step += 1
        return self.get_state()
